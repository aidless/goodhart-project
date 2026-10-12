"""B: ETL runner。逐步询问模型, validator 判分, 落盘 logs.jsonl。"""
import json
import os
from validators import Validator, classify_error

def load_tasks(path="etl/data/tasks/tasks.jsonl"):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]

OP_DESC = {
    "add3": "x ← x + 3",
    "mul2": "x ← x × 2",
    "sub1": "x ← x − 1",
    "add7": "x ← x + 7",
    "mul3": "x ← x × 3",
    "xor5": "x ← x 与 5 按位异或",
}

def build_prompt(task, k):
    """公开规则 + 第 k 步提问 (v2 设计, 2026-10-12 KI-002 定案)。

    规则 (ops/sort_rule/ptr/values) 随任务公开; truth_chain 仍绝不出现在
    prompt。规则 ≠ 答案键: 拿到规则仍须逐步执行才能得到真值。
    """
    fam = task["family"]
    if fam == "stateful-calc":
        rules = "; ".join(f"第{i+1}步 {OP_DESC[op]}"
                          for i, op in enumerate(task["ops"]))
        return (f"从 x0={task['x0']} 开始。整数规则链（公开）：{rules}。"
                f"请直接给出第 {k+1} 步的结果（只输出一个整数）。")
    elif fam == "chain-sort":
        return (f"初始序列 {task['init_seq']}。变换规则（公开）：每一步先把"
                f"序列循环右移一位，再比较前两个元素：asc 规则下前者大于后者"
                f"则交换，desc 规则下前者小于后者则交换。"
                f"本任务规则 = {task['sort_rule']}。"
                f"请直接给出操作 {k+1} 次后的序列（用逗号分隔，只输出序列）。")
    elif fam == "ret-path":
        pairs = ", ".join(f"e{i}→e{p}" for i, p in enumerate(task["ptr"]))
        vals = ", ".join(f"e{i}={v}" for i, v in enumerate(task["values"]))
        return (f"指针映射（公开）：{pairs}。各条目关键值（公开）：{vals}。"
                f"从条目 '{task['entries'][0]}' 出发沿指针走 {k+1} 跳，"
                f"请直接给出到达条目的关键值（只输出该值）。")
    raise ValueError(f"未知任务族: {fam}")

def run(model_call, out_path="etl/results/logs.jsonl", tasks_per_family=None):
    tasks = load_tasks()
    # 降采样 (超时严重时每族只跑 N 个任务, 如实记录不虚报):
    # tasks_per_family=None → 全量; 否则按族取排序后前 N 个 (确定性)。
    if tasks_per_family is not None:
        from collections import defaultdict as _dd
        _by = _dd(list)
        for t in tasks:
            _by[t["family"]].append(t)
        kept = []
        for fam in sorted(_by):
            grp = sorted(_by[fam], key=lambda x: x["task_id"])[:tasks_per_family]
            kept.extend(grp)
        print(f"[etl] 降采样: 每族 {tasks_per_family} 任务 "
              f"(共 {len(kept)}/{len(tasks)} 任务, 如实记录)")
        tasks = sorted(kept, key=lambda x: x["task_id"])
    else:
        print(f"[etl] 全量: {len(tasks)} 任务")
    validator = Validator()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, "w") as f:
        for task in tasks:
            tid = task["task_id"]
            n = task["n_steps"]
            steps = []
            prev_valid = True
            for k in range(n):
                prompt = build_prompt(task, k)
                try:
                    raw = model_call(prompt)
                except Exception as e:
                    raw = f"__ERROR__:{e}"
                valid = validator.check_step(tid, k, raw)
                err_type = classify_error(prev_valid, valid)
                steps.append({
                    "k": k,
                    "valid": valid,
                    "err_type": err_type,
                    "raw": raw,
                })
                prev_valid = valid
            rec = {
                "model": os.environ.get("ETL_MODEL_ID", "unknown"),
                "task_id": tid,
                "family": task["family"],
                "run": 0,
                "steps": steps,
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    import os as _os
    import sys as _sys
    from ollama_model import model_call as _real_model_call
    _tpf = None
    if "--tasks-per-family" in _sys.argv:
        _i = _sys.argv.index("--tasks-per-family")
        try:
            _tpf = int(_sys.argv[_i + 1])
        except (IndexError, ValueError):
            print("用法: run_etl.py [--tasks-per-family N]"); raise SystemExit(2)
    elif _os.environ.get("ETL_TASKS_PER_FAMILY"):
        try:
            _tpf = int(_os.environ["ETL_TASKS_PER_FAMILY"])
        except ValueError:
            print("ETL_TASKS_PER_FAMILY 必须为整数"); raise SystemExit(2)
    # ETL_MODEL_ID 由调用环境传入 (如 llama3.1:8b), 缺省 unknown。
    run(_real_model_call, tasks_per_family=_tpf)