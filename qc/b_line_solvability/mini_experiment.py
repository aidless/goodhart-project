"""B 线可解性迷你实验 (KI-002 证据): 同一任务, 规则隐藏 (现状) vs 规则公开 (修复方向)。

目的: 检验 KI-002 的诊断——首批 ETL 地板效应 (5/614) 源于**任务公开信息不足以
推导真值** (gen_tasks.py:110-112 白名单不含 ops/sort_rule/ptr/values), 而非模型
能力; 若规则公开后步准确率显著脱离随机水平, 则"换更强模型重跑"必须先改设计。

设计:
- 每族取排序后前 6 个任务 (确定性), 每个 task 取 k∈{0,2} 两步 (n_steps>=4 恒成立)。
- 臂 H (hidden): 生产 build_prompt (现状, 规则隐藏)。
- 臂 P (public): 同一任务同一 k, prompt 内给出完整规则 (ops 表 / sort_rule+变换
  文字 / ptr 映射+values 表)。真值与判分**不变**: validator.check_step 生产判分。
- 模型默认 qwen3:4b (可用 --model 换); qwen3 系列自动附 /no_think 软开关
  (ollama_model.py 已记录 qwen3:4b 被 thinking 占满的教训)。
- 全部原始回答逐字落盘 (项目纪律: raw 只存逐字, 不转述)。

环境事实 (2026-10-12): 系统级 ollama.service (:11434) 加载任何模型都被
SIGKILL (RTX3060 6GB 被 pid deeped3.py 占 3.4G + RAM 8G/14G 占用); 本实验用
临时 CPU 实例: CUDA_VISIBLE_DEVICES="" OLLAMA_HOST=127.0.0.1:11435 ollama serve,
OLLAMA_URL 指向它。跑完即杀, 不动系统服务。

不写 etl/results/ —— 这是诊断实验, 不是 ETL 跑批。
用法 (项目根目录):
  OLLAMA_URL=http://127.0.0.1:11435/v1/chat/completions \
  python3 qc/b_line_solvability/mini_experiment.py --model qwen3:4b
"""
import argparse
import json
import time

OP_DESC = {
    "add3": "x ← x + 3",
    "mul2": "x ← x × 2",
    "sub1": "x ← x − 1",
    "add7": "x ← x + 7",
    "mul3": "x ← x × 3",
    "xor5": "x ← x 与 5 按位异或",
}


def public_rules_prompt(task, k):
    """臂 P: 同一问题, 但规则公开 (任务从此可解)。答案格式与臂 H 完全一致。"""
    fam = task["family"]
    if fam == "stateful-calc":
        rules = "; ".join(f"第{i+1}步 {OP_DESC[op]}"
                          for i, op in enumerate(task["ops"]))
        return (f"从 x0={task['x0']} 开始。整数规则链（公开）：{rules}。"
                f"请直接给出第 {k+1} 步的结果（只输出一个整数）。")
    if fam == "chain-sort":
        return (f"初始序列 {task['init_seq']}。变换规则（公开）：每一步先把序列"
                f"循环右移一位，再比较前两个元素：asc 规则下前者大于后者则交换，"
                f"desc 规则下前者小于后者则交换。本任务规则 = {task['sort_rule']}。"
                f"请直接给出操作 {k+1} 次后的序列（用逗号分隔，只输出序列）。")
    if fam == "ret-path":
        pairs = ", ".join(f"e{i}→e{p}" for i, p in enumerate(task["ptr"]))
        vals = ", ".join(f"e{i}={v}" for i, v in enumerate(task["values"]))
        return (f"指针映射（公开）：{pairs}。各条目关键值（公开）：{vals}。"
                f"从条目 'e0' 出发沿指针走 {k+1} 跳，"
                f"请直接给出到达条目的关键值（只输出该值）。")
    raise ValueError(fam)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3:4b")
    ap.add_argument("--tasks-per-family", type=int, default=6)
    ap.add_argument("--out", default="qc/b_line_solvability/results.json")
    args = ap.parse_args()

    # env 必须在 import ollama_model 之前设好 (模块级常量在 import 时读取)
    import os
    os.environ["OLLAMA_MODEL"] = args.model
    sys_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "..", "src")
    sys_path = os.path.abspath(sys_path)
    if sys_path not in os.sys.path if hasattr(os, "sys") else True:
        pass
    import sys
    if sys_path not in sys.path:
        sys.path.insert(0, sys_path)

    from validators import Validator          # noqa: E402
    from run_etl import build_prompt          # noqa: E402
    from ollama_model import model_call       # noqa: E402

    import pickle
    with open("etl/data/schedules/schedules.pkl", "rb") as f:
        schedules = pickle.load(f)
    validator = Validator()

    by_family = {}
    for tid in sorted(schedules):
        by_family.setdefault(schedules[tid]["family"], []).append(tid)

    calls = []
    t_start = time.time()
    for fam in sorted(by_family):
        tids = by_family[fam][: args.tasks_per_family]
        for tid in tids:
            s = schedules[tid]
            task = {k: v for k, v in s.items()
                    if k in ("task_id", "family", "n_steps", "x0",
                             "init_seq", "sort_rule", "entries", "ops",
                             "ptr", "values")}
            for k in (0, 2):
                if k >= s["n_steps"]:
                    continue
                for arm, prompt in (("H-hidden", build_prompt(task, k)),
                                    ("P-public", public_rules_prompt(task, k))):
                    if args.model.startswith("qwen3"):
                        prompt = "/no_think\n" + prompt
                    t0 = time.time()
                    raw = model_call(prompt)
                    valid = validator.check_step(tid, k, raw)
                    calls.append({
                        "family": fam, "task_id": tid, "k": k, "arm": arm,
                        "valid": bool(valid), "raw": raw,
                        "latency_s": round(time.time() - t0, 2),
                        "prompt": prompt,
                    })
                    print(f"[{fam}] {tid} k={k} {arm} → "
                          f"{'HIT' if valid else 'miss'} raw={raw!r} "
                          f"({calls[-1]['latency_s']}s)", flush=True)

    summary = {}
    for c in calls:
        key = (c["family"], c["arm"])
        d = summary.setdefault(key, {"hits": 0, "total": 0})
        d["total"] += 1
        d["hits"] += int(c["valid"])
    table = {f"{f} / {a}": f"{d['hits']}/{d['total']}"
             for (f, a), d in sorted(summary.items())}

    out = {
        "model": args.model,
        "date": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "design": "同任务同k, 臂H=生产prompt(规则隐藏), 臂P=规则公开; "
                  "判分=生产 validator.check_step; 每族前6任务×k∈{0,2}",
        "summary": table,
        "n_calls": len(calls),
        "wall_s": round(time.time() - t_start, 1),
        "calls": calls,
    }
    with open(args.out, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\n=== 汇总 (hits/total) ===")
    for kk, vv in table.items():
        print(f"  {kk}: {vv}")
    print(f"\n{len(calls)} 次调用, {out['wall_s']}s, 全量落盘 {args.out}")


if __name__ == "__main__":
    main()
