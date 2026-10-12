"""Q2/Q4 探索性分析 (B 线规则公开批, 2026-10-12)。

数据源: etl/results/logs.jsonl (90 任务 614 步, qwen2.5:3b, 审计 mismatch=0)。
Q4: 逐 k 准确率衰减拟合; 留出检验 (k<=3 拟合 → 预测 k>=4)。
Q2: 错后恢复转移的结构化刻画 (按族比率 / 按 k 分布)。

纪律: 全部点估计, [exploratory]; n 小, 不做预注册级声称; 输出只写本目录。
"""
import json
import math
from collections import defaultdict

import numpy as np

LOGS = "etl/results/logs.jsonl"
OUT_MD = "qc/q2_q4_analysis/results.md"
OUT_JSON = "qc/q2_q4_analysis/results.json"


def load():
    acc = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # fam -> k -> [ok, n]
    rec = defaultdict(lambda: {"n": 0, "ks": [], "after_ks": []})  # fam -> 恢复统计
    errs = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # fam -> k -> [err, n_err_positions]
    for line in open(LOGS):
        r = json.loads(line)
        prev = True
        for h in r["steps"]:
            fam, k = r["family"], h["k"]
            acc[fam][k][1] += 1
            if h["valid"]:
                acc[fam][k][0] += 1
            else:
                errs[fam][k][0] += 1
            if (not prev) and h["valid"]:
                rec[fam]["n"] += 1
                rec[fam]["ks"].append(k)
            if not prev and not h["valid"]:
                errs[fam][k][1] += 1
                rec[fam]["after_ks"].append(k)
            prev = h["valid"]
    return acc, rec, errs


def fit_decay(xs):
    """log(acc) 对 k 的线性拟合; xs = {k: [ok, n]}。acc=0 的点以 (0.5/n) 平滑进。"""
    pts = []
    for k in sorted(xs):
        ok, n = xs[k]
        if n == 0:
            continue
        p = max(ok / n, 0.5 / n)  # 平滑, 避免log(0)
        pts.append((k, math.log(p)))
    if len(pts) < 3:
        return None
    x = np.array([p[0] for p in pts], dtype=float)
    y = np.array([p[1] for p in pts], dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    pred = slope * x + intercept
    ss_res = float(((y - pred) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return {"slope_per_k": float(slope), "intercept": float(intercept),
            "r2": r2, "n_k_points": len(pts)}


def leave_out_extrap(xs, split=3):
    """k<=split 拟合, 预测 k>split; 报告每点绝对误差 (对数域)。"""
    tr = {k: v for k, v in xs.items() if k <= split}
    te = {k: v for k, v in xs.items() if k > split}
    f = fit_decay(tr)
    if f is None or not te:
        return None
    errs = {}
    for k in sorted(te):
        ok, n = te[k]
        if n == 0:
            continue
        p_hat = math.exp(f["slope_per_k"] * k + f["intercept"])
        p_hat = min(max(p_hat, 1e-6), 1.0)
        errs[k] = {"p_pred": round(p_hat, 4), "p_obs": round(ok / n, 4),
                   "abs_err": round(abs(p_hat - ok / n), 4), "n": n}
    return {"fit_on": f"k<={split}", "points": errs,
            "mean_abs_err": round(float(np.mean([e["abs_err"] for e in errs.values()])), 4)}


def main():
    acc, rec, errs = load()
    out = {"q4": {}, "q2": {}}
    lines = ["# Q2/Q4 探索性分析 (B 线规则公开批 2026-10-12) [exploratory]", "",
             "> 数据: logs.jsonl 90 任务 614 步 (qwen2.5:3b), audit mismatch=0。",
             "> 全部点估计, 小样本; 未预注册; 引用须标 [exploratory]。", ""]

    lines += ["## Q4 — 逐 k 衰减与短链→长链外推", ""]
    for fam in ("stateful-calc", "chain-sort", "ret-path"):
        fam_acc = dict(acc[fam])
        f = fit_decay(fam_acc)
        lo = leave_out_extrap(fam_acc)
        out["q4"][fam] = {"fit": f, "leave_out": lo}
        lines.append(f"### {fam}")
        if f:
            halflife = math.log(0.5) / f["slope_per_k"] if f["slope_per_k"] < 0 else float("inf")
            lines.append(f"- log 线性拟合: 斜率 {f['slope_per_k']:.3f}/k "
                         f"(R²={f['r2']:.3f}, {f['n_k_points']} 个 k 点), 半衰期 ≈ {halflife:.1f} 步")
        if lo:
            lines.append(f"- 留出检验 (k≤3 拟合 → 预测 k≥4): 平均绝对误差 "
                         f"{lo['mean_abs_err']:.3f} (对数域拟合, 线性域对比)")
            for k, e in lo["points"].items():
                lines.append(f"  - k={k}: 预测 {e['p_pred']:.3f} vs 实测 {e['p_obs']:.3f} "
                             f"(n={e['n']}, |Δ|={e['abs_err']:.3f})")
        lines.append("")

    lines += ["### Q4 诚实判读", "",
              "- stateful-calc 的「外推成功」是退化的: 预测≈0 对实测=0 (误差 0.004),",
              "  只说明塌到地板, 不构成外推能力证据。",
              "- chain-sort/ret-path 的逐 k 样本仅 4–30, 曲线噪声大 (R²≈0.00–0.03),",
              "  留出误差 0.15 上下 —— **短链→长链外推在本数据上不可靠**。",
              "- 结论: Q4 仍未回答; 需要更大每 k 样本 (多 seed 重复或多任务) 才能检验。",
              ""]
    lines += ["## Q2 — 错后恢复 (作弊恢复/重锚定) 的结构", ""]
    lines.append("| 族 | 全部错步 | 恢复转移 | 恢复率 | 恢复发生 k 中位 |")
    lines.append("|---|---|---|---|---|")
    for fam in ("stateful-calc", "chain-sort", "ret-path"):
        r = rec[fam]
        n_err = sum(v[0] for v in errs[fam].values())  # 全部错步 (v[0])
        rate = r["n"] / n_err if n_err else 0.0
        med_rec = float(np.median(r["ks"])) if r["ks"] else float("nan")
        out["q2"][fam] = {"err_steps": n_err, "recoveries": r["n"],
                          "rate": round(rate, 4), "median_k_at_recovery": med_rec}
        lines.append(f"| {fam} | {n_err} | {r['n']} | {rate:.1%} | {med_rec:.0f} |")
    lines += ["",
              "### 读法 (与「重锚定假说」对照)",
              "- 恢复率分母 = 全部错步 (188/174/165); 恢复 = 前一步错、本步对。",
              "- 假说: 恢复率 ∝ 从公开 prompt 重算状态的可及性。ret-path 只需重走指针",
              "  (最易) > chain-sort 需重放旋转+交换 (中) > stateful-calc 需重推全部算子 (难)。",
              "- 实测梯度 ret-path 16.4% > chain-sort 8.6% > stateful-calc 2.1% 与假说方向一致;",
              "  这是相容性证据, 不是因果检验 (单模型, 无对照操纵)。",
              "- chain-sort 的恢复也解释了其 0.1168 步准确率: 不靠「执行规则」而靠",
              "  「部分重算」, 与迷你实验 P 臂 0/12 (固定 k=0,2 早期步) 的差异由此调和。"]
    text = "\n".join(lines) + "\n"
    with open(OUT_MD, "w") as f:
        f.write(text)
    with open(OUT_JSON, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(text)


if __name__ == "__main__":
    main()
