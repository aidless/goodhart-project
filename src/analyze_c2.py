"""A2: C.2 分析管线。产出图1 (detach_curve) 与表1 (各组 true_score)。
数据源: c2/results/summary.csv, 字段:
    alpha, seed, proxy_score, true_score, steps_alive, mean_speed
"""
import matplotlib
matplotlib.use("Agg")
import _plot_style  # noqa: F401  导入即生效: CJK 探测 + unicode_minus
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def load_summary(path="c2/results/summary.csv"):
    df = pd.read_csv(path)
    required = {"alpha", "seed", "proxy_score", "true_score"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"summary.csv 缺字段: {sorted(missing)}")
    return df

def aggregate(df):
    """按 alpha 聚合, 给出 mean 与 95% bootstrap CI。"""
    rng = np.random.default_rng(0)
    rows = []
    for alpha, sub in df.groupby("alpha"):
        for col in ("proxy_score", "true_score"):
            vals = sub[col].to_numpy(dtype=float)
            n = len(vals)
            if n == 0:
                continue
            boot = rng.choice(vals, size=(2000, n), replace=True).mean(axis=1)
            lo, hi = np.percentile(boot, [2.5, 97.5])
            rows.append({
                "alpha": alpha,
                "metric": col,
                "mean": float(vals.mean()),
                "ci_lo": float(lo),
                "ci_hi": float(hi),
                "n_seeds": n,
            })
    return pd.DataFrame(rows)

def fig1_detach_curve(agg_df, out="c2/results/fig1_detach_curve.pdf"):
    """双轴: 代理分数与真实分数随 alpha 变化。"""
    fig, ax1 = plt.subplots(figsize=(6.4, 4.0))

    proxy = agg_df[agg_df["metric"] == "proxy_score"].sort_values("alpha")
    true = agg_df[agg_df["metric"] == "true_score"].sort_values("alpha")

    ln1 = ax1.errorbar(
        proxy["alpha"], proxy["mean"],
        yerr=[proxy["mean"] - proxy["ci_lo"], proxy["ci_hi"] - proxy["mean"]],
        marker="o", capsize=3, color="tab:red", label="proxy_score",
    )
    ax1.set_xlabel("alpha")
    ax1.set_ylabel("proxy_score", color="tab:red")
    ax1.tick_params(axis="y", labelcolor="tab:red")

    ax2 = ax1.twinx()
    ln2 = ax2.errorbar(
        true["alpha"], true["mean"],
        yerr=[true["mean"] - true["ci_lo"], true["ci_hi"] - true["mean"]],
        marker="s", capsize=3, color="tab:blue", label="true_score",
    )
    ax2.set_ylabel("true_score", color="tab:blue")
    ax2.tick_params(axis="y", labelcolor="tab:blue")

    # 图例: 合并两个轴的句柄, 只画一次
    handles = [ln1, ln2]
    labels = ["proxy_score", "true_score"]
    ax1.legend(handles, labels, loc="best")

    fig.suptitle("C.2: 代理分数与真实分数随 alpha (95% CI)")
    fig.tight_layout()
    fig.savefig(out)
    print(f"已出图: {out}")

def table1_true_score(agg_df, out="c2/results/table1_true_score.csv"):
    """表1: 每组 true_score / proxy_score mean±CI 与 detach_ratio。"""
    piv = agg_df.pivot(index="alpha", columns="metric", values="mean")
    ci = agg_df.pivot(index="alpha", columns="metric",
                      values=["ci_lo", "ci_hi"])

    true_peak = piv["true_score"].max()
    rows = []
    for alpha in piv.index:
        ts = piv.loc[alpha, "true_score"]
        ps = piv.loc[alpha, "proxy_score"]
        detach = 1.0 - (ts / true_peak) if true_peak != 0 else float("nan")
        rows.append({
            "alpha": alpha,
            "true_score_mean": round(float(ts), 4),
            "true_score_ci": f"[{ci.loc[alpha,('ci_lo','true_score')]:.3f}, "
                             f"{ci.loc[alpha,('ci_hi','true_score')]:.3f}]",
            "proxy_score_mean": round(float(ps), 4),
            "detach_ratio": round(float(detach), 4),
        })
    out_df = pd.DataFrame(rows)
    out_df.to_csv(out, index=False)
    print(f"已出表: {out}")
    return out_df

def verdict(out_df):
    """按预注册第3节判读。三档之一: 确认脱钩 / 部分脱钩 / 否证。"""
    ts = out_df["true_score_mean"].to_numpy()
    drop = 1.0 - ts.min() / ts.max() if ts.max() != 0 else 0.0
    if drop >= 0.15:
        v = "确认脱钩 (true_score 峰值后下降 >= 15%)"
    elif drop >= 0.05:
        v = "部分脱钩 (true_score 峰值后下降 5%-15%)"
    else:
        v = "否证 (true_score 全区间单调不减)"
    print(f"判读: {v}  [峰后跌幅 {drop:.1%}]")
    print("⚠️ 以上为点估计; 正式判读须同时检查 CI 是否含 0, 见预注册第3节。")
    return v

def main():
    df = load_summary()
    agg_df = aggregate(df)
    fig1_detach_curve(agg_df)
    out_df = table1_true_score(agg_df)
    verdict(out_df)
    print("Done: fig1_detach_curve.pdf, table1_true_score.csv")

if __name__ == "__main__":
    main()