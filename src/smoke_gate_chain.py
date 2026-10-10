"""门禁链第 3–5 步的**基础设施冒烟测试** (确定性 stub, 非模型测量)。

背景: `run_all.sh` 在门禁处 fail-closed 中止, 因为 `run_etl.py` 的
`model_call` 仍是占位实现 —— 于是 run_etl / audit_replay / analyze_etl
这三步从未在真实数据上跑过。环境里也没有任何 LLM 凭据, 无法接入真实模型。

本脚本用**确定性 stub** 把这三步的数据契约打通, 并验证门禁的 fail-closed
行为。它证明的是「管线能跑、契约能对上」, **不是**「模型行为如何」。
所有产物写到临时目录, 绝不碰 etl/results/ 的正式结果。

用法: python3 src/smoke_gate_chain.py
退出码 0 = 全部通过。
"""
import json
import os
import pickle
import random
import shutil
import sys
import tempfile

import analyze_etl
import leak_check
import run_etl
from leak_check import _truth_map

SCHED = "etl/data/schedules/schedules.pkl"
TASKS = "etl/data/tasks/tasks.jsonl"

WARN = ("=" * 70 + "\n"
        "⚠️  本脚本产出的是【基础设施冒烟测试】数据, 由确定性 stub 生成,\n"
        "    不是模型测量结果, 绝不能进入论文/报告的任何数字。\n"
        + "=" * 70)


def _load_schedules():
    with open(SCHED, "rb") as f:
        return pickle.load(f)


def _check(name, ok, detail=""):
    print(f"  [{'✓' if ok else '✗'}] {name}" + (f" — {detail}" if detail else ""))
    return ok


def t1_gate_fail_closed(schedules):
    """stub 全部抛异常 (模拟接口不可用) → 门禁必须 FAIL。"""
    print("\n[T1] 接口不可用 → 门禁 fail-closed")

    def dead(prompt):
        raise RuntimeError("stub: 接口不可用")

    ok = (leak_check.run_leak_check(schedules, dead, rng=random.Random(0)) is False)
    return _check("全调用失败时 GATE = FAIL (未静默放行)", ok)


def t2_gate_catches_leak(schedules):
    """stub 是 oracle (答对全部) → 门禁必须 FAIL (LEAK)。"""
    print("\n[T2] 完美泄漏 → 门禁判 LEAK")

    tmap = _truth_map(schedules)
    ok = (leak_check.run_leak_check(schedules, lambda p: tmap[p],
                                    rng=random.Random(0)) is False)
    return _check("oracle 泄漏时 GATE = FAIL", ok)


def t3_gate_passes_garbage(schedules):
    """stub 恒答无关串 → 门禁必须 PASS (否则门是装饰)。"""
    print("\n[T3] 诚实乱答 → 门禁放行 (证明门不是恒拦)")

    ok = (leak_check.run_leak_check(schedules, lambda p: "__NO_ANSWER__",
                                    rng=random.Random(0)) is True)
    return _check("乱答时 GATE = PASS", ok)


