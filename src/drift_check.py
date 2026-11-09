"""README 数字块、CLAIM_LEDGER 指针、已提交 CSV / logs 的对照。

不训练, 不调用模型。缺文件就报缺, 不补造。
用法: python3 src/drift_check.py [--require-recompute]
"""
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

import numpy as np

import analyze_c2
import gen_tasks

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

C2_SUMMARY = "report/data/summary.csv"
C2_TABLE = "report/data/table1_true_score.csv"
B1_LOGS = "etl/results/archive_20261008_hidden_rules/logs.jsonl"
B1_TABLE = "etl/results/archive_20261008_hidden_rules/table_detach.csv"
B2_LOGS = "etl/results/archive_20261012_public_rules/logs.jsonl"
B2_TABLE = "etl/results/archive_20261012_public_rules/table_detach.csv"
Q5_TRUE = "qc/q5_claims/evidence/q5_true_paired.csv"
Q5_SPEED = "qc/q5_claims/evidence/q5_speeddev_paired.csv"
Q5_CLAIMS = "qc/q5_claims/claims.json"
SCHED_PKL = "etl/data/schedules/schedules.pkl"
SCHED_SHA = "etl/data/schedules/SHA256.txt"

PATH_RE = re.compile(
    r"(?<![\w./$-])((?:[\w.-]+/)+[\w.-]+\.(?:jsonl|csv|json|md|py|log|pdf|txt|yml))(?![\w])"
)
POINTER_FILES = (
    "README.md",
    "CLAIM_LEDGER.md",
    "FAILURE_MODES.md",
    ".github/workflows/checks.yml",
    "run_all.sh",
)


def fmt4(x):
    v = round(float(x), 4)
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def norm_ci(text):
    body = str(text).strip().strip('"').strip("[]")
    lo, hi = [float(x.strip()) for x in body.split(",")]
    return f"{lo:.3f},{hi:.3f}"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def parse_numbers(text):
    m = re.search(r"```numbers\n(.*?)```", text, re.S)
    if not m:
        raise ValueError("README 缺少 ```numbers 块")
    out = {}
    for line in m.group(1).splitlines():
        if not line.strip():
            continue
        key, value = line.split(":", 1)
        out[key.strip()] = value.strip()
    return out


def log_stats(path):
    tasks = steps = correct = full = 0
    fam = {}
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            tasks += 1
            fam.setdefault(rec["family"], [0, 0])
            ok_task = True
            for step in rec["steps"]:
                steps += 1
                hit = bool(step.get("valid"))
                fam[rec["family"]][0] += 1
                fam[rec["family"]][1] += int(hit)
                correct += int(hit)
                ok_task = ok_task and hit
            full += int(ok_task)
    fam_s = ",".join(f"{k}={fam[k][1]}/{fam[k][0]}" for k in sorted(fam))
    return {
        "tasks": str(tasks),
        "steps": str(steps),
        "correct": str(correct),
        "full": str(full),
        "families": fam_s,
        "rates": {k: fam[k][1] / fam[k][0] for k in fam},
    }


