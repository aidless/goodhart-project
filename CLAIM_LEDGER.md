# CLAIM_LEDGER

> 每条 claim = 陈述 + 预注册出处 + 判定检验 + 证据指针 + 状态。
> 状态词只用 `verified` / `inconclusive` / `TODO`。
> 指针是仓库内相对路径。文件不在 git 里就写 MISSING，不补造。
> 不把 `docs/HANDOVER.md` 里的绝对路径当成复现步骤。

## V-C2-01 — C.2 汇总表可重算（verified，范围只到已提交的 summary）

- 陈述：`report/data/summary.csv` 有 30 行数据（6 档 α × 5 seeds）。sha256 与 `c2_run.log` 记录的摘要哈希相同。用 `src/analyze_c2.py` 重算，α=0.5 的 true 均值 444.0216（CI 431.894,456.149），α=1.0 的 true 均值 −2.2205、proxy 均值 1.3762。α=1.0 的 detach 1.005，α=2.0 的 detach 0.8661。这是已提交汇总的重算，不是一次新的训练。
- 预注册：`prereg/preregistration_c2.md` 的 H1/H0/H2、三档判读、强制附带。第 3 条「proxy 达峰后继续上升或持平」在这批汇总上字面不满足（proxy 在 α=1.0 最大，其后回落）。2026-10-08 的裁定记在 `docs/HANDOVER.md` §13.11，本账本不升级那次裁定。
- 判定检验：`python3 src/drift_check.py` 对照 README 的 numbers 块、本文件、以及 `report/data/table1_true_score.csv`。
- 证据指针：
  - `report/data/summary.csv`（30 行数据 + 表头；sha256 `58b64fc881822af7a8ffb5033146c7a7e94505cf91e58c2322bad7b662192c31`）
  - `report/data/table1_true_score.csv`
  - `c2_run.log`（30 行 `[run]`，并记录同一 sha256；`prereg_synced=True` 只出现在这行日志里）
  - `c2/results/summary.csv` — MISSING。`c2/results/` 被 gitignore。离线路径会把重算表写到该目录，不把 summary 从训练集再造出来。
  - `c2/results/train_config.json` — MISSING。没有提交的配置文件，不能从日志反写一份。
- 状态：**verified**（仅限已提交 summary 的均值、CI、detach 与日志哈希一致）。训练权重、逐步曲线不在仓库里，不能从本仓库重跑判分。

## V-ETL-01 — 批次 1 判分可重放（verified）

- 陈述：`etl/results/archive_20261008_hidden_rules/logs.jsonl` 为 90 个任务、614 步，模型名 llama3.1:8b。`src/audit_replay.py` 重放 mismatch=0。语义正确（日志字段 `valid`，与 `Validator.check_step` 一致）为 5/614：chain-sort 0/197、ret-path 0/204、stateful-calc 5/213。整任务全对 0/90。这不是能力结论。B 线没有预注册。
- 更正（原文保留在 `docs/HANDOVER.md` §13.13）：该节写过「correct 0/614」。日志里没有 `ok` 字段。对缺失键计数会得到 0。语义正确率是 5/614。`paper/main.tex` 写的是 5/614。
- 预注册出处：无。`docs/internal_report_skeleton.md` 把 B 线标为 exploratory。
- 判定检验：`python3 src/audit_replay.py etl/results/archive_20261008_hidden_rules/logs.jsonl` 必须打印 mismatch=0 并以 0 退出。
- 证据指针：
  - `etl/results/archive_20261008_hidden_rules/logs.jsonl`
  - `etl/results/archive_20261008_hidden_rules/table_detach.csv`
  - `etl/results/archive_20261008_hidden_rules/report_snippets.md`（脚注把 parse_ok 写成 JSON 合法率；见 F-ETL-COLUMN。表内数字不改。）
  - `etl/results/archive_20261008_hidden_rules/fig_etl_curve.pdf`
  - `etl/results/archive_20261008_hidden_rules/fig_error_decomp.pdf`
  - `etl/results/logs.jsonl` — MISSING。这是可被重跑覆盖的工作副本，不入库。
- 状态：**verified**（判分可重放，以及 5/614 这一计数）。不把 5/614 写成模型能力。

## V-ETL-02 — 批次 2 规则公开重跑（exploratory）

