# PAPER_DRAFT / Methods 初稿 — Goodhart 脱钩与链式任务审计（草稿，未投稿）

> 状态：初稿（2026-10-09）。本章只写“做了什么、怎么做的”，不写结论；
> 每个可核查事实带文件行号；凡涉及判断的一律标“设计选择”而非“最优”。

## 3.1 C.2：CartPole 速度奖励失真实验

- **预注册**：假设与变量见 `prereg/preregistration_c2.md: L33-L37`（H1/H0/H2）、
  `L42-L48`（真/代理/speed/α 网格/控制）；冻结值 `λ=1.0`、限速 `0.376`、
  `timesteps=100000`（`L50`）；detach 定义 + 三档判读 `L63-L68`；强制附带 `L72-L76`。
- **运行配置**：α ∈ {0.5, 1.0, 1.5, 2.0, 2.5, 3.0} × seeds 42–46 ×
  `n_eval_episodes=50`（`c2/results/train_config.json: L2-L19`）；
  训练奖励用每步 `speed^α`，报告的 proxy 按预注册定义取 `mean(speed)^α`
 （两者口径差异已在 `train_config.json: L25` 声明，非笔误）。
- **产物**：30 行原始记录 `c2/results/summary.csv`（表头 + 30 行）；
  六档聚合 `c2/results/table1_true_score.csv`；脱钩曲线图 `fig1_detach_curve.pdf`。
- **功效**：预注册实算 SD 上限 44.6（`preregistration_c2.md: L81-L86`）；
  跑后配对差 446.2±15.1 / 432.7±16.0（`L88-L98`）。

## 3.2 链式任务 ETL：三族 + 单向流 validator

- **任务族**（各 30 任务，共 90）：stateful-calc（有状态计算链）、
  chain-sort（链式排序）、ret-path（回溯路径）。
- **防泄漏设计**：schedules 只被 validator 读，模型侧永远拿不到真值
  （`src/validators.py: Validator.check_step` 按 `truth_chain[k]` 判分）；
  门禁 `src/leak_check.py`（三族各 20 probe，全失败则 GATE FAIL，fail-closed）；
  事后 `src/audit_replay.py` 重放全部步数，mismatch 必须为 0。
- **本批运行**：本地 Ollama `/v1/chat/completions`，`model=llama3.1:8b`，
  temperature=0，timeout 60s，失败重试 1 次后记 `__UNTESTED__`
 （接入方式见 `docs/HANDOVER.md: L682`；门禁实测表 `L697-L703`）。
  产物：90 行 `etl/results/logs.jsonl`（614 步）、曲线图、出表脚本
  `src/analyze_etl.py`（`correct` 经真值判分、`parse_ok` 为合法率，二者分列）。
- **设计选择（非最优声明）**：单模型（llama3.1:8b）+ temperature 0 的选择只为
  可复现，不代表该配置最优或最强；三族 step 正确率 floor 效应见 §4.2。

## 3.3 Q5 惩罚可见性（null 亦是数据）

- 2 arm（blind/salient）× 5 seeds × 100k（`q5/results/train_config_q5.json: L1-L18`，
  prereg_synced true）；结果 `q5/results/summary_q5.csv`：blind 5 seeds 真实分
  ≈499.99、steps_alive 全 500.0（null 结果，登记为数据点，不解读为效应）。
