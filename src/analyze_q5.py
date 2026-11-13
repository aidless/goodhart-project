"""A5: Q5 分析管线 — blind vs salient 按 seed 配对比较。

预注册: prereg/preregistration_q5.md §3 (已锁定 2026-10-08)。
判读 (预注册写死, 不得越档表述):
  H1 确认: true_score 配对差 (salient−blind) mean > 0 且 95% bootstrap CI 不含 0
  H2 确认: |mean_speed − speed_limit| 配对差 mean < 0 且 CI 不含 0 (salient 更贴限速)
  其余情形 → 未确认 (如实报告, 不改判据)
强制附带 (§3): 各 arm 的 steps_alive / mean_speed 必须报出。
fail-closed: 配对数 < 5 (预注册样本) → 拒绝判读, exit 1。
跑后义务 (§4): 打印配对差 SD 与 dz, 提醒向预注册 §4 追加实测功效 (只准追加)。

用法 (从仓库根):
  python3 src/analyze_q5.py   # 需 goodhart venv（见 docs/HANDOVER.md）
"""
import argparse
import csv

import numpy as np

SPEED_LIMIT = 0.376
N_BOOT = 2000


def load_arms(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    arms = {}
    for r in rows:
        arms.setdefault(r["arm"], {})[int(r["seed"])] = r
    missing = {"blind", "salient"} - set(arms)
    if missing:
        raise ValueError(f"缺 arm: {sorted(missing)}")
    return arms, sorted(set(arms["blind"]) & set(arms["salient"]))


def paired_ci(diffs, rng):
    diffs = np.asarray(diffs, dtype=float)
    boot = rng.choice(diffs, size=(N_BOOT, len(diffs)), replace=True).mean(axis=1)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return float(diffs.mean()), float(lo), float(hi)


def main():
    ap = argparse.ArgumentParser(description="Q5 配对分析 (preregistration_q5.md §3)")
    ap.add_argument("--csv", default="q5/results/summary_q5.csv")
    args = ap.parse_args()

    arms, common = load_arms(args.csv)
    # fail-closed: 预注册固定 2 arm × 5 seeds; 样本不齐绝不判读
    if len(common) < 5:
        print(f"配对数仅 {len(common)}/5 —— 不足预注册样本, 拒绝判读 (fail-closed)")
        return 1
    print(f"配对 seeds: {common} (n=5, 与预注册 §2 一致)")
    rng = np.random.default_rng(0)

    # 强制附带量 (§3): 各 arm 均值先报
    for arm in ("blind", "salient"):
        ts = np.mean([float(arms[arm][s]["true_score"]) for s in common])
        sa = np.mean([float(arms[arm][s]["steps_alive"]) for s in common])
        ms = np.mean([float(arms[arm][s]["mean_speed"]) for s in common])
        print(f"[{arm:8s}] true={ts:8.2f}  steps_alive={sa:6.1f}  mean_speed={ms:.3f}")

    # H1: true_score 配对差 (salient − blind)
    d1 = [float(arms["salient"][s]["true_score"])
          - float(arms["blind"][s]["true_score"]) for s in common]
    m1, lo1, hi1 = paired_ci(d1, rng)
    h1 = (m1 > 0) and (lo1 > 0 or hi1 < 0)
    print(f"H1 true_score 配对差 (salient−blind): mean={m1:+.2f}  "
          f"95% bootstrap CI [{lo1:+.2f}, {hi1:+.2f}]")
    print(f"H1: {'确认' if h1 else '未确认'} (预注册判据: mean>0 且 CI 不含 0)")

    # H2: |mean_speed − limit| 配对差, 方向 salient 更小
    def dev(r):
        return abs(float(r["mean_speed"]) - SPEED_LIMIT)
    d2 = [dev(arms["salient"][s]) - dev(arms["blind"][s]) for s in common]
    m2, lo2, hi2 = paired_ci(d2, rng)
    h2 = (m2 < 0) and (lo2 > 0 or hi2 < 0)
    print(f"H2 |mean_speed−limit| 配对差: mean={m2:+.4f}  "
          f"95% bootstrap CI [{lo2:+.4f}, {hi2:+.4f}]")
    print(f"H2: {'确认' if h2 else '未确认'} (预注册判据: mean<0 且 CI 不含 0)")

    # §3 触发句: 双饱和检查
    sa = {a: np.mean([float(arms[a][s]["steps_alive"]) for s in common])
          for a in ("blind", "salient")}
    if all(v > 0.98 * 500 for v in sa.values()):
        print("⚠️ 两组 steps_alive 均 >0.98×500 —— 报告须写明信号全部来自罚分项")

    # §4 跑后义务: 实测功效反算 (提醒向预注册追加, 只准追加)
    sd1 = float(np.std(d1, ddof=1))
    dz1 = m1 / sd1 if sd1 > 0 else float("nan")
    print(f"配对差 SD={sd1:.2f}, dz={dz1:.2f} → "
          "向 preregistration_q5.md §4 追加实测功效 (只准追加)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