- 陈述：`etl/results/archive_20261012_public_rules/logs.jsonl` 为 qwen2.5:3b，90 任务、614 步。语义正确 chain-sort 23/197、ret-path 39/204、stateful-calc 25/213，合计 87/614。整任务全对 1/90。audit mismatch=0。未预注册，只作描述。
- 对照：批次 1 与批次 2 的模型和 prompt 都不同。不能把两批的差写成「模型变强了」。
- 证据指针：
  - `etl/results/archive_20261012_public_rules/logs.jsonl`
  - `etl/results/archive_20261012_public_rules/table_detach.csv`
  - `etl/results/archive_20261012_public_rules/report_snippets.md`
  - `qc/q2_q4_analysis/results.json`（探索性分解；不是预注册检验）
- 状态：账本状态词里没有「exploratory」。这里保持 **TODO** 作为「未预注册、不可升级为机制结论」，数字本身由 drift check 对照 logs。

## I-Q5-H1 — 惩罚可见性主假设（inconclusive）

- 陈述：已提交的 `qc/q5_claims/evidence/q5_true_paired.csv` 上，salient−blind 的 true_score 配对差均值是 -0.000352。`qc/q5_claims/claims.json` 的 CI 含 0。不外推成「可察觉性不重要」。
- 预注册：`prereg/preregistration_q5.md`。
- 证据指针：
  - `qc/q5_claims/evidence/q5_true_paired.csv`
  - `qc/q5_claims/claims.json`
  - `q5_run.log`（10 行 `[run]` 与 exit 0。日志没有逐 seed 的分数。）
  - `q5/results/summary_q5.csv` — MISSING。
  - `docs/HANDOVER.md` §13.12 记录过一个 sha256。仓库里没有这份原始表，不能在这里复核那个哈希。
  - `q5/results/train_config_q5.json` — MISSING。
- `steps_alive` 与罚分合计出现在 §13.12 的表里，不在已提交的配对 CSV 里。这两项从 git 树 **UNKNOWN**，引用时不要写成已复核。
- 状态：**inconclusive**

## I-Q5-H2 — 惩罚可见性次假设（inconclusive）

- 陈述：`qc/q5_claims/evidence/q5_speeddev_paired.csv` 上，|mean_speed−limit| 的 salient−blind 配对差均值是 -0.001264。`qc/q5_claims/claims.json` 记 CI 不含 0。效应相对两组共同偏差很小，而且文件里没有带符号的 mean_speed 列，不能从这张表单独还原「0.107 / 0.108」的速度。那两个速度值 **UNKNOWN**（只在 §13.12 的叙述里）。
- 证据指针：同 I-Q5-H1 的已提交配对表与 `qc/q5_claims/claims.json`。
- 状态：**inconclusive**

## I-B-MECH — 链式误差分解（TODO）

- 陈述：cumulative / single 分解没有预注册检验。批次 1 的 first_err 中位数是 0，但不是每个任务都在第 0 步出错（stateful-calc 有正确步）。不能把「中位数为 0」写成「没有任何一步算对」。
- 证据指针：`etl/results/archive_20261008_hidden_rules/fig_error_decomp.pdf`，`docs/internal_report_skeleton.md`。
- 状态：**TODO**

## I-C2-H2 — α* 稳定性（TODO）

- 陈述：30 行 summary 里每个 seed 的 true 峰都在 α=0.5，也就是网格左端。方差 0 是删失，不是 H2 的正面证据。
- 证据指针：`report/data/summary.csv`。
- 状态：**TODO**

## I-VENUE — 投稿口径（TODO）

- 陈述：投到哪里是决定，不是数据。
- 状态：**TODO**

## F-ETL-COLUMN — `parse_ok` 列名（TODO）

- 陈述：归档表 `etl/results/archive_20261008_hidden_rules/table_detach.csv` 的 `step_acc` 与日志 `valid` 一致，在 mismatch=0 时也就是语义正确率。`parse_ok` 列拷贝同一个 `valid` 位。归档脚注把它写成 JSON 合法率，这个区分在已提交 logs 上并不存在。列没有改名，避免改写归档。
- 证据指针：`src/analyze_etl.py`，`etl/results/archive_20261008_hidden_rules/report_snippets.md`。
- 状态：**TODO**

## 复算

```bash
python3 src/drift_check.py
python3 src/audit_replay.py etl/results/archive_20261008_hidden_rules/logs.jsonl
python3 src/analyze_c2.py report/data/summary.csv c2/results
```
