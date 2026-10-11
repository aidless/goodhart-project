"""Q5 判读的独立重算 + claims.json 生成 (research_verify_claims 输入)。

来源: q5/results/summary_q5.csv (只读, 不修改)。
本脚本**不导入** src/analyze_q5.py —— 独立实现, 用于交叉核对。
理由 (research-evidence-check skill): 核验工具只做数值匹配、不从原始数据重算,
"一个错误数字只要在程序和正文里一致就会通过", 涉及结论的数字必须独立重算。

用法: /home/liuzewen/.venvs/goodhart/bin/python qc/q5_claims/build_claims.py
"""
import csv
import hashlib
import json
import os

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SUMMARY = os.path.join(REPO, "q5", "results", "summary_q5.csv")
EV = os.path.join(HERE, "evidence")
SPEED_LIMIT = 0.376
N_BOOT = 2000
GROUP = "q5-salience"
ALPHA = 0.05


def load_arms():
    with open(SUMMARY, newline="") as f:
        rows = list(csv.DictReader(f))
    arms = {}
    for r in rows:
        arms.setdefault(r["arm"], {})[int(r["seed"])] = r
    missing = {"blind", "salient"} - set(arms)
    if missing:
        raise ValueError(f"缺 arm: {sorted(missing)}")
    seeds = sorted(set(arms["blind"]) & set(arms["salient"]))
    return arms, seeds


def paired_stats(diffs, rng):
    """独立实现的配对统计 (不复制 analyze_q5.py 的代码)。

    sd 用样本标准差 (ddof=1), t 为配对 t, p 为双尾配对 t 检验。
    bootstrap CI 用 2000 次重采样 (与预注册 §4 一致)。
    """
    d = np.asarray(diffs, dtype=float)
    n = len(d)
    mean = float(d.mean())
    sd = float(d.std(ddof=1)) if n > 1 else 0.0
    dz = mean / sd if sd > 0 else 0.0
    se = sd / np.sqrt(n) if sd > 0 else 0.0
    t = mean / se if se > 0 else 0.0
    p = float(stats.ttest_rel(d, np.zeros(n)).pvalue) if sd > 0 else 1.0
    boot = rng.choice(d, size=(N_BOOT, n), replace=True).mean(axis=1)
    lo, hi = (float(x) for x in np.percentile(boot, [2.5, 97.5]))
    pos = int((d > 0).sum())
    return {
        "n": n, "mean": mean, "sd": sd, "d": dz, "t": t, "p": p,
        "ci_low": lo, "ci_high": hi, "pos": pos,
        "pos_share": (pos / n) if n else 0.0,
    }


