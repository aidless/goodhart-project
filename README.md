# Goodhart 脱钩与链式任务测量

**STATUS: WORK-IN-PROGRESS — not A yet.** 缺口列在下面，不把本仓库说成 A。

## 问题（三行）

测量两件事：C.2 在 CartPole+PPO 上比较真实分和速度代理分随 α 怎么变（只重算已提交的 summary，不在这里重训）；B 看链式 ETL 的已提交 logs 能否重放、错步落在哪（不把答对率写成能力结论）。
不声称：代理分变高等于任务成功；门禁 CLEAN 或 PASS 等于没有泄漏；5 个 seed 上的 α* 是稳定的；B 线已经预注册。
离线路径是 `bash run_all.sh`（生成任务、`src/leak_check.py --selftest`、重放已提交 logs、重算 C.2 summary）。C.2/Q5 训练不在这条路径里，也不在 CI 里。

## 还没到 A

1. `c2/results/train_config.json` — MISSING。`prereg_synced=True` 只是 `c2_run.log` 里的一行。没有策略权重，30 次训练不能从本仓库重打分。
2. `c2/results/` 被 gitignore。已提交的 summary 是 `report/data/summary.csv`，哈希与 `c2_run.log` 相同。新鲜克隆在跑 `run_all.sh` 之前没有 `c2/results/`。
3. `q5/results/summary_q5.csv` — MISSING。steps_alive、原始 mean_speed、罚分合计不能从已提交的配对 CSV 重算，记为 UNKNOWN。配对差本身可以重算，见 CLAIM_LEDGER.md。
4. 现场 ETL 和现场门禁要本地模型（`src/ollama_model.py`）。`run_all.sh` 不调用它。
5. 预注册「确认脱钩」的第 3 条（proxy 达峰后继续上升或持平）在这批汇总上字面不满足。2026-10-08 的裁定和偏离说明在 `docs/HANDOVER.md` §13.11。本仓库不改那个裁定，也不把它写成无条件结论。
6. 归档脚注把 `parse_ok` 写成 JSON 合法率。已提交 logs 里它是 `valid` 的拷贝，而重放表明 `valid` 就是语义判分。
7. `docs/HANDOVER.md` §13.13 保留着已作废的「correct 0/614」。那是对缺失字段 `ok` 的计数。批次 1 的语义正确率是 5/614。原文不删，更正写在 `CLAIM_LEDGER.md`。
8. chain-sort 在早期阈值下不会判 LEAK；低执行功率下 v3.1 也可以是 CLEAN。见 `FAILURE_MODES.md`。

## 已提交数字

下面这块由 `src/drift_check.py` 对照文件重算。改数字而不改文件会失败。训练没有在这里重跑。

```numbers
c2_summary: report/data/summary.csv
c2_summary_sha256: 58b64fc881822af7a8ffb5033146c7a7e94505cf91e58c2322bad7b662192c31
c2_n_runs: 30
c2_true_0.5: 444.0216
c2_true_ci_0.5: 431.894,456.149
c2_proxy_0.5: 0.6429
c2_true_1.0: -2.2205
c2_true_ci_1.0: -4.519,0.081
c2_proxy_1.0: 1.3762
c2_detach_1.0: 1.005
c2_detach_2.0: 0.8661
c2_train_config: MISSING
etl_b1_logs: etl/results/archive_20261008_hidden_rules/logs.jsonl
etl_b1_tasks: 90
etl_b1_steps: 614
etl_b1_correct: 5
etl_b1_full_tasks: 0
etl_b1_mismatch: 0
etl_b1_families: chain-sort=0/197,ret-path=0/204,stateful-calc=5/213
etl_b2_logs: etl/results/archive_20261012_public_rules/logs.jsonl
etl_b2_tasks: 90
etl_b2_steps: 614
etl_b2_correct: 87
etl_b2_full_tasks: 1
etl_b2_mismatch: 0
etl_b2_families: chain-sort=23/197,ret-path=39/204,stateful-calc=25/213
schedules_sha256: 6c78350def493ef409e504f5a3a8db3b3a5f39219e69b1be271eccda1704adc9
q5_summary: MISSING
```

## 怎么跑

离线（新鲜克隆，目标在 15 分钟内，实际是分钟级）：

```bash
python3 -m venv .venv
grep -viE '^(torch|stable-baselines3)' requirements.txt > /tmp/offline-requirements.txt
.venv/bin/python -m pip install -r /tmp/offline-requirements.txt
bash run_all.sh
```

仓库里已有 `.venv` 时，`run_all.sh` 用它的解释器。否则用 `python3`，也可以 `PYTHON=python3 bash run_all.sh`。上面的安装与 CI 一样，去掉 `torch` 和 `stable-baselines3`。

`run_all.sh` 做：生成任务、`leak_check --selftest`、重放五份已提交 logs、从 `report/data/summary.csv` 重算 C.2 表、从两份归档重算 ETL 表、跑 `drift_check` 和 pytest。

训练（可选，不在 CI，时间不在上面的 15 分钟里）：

```bash
.venv/bin/python -m pip install torch stable-baselines3
.venv/bin/python src/train_c2.py
.venv/bin/python src/train_q5.py
```

现场门禁或现场 ETL 另跑，并且需要本地模型。没有模型时 `src/leak_check.py`（不带 `--selftest`）会 fail-closed 退出：

```bash
.venv/bin/python src/leak_check.py
.venv/bin/python src/run_etl.py
```

脚本从仓库根运行，例如 `python3 src/drift_check.py`。`python -m` 会让 `import _plot_style` 失败。

`schedules.pkl` 不入库。入库的是 `etl/data/schedules/SHA256.txt`。`run_all.sh` 会重新生成 pickle，并检查哈希没变。

## 失败时看起来像成功的三种情况

见 `FAILURE_MODES.md`：泄漏门禁的假绿、代理分变好而真实分崩、n=5 的种子脆弱。

## 目录

```
./
├── prereg/                 # C.2 与 Q5 预注册
├── src/                    # 生成、门禁、ETL、审计、重算、drift_check
├── etl/data/tasks/         # 公开任务
├── etl/data/schedules/     # 只入库 SHA256.txt
├── etl/results/archive_*/  # 已提交的 ETL 批次
├── report/data/            # 已提交的 C.2 summary 与 table1
├── qc/                     # Q5 配对表、探索性分解
├── docs/known_issues.md
├── CLAIM_LEDGER.md
├── FAILURE_MODES.md
└── run_all.sh              # 离线路径，不含训练
```

## 两条约束

1. `schedules.pkl` 只给 validator 读。跑现场模型前先过 `src/leak_check.py`。
2. `src/audit_replay.py` 的 mismatch 必须为 0。`logs.jsonl` 的 `raw` 是逐字原文。

已知问题的过程记录在 `docs/known_issues.md`。账本在 `CLAIM_LEDGER.md`。
