"""A2: ETL 分析管线 (含容错字段读取)。产出图2/图3/表2。
数据源: etl/results/logs.jsonl

2026-10-08 修复: step_acc 口径缺陷。
  原缺陷: step_acc 读的是 valid (JSON 合法率), 不是语义正确率。
  修复: 用 Validator.check_step() 对每步重新判分, 得到真正的 correct。
  区分: parse_ok (JSON 可解析) vs correct (语义正确, 经真值判分)。
"""
import json
import matplotlib
matplotlib.use("Agg")
import _plot_style  # noqa: F401  导入即生效: CJK 探测 + unicode_minus
import matplotlib.pyplot as plt
import pandas as pd
from validators import Validator

_validator = None

def _get_validator():
    global _validator
    if _validator is None:
        _validator = Validator()
    return _validator

def _pick(d, *names, default=None):
    for n in names:
        if n in d:
            return d[n]
    return default

def _norm_err(v):
    if v is None:
        return None
    v = str(v).lower()
    if "cumul" in v:
        return "cumulative"
    if "single" in v:
        return "single"
    return "other"

def load_records(path="etl/results/logs.jsonl"):
    recs = []
    val = _get_validator()
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            for h in r["steps"]:
                k = h["k"]
                raw = h.get("raw", "")
                # 用 Validator 重新判分 (真值判分)
                try:
                    correct = val.check_step(r["task_id"], k, raw)
                except Exception:
                    correct = False
                recs.append({
                    "model": r["model"],
                    "task_id": r["task_id"],
                    "family": _pick(r, "family", default=r["task_id"].rsplit("-", 1)[0]),
                    "run": _pick(r, "run", "trial", default=0),
                    "k": k,
                    "parse_ok": bool(_pick(h, "valid", "correct", default=False)),
                    "correct": bool(correct),
                    "err_type": _norm_err(_pick(h, "err_type", "error_class", "err")),
                })
    return pd.DataFrame(recs)

def etl_curve(df, out="etl/results/fig_etl_curve.pdf"):
    fams = sorted(df["family"].unique())
    fig, axes = plt.subplots(1, len(fams), figsize=(4 * len(fams), 3.2), sharey=True)
    if len(fams) == 1:
        axes = [axes]
    for ax, fam in zip(axes, fams):
        sub = df[df["family"] == fam]
        curve_correct = sub.groupby("k")["correct"].mean()
        curve_parse = sub.groupby("k")["parse_ok"].mean()
        ax.plot(curve_correct.index, curve_correct.values, marker="o", label="correct (语义)")
        ax.plot(curve_parse.index, curve_parse.values, marker="s", linestyle="--", label="parse_ok (合法)")
        ax.set_title(fam)
        ax.set_xlabel("step k")
        if ax is axes[0]:
            ax.set_ylabel("rate")
        ax.set_ylim(0, 1.05)
        ax.legend(fontsize=8)
    fig.suptitle("ETL: 语义正确率 vs 合法率 随 k")
    fig.tight_layout()
    fig.savefig(out)
    print(f"已出图: {out}")

def error_decomposition(df, out="etl/results/fig_error_decomp.pdf"):
    """single vs cumulative 占比随 k。"""
    fams = sorted(df["family"].unique())
    fig, axes = plt.subplots(1, len(fams), figsize=(4 * len(fams), 3.2))
    if len(fams) == 1:
        axes = [axes]
    for ax, fam in zip(axes, fams):
        sub = df[(df["family"] == fam) & (~df["correct"])]
        if len(sub) == 0:
            ax.set_title(f"{fam} (无错)")
            continue
        counts = sub.groupby(["k", "err_type"]).size().unstack(fill_value=0)
        shares = counts.div(counts.sum(axis=1), axis=0)
        cum = shares.get("cumulative", pd.Series(0.0, index=shares.index))
        sin = shares.get("single", pd.Series(0.0, index=shares.index))
        ax.plot(cum.index, cum.values, marker="o", label="cumulative")
        ax.plot(sin.index, sin.values, marker="s", label="single")
        ax.set_title(fam)
        ax.set_xlabel("step k")
        ax.set_ylim(0, 1.05)
        ax.legend()
    fig.suptitle("误差分解: cumulative vs single [exploratory]")
    fig.tight_layout()
    fig.savefig(out)
    print(f"已出图: {out}")

def detach_table(df, path="etl/results/table_detach.csv"):
    """每模型整体语义正确率 + 合法率 + 首错步中位数。"""
    rows = []
    for (model, fam), sub in df.groupby(["model", "family"]):
        acc = sub["correct"].mean()
        parse = sub["parse_ok"].mean()
        first_err = []
        for tid, g in sub.groupby("task_id"):
            g = g.sort_values("k")
            bad = g[~g["correct"]]
            first_err.append(int(bad["k"].iloc[0]) if len(bad) else -1)
        rows.append({
            "model": model, "family": fam,
            "step_acc": round(acc, 4),
            "parse_ok": round(parse, 4),
            "first_err_median": pd.Series(first_err).median(),
        })
    out = pd.DataFrame(rows)
    out.to_csv(path, index=False)
    print(f"已出表: {path}")
    return out

def report_snippets(tbl, path="etl/results/report_snippets.md"):
    lines = ["# ETL 结果片段 (自动生成, 严禁手抄)", ""]
    lines.append("## 整体语义正确率")
    lines.append("")
    lines.append("| model | family | step_acc | parse_ok | first_err_median |")
    lines.append("|---|---|---|---|---|")
    for _, r in tbl.iterrows():
        lines.append(f"| {r['model']} | {r['family']} | {r['step_acc']} | {r['parse_ok']} | {r['first_err_median']} |")
    lines.append("")
    lines.append("> step_acc = 语义正确率 (经 Validator 真值判分); parse_ok = JSON 合法率。")
    lines.append("> 注意: 以上数字未经预注册假设检验, 引用前对照 preregistration_c2.md 判读规则。")
    text = "\n".join(lines)
    with open(path, "w") as f:
        f.write(text + "\n")
    print(f"已出片段: {path}")

def main():
    df = load_records()
    if df.empty:
        print("logs.jsonl 为空, 无可分析")
        return
    etl_curve(df)
    error_decomposition(df)
    tbl = detach_table(df)
    report_snippets(tbl)
    print("Done: fig_etl_curve.pdf, fig_error_decomp.pdf, table_detach.csv, report_snippets.md")

if __name__ == "__main__":
    main()