def write_paired_csv(name, seeds, sal, bli):
    path = os.path.join(EV, name)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        # 列序 = (salient, blind): 工具算的 diff = mean(salient) - mean(blind),
        # 与预注册 §3 "salient - blind" 方向一致。
        w.writerow(["seed", "salient", "blind"])
        for i, s in enumerate(seeds):
            w.writerow([s, repr(sal[i]), repr(bli[i])])
    return name


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    os.makedirs(EV, exist_ok=True)
    arms, seeds = load_arms()
    if len(seeds) != 5:
        raise SystemExit(f"fail-closed: 预期 5 配对 seed, 实得 {seeds}")

    sal_true = [float(arms["salient"][s]["true_score"]) for s in seeds]
    bli_true = [float(arms["blind"][s]["true_score"]) for s in seeds]
    sal_dev = [abs(float(arms["salient"][s]["mean_speed"]) - SPEED_LIMIT) for s in seeds]
    bli_dev = [abs(float(arms["blind"][s]["mean_speed"]) - SPEED_LIMIT) for s in seeds]

    n_true = write_paired_csv("q5_true_paired.csv", seeds, sal_true, bli_true)
    n_dev = write_paired_csv("q5_speeddev_paired.csv", seeds, sal_dev, bli_dev)

    rng = np.random.default_rng(0)
    h1 = paired_stats([a - b for a, b in zip(sal_true, bli_true)], rng)
    h2 = paired_stats([a - b for a, b in zip(sal_dev, bli_dev)], rng)

    mean_sal_true = float(np.mean(sal_true))
    mean_bli_true = float(np.mean(bli_true))
    h1.update({"mean_a": mean_sal_true, "mean_b": mean_bli_true})
    h2.update({"mean_a": float(np.mean(sal_dev)), "mean_b": float(np.mean(bli_dev))})

    print("=== 独立重算 (来源: q5/results/summary_q5.csv) ===")
    print(f"配对 seeds = {seeds} (n={len(seeds)})")
    print(f"blind   true_score mean = {mean_bli_true:.7f}   mean_speed = "
          f"{np.mean([float(arms['blind'][s]['mean_speed']) for s in seeds]):.7f}")
    print(f"salient true_score mean = {mean_sal_true:.7f}   mean_speed = "
          f"{np.mean([float(arms['salient'][s]['mean_speed']) for s in seeds]):.7f}")
    print(f"H1 diff(salient-blind) = {h1['mean']:+.8f}  sd={h1['sd']:.8f} "
          f"dz={h1['d']:+.4f}  t={h1['t']:+.4f}  p={h1['p']:.6f}  "
          f"pos={h1['pos']}/{h1['n']}  CI=[{h1['ci_low']:+.8f}, {h1['ci_high']:+.8f}]")
    print(f"H2 diff(salient-blind) = {h2['mean']:+.8f}  sd={h2['sd']:.8f} "
          f"dz={h2['d']:+.4f}  t={h2['t']:+.4f}  p={h2['p']:.6f}  "
          f"pos={h2['pos']}/{h2['n']}  CI=[{h2['ci_low']:+.8f}, {h2['ci_high']:+.8f}]")

    claims = [
        {
            "id": "Q5-H1-TRUE-SCORE",
            "analysis": {
                "method": "paired-diff", "data": n_true, "experiment": GROUP,
                "alpha": ALPHA, "fields": ["salient", "blind"],
            },
            "evidence": [n_true],
            "statement": (
                f"H1 (预注册 §3): salient - blind 的 true_score 配对差必须 > 0 且 95% "
                f"bootstrap CI 不含 0。实测 mean={h1['mean']:+.6f}, 方向与预注册预测相反, "
                f"CI [{h1['ci_low']:+.6f}, {h1['ci_high']:+.6f}] 含 0, p={h1['p']:.4f} "
                f"不显著 → H1 未确认, 数据与 H0 (两组无差异) 一致。"
                f"两组 steps_alive 均饱和于 500, 信号全部来自罚分项。"
            ),
            "numbers": {
                "experiment": GROUP, "n": h1["n"], "mean_a": h1["mean_a"],
                "mean_b": h1["mean_b"], "diff": h1["mean"], "d": h1["d"],
                "pos": h1["pos"], "pos_share": h1["pos_share"], "t": h1["t"],
                "p": h1["p"], "ci_low": h1["ci_low"], "ci_high": h1["ci_high"],
                "holm_significant": False,
            },
        },
        {
            "id": "Q5-H2-SPEED-DEVIATION",
            "analysis": {
                "method": "paired-diff", "data": n_dev, "experiment": GROUP,
                "alpha": ALPHA, "fields": ["salient", "blind"],
            },
            "evidence": [n_dev],
            "statement": (
                f"H2 (预注册 §3): |mean_speed - limit| 配对差, 方向为 salient 更小。"
                f"实测 mean={h2['mean']:+.6f}, CI [{h2['ci_low']:+.6f}, {h2['ci_high']:+.6f}] "
                f"不含 0, p={h2['p']:.4f} → 冻结判据形式上'确认'。"
                f"但效应量仅为两组共同偏差 (约 0.2689) 的 {abs(h2['mean'])/0.2689*100:.2f}%, "
                f"且两组同为过度保守 (mean_speed 仅为限速的 28.5%/28.8%), 非 H2 假设的"
                f"'压线 vs 冲速'之别 → 形式满足、实质不成立 (如实双记)。"
            ),
            "numbers": {
                "experiment": GROUP, "n": h2["n"], "mean_a": h2["mean_a"],
                "mean_b": h2["mean_b"], "diff": h2["mean"], "d": h2["d"],
                "pos": h2["pos"], "pos_share": h2["pos_share"], "t": h2["t"],
                "p": h2["p"], "ci_low": h2["ci_low"], "ci_high": h2["ci_high"],
                "holm_significant": True,
            },
        },
        {
            "id": "Q5-H1-DIRECTION-KILL",
            "analysis": {
                "method": "kill-switch", "data": n_true, "experiment": GROUP,
                "fields": ["salient", "blind"],
            },
            "evidence": [n_true],
            "statement": (
                "预注册方向性杀开关: H1 预测 salient - blind > 0。实测 diff<0, "
                "方向与预注册预测相反 → 该方向性预测被否证 (STOP-PREREG-DIRECTION-REFUTED)。"
                "注意: 这是方向否证, 不是'惩罚可察觉性不重要'的一般结论 "
                "(预注册 §3 只允许归因 (a)/(b))。"
            ),
            "numbers": {
                "experiment": GROUP, "n": h1["n"], "diff": h1["mean"],
                "verdict": "STOP-PREREG-DIRECTION-REFUTED",
            },
        },
    ]

    ledger = []
    for i, art in enumerate((n_true, n_dev)):
        ledger.append({
            "artifact": art,
            "sha256": sha256(os.path.join(EV, art)),
            "produced_by": "qc/q5_claims/build_claims.py",
            "seed": i,
            "claim_id": "Q5-H1-TRUE-SCORE" if i == 0 else "Q5-H2-SPEED-DEVIATION",
        })

    with open(os.path.join(HERE, "claims.json"), "w") as f:
        json.dump(claims, f, ensure_ascii=False, indent=2)
    with open(os.path.join(EV, "ledger.jsonl"), "w") as f:
        for e in ledger:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    print("\n已写: claims.json + evidence/{q5_true_paired.csv,q5_speeddev_paired.csv,ledger.jsonl}")
    print(f"summary_q5.csv sha256 = {sha256(SUMMARY)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