def t4_chain_plumbing(schedules, workdir):
    """用 oracle-with-decay stub 跑通 run_etl → audit_replay → analyze_etl。

    stub 对每个 (任务,k) 确定性作答: 前 2 步给真值、之后给错值 —— 这样
    logs.jsonl 里同时出现 single 与 cumulative 两类错误, 把 analyze_etl 的
    两条分支都走到。

    注意: 这一步**绕过门禁**(直接调 run_etl.run) —— 因为 oracle 必然被判
    LEAK。绕过是有意的: 本步只验数据契约, 不做任何测量, 且产物落在临时目录。
    """
    print("\n[T4] run_etl → audit_replay → analyze_etl 数据契约")
    print("  (绕过门禁直接调 run_etl: 本步只验契约, 不测量, 产物在临时目录)")

    # 注意: run_etl.build_prompt 与 leak_check 的探针 prompt 是**两套**字符串,
    # 所以这里必须用 build_prompt 自己建映射, 不能借用 _truth_map。
    tasks = run_etl.load_tasks()
    tmap = {}
    for t in tasks:
        s = schedules[t["task_id"]]
        for k in range(t["n_steps"]):
            truth = s["truth_chain"][k]
            # 模型只会吐出字符串: 序列族要 join, 标量族要 str
            tmap[run_etl.build_prompt(t, k)] = (
                ",".join(str(x) for x in truth) if isinstance(truth, list)
                else str(truth))

    def stub(prompt):
        """每 4 次查询答对 1 次 → logs 里同时有 valid 与 invalid。

        用全局调用计数而非解析 prompt 里的 k: 本步只求制造 mixed 数据,
        不做任何测量, 越简单越不容易引入自己的 bug。
        """
        if prompt not in tmap:
            return "__NO_ANSWER__"
        stub.n += 1
        return tmap[prompt] if (stub.n % 4 == 0) else "__NO_ANSWER__"

    stub.n = 0

    logs = os.path.join(workdir, "logs.jsonl")
    run_etl.run(stub, out_path=logs)
    n_lines = sum(1 for ln in open(logs) if ln.strip())
    ok = _check("run_etl 写出 logs.jsonl", os.path.getsize(logs) > 0,
                f"{n_lines} 条记录")

    # -- audit_replay: 逐 step 重放判分, mismatch 必须为 0 ------------------
    rc = _audit(logs)
    ok &= _check("audit_replay mismatch = 0", rc == 0,
                 f"退出码 {rc}")

    # -- analyze_etl: 出图/出表/出片段 (全部重定向到临时目录) ---------------
    df = analyze_etl.load_records(logs)
    fig1 = os.path.join(workdir, "fig_etl_curve.pdf")
    fig2 = os.path.join(workdir, "fig_error_decomp.pdf")
    tbl = analyze_etl.detach_table(df, path=os.path.join(workdir, "table_detach.csv"))
    analyze_etl.etl_curve(df, out=fig1)
    analyze_etl.error_decomposition(df, out=fig2)
    analyze_etl.report_snippets(tbl, path=os.path.join(workdir, "report_snippets.md"))
    ok &= _check("analyze_etl 四个产物均生成",
                 all(os.path.exists(p) for p in (
                     fig1, fig2,
                     os.path.join(workdir, "table_detach.csv"),
                     os.path.join(workdir, "report_snippets.md"))))
    ok &= _check("logs 含 parse_ok 与不可解析两类 (两条分支都被走到)",
                 df["parse_ok"].any() and (~df["parse_ok"]).any(),
                 f"parse_ok={int(df['parse_ok'].sum())}/{len(df)}")
    return ok


def _audit(logs):
    """直接复用 audit_replay 的判定逻辑, 返回 mismatch 数 (0 = PASS)。"""
    from validators import Validator, classify_error
    validator = Validator()
    mismatches = 0
    with open(logs) as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            prev_valid = True
            for h in rec["steps"]:
                re_valid = validator.check_step(rec["task_id"], h["k"], h["raw"])
                re_err = classify_error(prev_valid, re_valid)
                if re_valid != h["valid"] or re_err != h["err_type"]:
                    mismatches += 1
                prev_valid = re_valid
    return mismatches


def main():
    print(WARN)
    for p in (SCHED, TASKS):
        if not os.path.exists(p):
            print(f"缺少 {p}; 请先跑 python3 src/gen_tasks.py")
            return 2

    schedules = _load_schedules()
    print(f"\n真实 schedules: {len(schedules)} 任务 "
          f"(sha256 见此目录 SHA256.txt)")

    workdir = tempfile.mkdtemp(prefix="smoke_gate_chain_")
    print(f"临时工作目录: {workdir}")
    try:
        results = [
            t1_gate_fail_closed(schedules),
            t2_gate_catches_leak(schedules),
            t3_gate_passes_garbage(schedules),
            t4_chain_plumbing(schedules, workdir),
        ]
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    print("\n" + "=" * 70)
    if all(results):
        print("SMOKE: PASS — 门禁 fail-closed 成立, 第 3–5 步契约接通")
        print("限制: 真实模型调用仍被『环境无 LLM 凭据』阻塞, 未做任何真实测量。")
        return 0
    print("SMOKE: FAIL — 见上方 ✗ 项")
    return 1


if __name__ == "__main__":
    sys.exit(main())