def table_rates(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    return {r["family"]: float(r["step_acc"]) for r in rows}


def paired_mean(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    diffs = [float(r["salient"]) - float(r["blind"]) for r in rows]
    if len(diffs) != 5:
        raise ValueError(f"{path} 期望 5 行, 实得 {len(diffs)}")
    return float(np.mean(diffs))


def c2_fields():
    df = analyze_c2.load_summary(C2_SUMMARY)
    agg = analyze_c2.aggregate(df)
    fd, tmp = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    try:
        tbl = analyze_c2.table1_true_score(agg, out=tmp)
    finally:
        os.remove(tmp)

    def one(alpha):
        hit = tbl[np.isclose(tbl["alpha"].astype(float), alpha)].iloc[0]
        return hit

    a05, a10, a20 = one(0.5), one(1.0), one(2.0)
    return {
        "c2_summary": C2_SUMMARY,
        "c2_summary_sha256": sha256(C2_SUMMARY),
        "c2_n_runs": str(len(df)),
        "c2_true_0.5": fmt4(a05["true_score_mean"]),
        "c2_true_ci_0.5": norm_ci(a05["true_score_ci"]),
        "c2_proxy_0.5": fmt4(a05["proxy_score_mean"]),
        "c2_true_1.0": fmt4(a10["true_score_mean"]),
        "c2_true_ci_1.0": norm_ci(a10["true_score_ci"]),
        "c2_proxy_1.0": fmt4(a10["proxy_score_mean"]),
        "c2_detach_1.0": fmt4(a10["detach_ratio"]),
        "c2_detach_2.0": fmt4(a20["detach_ratio"]),
        "c2_train_config": "MISSING",
        "_table": tbl,
    }


def parse_c2_table(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    parsed = []
    for r in rows:
        parsed.append({
            "alpha": float(r["alpha"]),
            "true": float(r["true_score_mean"]),
            "ci": norm_ci(r["true_score_ci"]),
            "proxy": float(r["proxy_score_mean"]),
            "detach": float(r["detach_ratio"]),
        })
    return parsed


def check_c2_table(tbl, errors):
    committed = {round(r["alpha"], 4): r for r in parse_c2_table(C2_TABLE)}
    if len(committed) != len(tbl):
        errors.append(f"{C2_TABLE} 行数 {len(committed)} != 重算 {len(tbl)}")
        return
    for _, row in tbl.iterrows():
        alpha = round(float(row["alpha"]), 4)
        got = committed.get(alpha)
        if got is None:
            errors.append(f"{C2_TABLE} 缺 alpha={alpha}")
            continue
        if abs(got["true"] - float(row["true_score_mean"])) > 5e-4:
            errors.append(f"alpha={alpha} true_score 与 {C2_TABLE} 不一致")
        if abs(got["proxy"] - float(row["proxy_score_mean"])) > 5e-4:
            errors.append(f"alpha={alpha} proxy_score 与 {C2_TABLE} 不一致")
        if abs(got["detach"] - float(row["detach_ratio"])) > 5e-4:
            errors.append(f"alpha={alpha} detach 与 {C2_TABLE} 不一致")
        if got["ci"] != norm_ci(row["true_score_ci"]):
            errors.append(
                f"alpha={alpha} CI {got['ci']} != 重算 {norm_ci(row['true_score_ci'])}"
            )


def check_rates(stats, table_path, label, errors):
    rates = table_rates(table_path)
    if set(rates) != set(stats["rates"]):
        errors.append(f"{label} 族与 {table_path} 不一致")
        return
    for fam, rate in stats["rates"].items():
        if abs(round(rate, 4) - rates[fam]) > 5e-5:
            errors.append(
                f"{label} {fam} logs {rate:.4f} != {table_path} {rates[fam]}"
            )


def audit_mismatch(path):
    import audit_replay
    steps, mismatches = audit_replay.replay(path)
    return steps, mismatches


def check_pointers(errors):
    for rel in POINTER_FILES:
        text = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        for i, line in enumerate(text.splitlines(), 1):
            if "/home/" in line or "/Users/" in line or re.search(r"[A-Za-z]:\\\\", line):
                errors.append(f"{rel}:{i} 含绝对路径")
            if "goodhart-project/" in line:
                errors.append(f"{rel}:{i} 含无法解析的 goodhart-project/ 前缀")
            for tok in PATH_RE.findall(line):
                if "..." in tok or "*" in tok:
                    continue
                exists = os.path.exists(os.path.join(ROOT, tok))
                if "MISSING" in line:
                    if exists:
                        errors.append(f"{rel}:{i} 标了 MISSING 但文件在: {tok}")
                elif not exists:
                    errors.append(f"{rel}:{i} 指针不存在: {tok}")


def check_q5(ledger, errors):
    if os.path.exists(os.path.join(ROOT, "q5/results/summary_q5.csv")):
        errors.append("q5/results/summary_q5.csv 已出现; 不要把它继续标成 MISSING")
    true_mean = paired_mean(Q5_TRUE)
    speed_mean = paired_mean(Q5_SPEED)
    claims = json.load(open(Q5_CLAIMS, encoding="utf-8"))
    by_id = {c["id"]: c for c in claims}
    h1 = by_id["Q5-H1-TRUE-SCORE"]["numbers"]["diff"]
    h2 = by_id["Q5-H2-SPEED-DEVIATION"]["numbers"]["diff"]
    if abs(true_mean - h1) > 1e-8:
        errors.append(f"Q5 H1 claims.json diff {h1} != {Q5_TRUE} {true_mean}")
    if abs(speed_mean - h2) > 1e-8:
        errors.append(f"Q5 H2 claims.json diff {h2} != {Q5_SPEED} {speed_mean}")
    for token in (f"{true_mean:.6f}", f"{speed_mean:.6f}", Q5_TRUE):
        if token not in ledger:
            errors.append(f"CLAIM_LEDGER 没有与已提交 Q5 表一致的 {token}")


def check_recompute(errors):
    local_table = "c2/results/table1_true_score.csv"
    if not os.path.exists(local_table):
        errors.append(f"--require-recompute: 没有 {local_table}")
    else:
        committed = parse_c2_table(C2_TABLE)
        local = parse_c2_table(local_table)
        if len(local) != len(committed):
            errors.append("本地重算 table1 行数与 report/data 不一致")
        else:
            for a, b in zip(committed, local):
                for key in ("true", "proxy", "detach"):
                    if abs(a[key] - b[key]) > 5e-4:
                        errors.append(f"本地重算 table1 alpha={a['alpha']} {key} 漂移")
                if a["ci"] != b["ci"]:
                    errors.append(f"本地重算 table1 alpha={a['alpha']} CI 漂移")
    for label, arch, local in (
        ("b1", B1_TABLE, "etl/results/offline_recompute/b1/table_detach.csv"),
        ("b2", B2_TABLE, "etl/results/offline_recompute/b2/table_detach.csv"),
    ):
        if not os.path.exists(local):
            errors.append(f"--require-recompute: 没有 {local}")
            continue
        if table_rates(arch) != table_rates(local):
            errors.append(f"{label} 离线重算 step_acc 与归档表不一致: {table_rates(local)}")


def problem_line_count(text):
    m = re.search(r"## 问题（三行）\n+(.+?)\n+## ", text, re.S)
    if not m:
        return None
    return [ln for ln in m.group(1).splitlines() if ln.strip()]


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    os.chdir(ROOT)
    errors = []

    if not os.path.exists(SCHED_PKL):
        gen_tasks.main()
    sched_hash = sha256(SCHED_PKL)
    anchored = open(SCHED_SHA, encoding="utf-8").read().strip()
    if sched_hash != anchored:
        errors.append(f"schedules.pkl sha256 {sched_hash} != {SCHED_SHA} {anchored}")

    if os.path.exists("c2/results/train_config.json"):
        errors.append("c2/results/train_config.json 已出现; 账本把它标为 MISSING, 先核对再改状态")

    readme = open("README.md", encoding="utf-8").read()
    ledger = open("CLAIM_LEDGER.md", encoding="utf-8").read()
    if "STATUS: WORK-IN-PROGRESS — not A yet" not in readme:
        errors.append("README 缺少 STATUS: WORK-IN-PROGRESS — not A yet")
    if "badge.svg" in readme:
        errors.append("README 含 CI 徽章")
    lines = problem_line_count(readme)
    if lines is None or len(lines) != 3:
        errors.append(f"问题陈述不是 3 行 (得到 {0 if lines is None else len(lines)})")

    try:
        block = parse_numbers(readme)
    except ValueError as exc:
        errors.append(str(exc))
        block = {}

    fields = c2_fields()
    tbl = fields.pop("_table")
    check_c2_table(tbl, errors)

    b1 = log_stats(B1_LOGS)
    b2 = log_stats(B2_LOGS)
    b1_steps, b1_mis = audit_mismatch(B1_LOGS)
    b2_steps, b2_mis = audit_mismatch(B2_LOGS)
    if str(b1_steps) != b1["steps"] or str(b2_steps) != b2["steps"]:
        errors.append("audit_replay 步数与 logs 计数不一致")
    check_rates(b1, B1_TABLE, "b1", errors)
    check_rates(b2, B2_TABLE, "b2", errors)

    expected = {
        **fields,
        "etl_b1_logs": B1_LOGS,
        "etl_b1_tasks": b1["tasks"],
        "etl_b1_steps": b1["steps"],
        "etl_b1_correct": b1["correct"],
        "etl_b1_full_tasks": b1["full"],
        "etl_b1_mismatch": str(b1_mis),
        "etl_b1_families": b1["families"],
        "etl_b2_logs": B2_LOGS,
        "etl_b2_tasks": b2["tasks"],
        "etl_b2_steps": b2["steps"],
        "etl_b2_correct": b2["correct"],
        "etl_b2_full_tasks": b2["full"],
        "etl_b2_mismatch": str(b2_mis),
        "etl_b2_families": b2["families"],
        "schedules_sha256": sched_hash,
        "q5_summary": "MISSING",
    }
    if set(block) != set(expected):
        errors.append(
            "numbers 块键集合不一致\n"
            f"  只在 README: {sorted(set(block) - set(expected))}\n"
            f"  只在重算: {sorted(set(expected) - set(block))}"
        )
    for key, value in expected.items():
        if block.get(key) != value:
            errors.append(f"numbers {key}: README={block.get(key)!r} 重算={value!r}")

    for token in (C2_SUMMARY, fields["c2_summary_sha256"], B1_LOGS, B2_LOGS, "5/614"):
        if token not in ledger:
            errors.append(f"CLAIM_LEDGER 未引用 {token}")
    if "q5/results/summary_q5.csv" not in ledger or "MISSING" not in ledger:
        errors.append("CLAIM_LEDGER 没有把 q5/results/summary_q5.csv 标成 MISSING")

    check_q5(ledger, errors)
    check_pointers(errors)
    if "--require-recompute" in argv:
        check_recompute(errors)

    if errors:
        print("drift check FAIL")
        for err in errors:
            print(f"- {err}")
        return 1
    print("drift check PASS")
    print(f"C.2 summary {fields['c2_summary_sha256'][:12]} n={fields['c2_n_runs']}")
    print(f"ETL b1 {b1['correct']}/{b1['steps']} mismatch={b1_mis}; "
          f"b2 {b2['correct']}/{b2['steps']} mismatch={b2_mis}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
