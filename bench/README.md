# Bench — Goodhart 脱钩与链式任务基准

> 本目录登记 goodhart-project 的真实基准（benchmark）数据与复跑命令。
> 每个数字都能从仓库内 `etl/results/` 或 `c2/results/` 的落盘文件重取，命令列在下方。
> 这是**测量**不是断言：全部数字为单次/单模型点估计，标注 `[exploratory]`。

## 基准 1 — 链式任务语义正确率（ETL 基准，跨模型 × 规则可见性）

| 批次 | 模型 | 规则可见性 | chain-sort | ret-path | stateful-calc | 正确步 | 总步 | 来源 |
|---|---|---|---|---|---|---|---|---|
| 首批（地板） | llama3.1:8b | 隐藏 | 0.0000 | 0.0000 | 0.0235 | 0 | 614 | `etl/results/archive_20261008_hidden_rules/table_detach.csv` |
| 二批（规则公开） | qwen2.5:3b | 公开 | 0.1168 | 0.1912 | 0.1174 | 59 | 614 | `etl/results/archive_20261012_public_rules/table_detach.csv` |
| 二批强模型 | qwen3.5:7b | 公开 | 0.0863 | — | — | — | — | `etl/results/logs_chainsort_v2_showstate_qwen7b.jsonl` |

- **判读**：首批正确步 0/614（地板）；规则公开 + 换模型后地板解除（ret-path 0.1912 最高）。
- **边界**：二批同时动了「规则可见性」与「模型」两个因子，**不能**归因于规则公开单独；
  7b 复测 0.0863 ≤ 3b 0.1168，「换强模型」腿**否证**，剩余路径 = 改任务设计（见 `docs/known_issues.md`）。
- **判分可复现**：`audit_replay` 重放 614 步，mismatch=0（`src/audit_replay.py`）。

## 基准 2 — 脱钩曲线（C.2 控制实验基准）

| 参数 | 值 | 来源 |
|---|---|---|
| 环境/算法 | CartPole / PPO | `c2/results/train_config.json` |
| 扫描 | α ∈ {0.5,1.0,1.5,2.0,2.5,3.0} × 5 seeds × 100k 步 = 30 组合 | `c2_run.log` L5-L35 |
| 真实得分峰值 | 444.0（CI [431.9,456.1]）@ α=0.5 | `c2/results/table1_true_score.csv` |
| 代理峰值处真实得分 | −2.22（CI [−4.52,0.08]）@ α=1.0 | 同上 |
| 脱钩比 | 1.005 | 同上 |

- **判读**：真实得分在代理峰值处崩溃，按预注册三档记「脱钩确认」（`prereg/preregistration_c2.md`）。
- **边界**：单环境单算法，**不证明** Goodhart 定律普遍成立。

## 复跑命令（在仓库根，用 `goodhart` venv）

```bash
V=/home/liuzewen/.venvs/goodhart/bin/python

# 基准 1：判分可复现（mismatch 必须为 0）
$V src/audit_replay.py

# 基准 1：分族 step_acc 逐字取
cat etl/results/archive_20261012_public_rules/table_detach.csv

# 基准 1：总步数实算（应得 614）
$V -c "
import json
tot=0
for line in open('etl/results/logs.jsonl'):
    line=line.strip()
    if line: tot+=len(json.loads(line)['steps'])
print('steps=',tot)"

# 基准 2：六档 mean/CI/proxy/detach 逐字取
$V -c "import csv; print(list(csv.DictReader(open('c2/results/table1_true_score.csv'))))"
```

## 门禁

- `leak_check.py` 三族泄漏门禁为 **fail-closed**：注入 25% 泄漏者必须判 LEAK，
  `--selftest` 500 随机种子 500/500（RED 反证通过）。见 README「证明什么 / 不证明什么」。
