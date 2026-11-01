# Goodhart 脱钩与链式任务测量

> **这个项目解决什么问题**：把「代理目标与真实目标脱钩」与「链式任务中错误如何累积」
> 从口头论点变成**可测量、可复算、可审计**的证据。前者用 CartPole + PPO 做控制实验
> （真实目标 vs 代理目标，预注册判据），后者用 90 个链式任务 + 614 步真实 LLM 调用
> 测语义正确率与误差分解。两者共享一条纪律：**数字必须能重算，证据链必须闭合**。

**为什么重要**：Goodhart 定律与链式任务可靠性是 AI 对齐与智能体可靠性的核心争论，
但多数讨论停在直觉层面。这里用可复现实验 + fail-closed 门禁把「脱钩发生了」与
「错误会累积」变成可被审计的 claim，而不是断言。

**结果（摘要）**：
- **C.2（脱钩）**：按预注册判据记录为「脱钩确认」——α=1.0 处真实得分降至 −2.22
  （95% CI [−4.52, 0.08]）而代理得分升至峰值 1.376，脱钩比 1.005（`c2/results/table1_true_score.csv`）。
  第 3 条件字面条款未满足（代理峰值后回落），已在论文正文与局限中显式标注，非隐藏。
- **B（链式任务）**：首批（隐藏规则）落在**地板**（correct 0/614）；诊断为**任务设计属性**而非模型能力；
  规则公开 + 换模型重跑后地板解除——step_acc ret-path 0.1912 / stateful-calc 0.1174 / chain-sort 0.1168
  （`etl/results/archive_20261012_public_rules/table_detach.csv`），`audit_replay` 614 步 mismatch=0。
  误差分解得作用面：cumulative 主导（stateful 82% / chain-sort 76% / ret-path 69%），
  错后恢复 46/614，梯度 16.4/8.6/2.1% 与重锚定假说**相容**（探索性，非因果）。

**边界（先说结论，细则见文末「证明什么 / 不证明什么」）**：C.2 是**单环境单算法**的控制实验，
不证明 Goodhart 定律普遍成立；B 是**单模型单跑（n=90）**，全部点估计标 [exploratory]，
不构成模型能力因果结论。

## 目录结构

```
goodhart-project/
├── prereg/
│   ├── preregistration_c2.md        # C.2 预注册（跑之前锁定）
│   └── citation_verification.csv    # 17 条引用核验台账
├── src/
│   ├── gen_tasks.py                 # B: 生成任务 + 隐藏 schedules
│   ├── validators.py                # B: 单向流验证器
│   ├── leak_check.py                # B: 三族泄漏门禁 (fail-closed + --selftest)
│   ├── run_etl.py                   # B: ETL runner
│   ├── audit_replay.py              # B: 事后审计
│   ├── analyze_etl.py               # B: 出图2/图3/表2
│   ├── analyze_c2.py                # A2: 出图1/表1
│   └── _plot_style.py               # 共用绘图样式 (CJK 字体探测)
├── etl/
│   ├── data/tasks/                  # 公开任务（无真值）
│   ├── data/schedules/              # 隐藏真值（模型侧永不可见）
│   └── results/                     # logs.jsonl + 图表
├── c2/
│   └── results/                     # summary.csv + 图1/表1 (训练跑出后生成)
├── docs/
│   ├── internal_report_skeleton.md  # 报告骨架
│   ├── agi_question_list.md         # AGI 问题清单 Q1–Q6
│   ├── leak_audit_checklist.md      # 防泄漏审计清单
│   └── HANDOVER.md                  # 跨会话交接（§0–§12 已补齐；§13 登记与磁盘的差异）
├── templates/
│   └── dsh_probe_template.yaml      # DSH 探测记录模板
├── report/                          # 单页研究状态应用 (离线 HTML; 打开 report/index.html)
├── requirements.txt
└── run_all.sh
```

## 两条铁律

1. **单向流**：`schedules.pkl` 只被 validator 读取，绝不出现在任何 prompt 里。跑前必须过 `leak_check.py` 三族门禁。
2. **可复现**：`audit_replay.py` 的 mismatch 必须为 0；`logs.jsonl` 的 `raw` 字段是逐字原文，禁止转述。

## 运行约定

脚本一律**从仓库根**以 `src/xxx.py` 方式运行，**不要用 `python -m src.xxx`**。
`analyze_c2.py` / `analyze_etl.py` 都 `import _plot_style`（同级模块），
这依赖 `sys.path[0] == src/`——只有 `python3 src/analyze_etl.py` 这种调用方式成立；
换成 `-m` 会变成 `ImportError: No module named '_plot_style'`。

## 当前覆盖范围

`run_all.sh` 只跑 **B 管线**（任务生成 → 门禁 → ETL → 审计 → 分析）。

**C.2 已完成**：`src/train_c2.py` 已与预注册对齐（`prereg_synced=true`，30/30
= 6 档 α × 5 seeds × 100k 步跑满），`analyze_c2.py` 已出图1/表1，判读为
「确认脱钩」（第 3 条件字面偏离的标注与报告定稿措辞见 §13.11；对齐过程见 §13.9）。
`run_all.sh` 仍只覆盖 B 管线、不含 C.2 训练环节（训练需单独跑，见下方"快速开始"），
这**不是遗漏**；C.2 产物在 `c2/results/`（不入库，sha256 锚点记于预注册 §4）。

## 快速开始

```bash
# 本机 Debian 系 Python 3.12 启用了 PEP 668 (externally-managed-environment),
# 直连 pip install 会被系统策略拒绝 (exit 1)。走 venv。
#
# 注意: venv 不能建在仓库内 —— 本仓库目录名含路径分隔符 ':'
# (F:\deepseek), Python 3.11+ 会拒绝: "contains the PATH separator :"。
# 故建在无冒号路径, 并用 --system-site-packages 复用系统的 CUDA torch。
python3 -m venv --system-site-packages /home/liuzewen/.venvs/goodhart
/home/liuzewen/.venvs/goodhart/bin/python -m pip install -r requirements.txt
# 跑训练/脚本时用该 venv 的解释器:
#   /home/liuzewen/.venvs/goodhart/bin/python src/train_c2.py

# 解释器默认 python3; 若你的环境只有 python, 用:
#   PYTHON=python bash run_all.sh
bash run_all.sh
```

接口未接入时会在门禁处停下（`leak_check.py` 以 exit 1 拒判），属**预期行为**。

## 已知问题

- ~~`leak_check.py` 中 `ret-path` 族的随机基线为 `1/len(entries)`，阈值上限可达 0.5。~~
  **已修（KI-001 C，2026-10-07）**：三族 prompt 现在前置公开的 `task_id`（消除
  prompt 碰撞），`ret-path` 基线改为 `1/(同 k 上互异真值个数)`。实测 25% 泄漏者
  判 LEAK，500 个随机种子下 500/500。详见 `docs/known_issues.md`。
- ~~**仍未决**：`chain-sort` 族阈值偏松（25% 泄漏者在该族仍判 CLEAN）；门禁链
  第 3–5 步（run_etl / audit_replay / analyze_etl）因 `model_call` 是占位实现，
  从未在真实数据上跑过。~~ **已结清（2026-10-08）**：`chain-sort` 原记录是**误诊**
  —— 该族隐藏规则只有二值，盲猜者可枚举恰好 2 个候选，真实盲猜率 ≈0.5，故 25%
  泄漏者判 CLEAN 本属正确；基线已改为 `1/(公开信息下可推导候选数)`，并移除 public
  白名单里的 `sort_rule`。门禁链 3–5 步已**端到端打通**：本地 Ollama（llama3.1:8b）
  作为真实 `model_call`，门禁实测三族 0/20 → GATE PASS，ETL 真实跑 614 步、
  `audit_replay` mismatch=0；首批数字呈地板效应（correct 0/614），误差分解无作用面。
  见 `docs/known_issues.md` 与 `docs/HANDOVER.md` §13.10、§13.13。

- `etl/data/schedules/schedules.pkl` 不入库（防 git 通道泄漏真值），只留 `SHA256.txt` 锚点。
  见 `.gitignore`。

## 证明什么 / 不证明什么

**证明（全部可复算，见下节）**

- **C.2 脱钩发生且可判读**：预注册判据下，真实得分在代理峰值处崩溃（α=1.0 → −2.22
  [−4.52, 0.08]），脱钩比 1.005；30/30 组合跑满（6 档 α × 5 seeds × 100k 步）。
- **C.2 的崩溃主要是生存骤降**：90.3% 的真实得分塌缩来自生存步数下降（500.0 → 97.0 步），
  不是超速惩罚项（9.7%）——所以反转是真实的，但**不能**归因于速度奖励扭曲单独。
- **B 链式任务管线端到端闭合**：90 任务 / 614 步，`audit_replay` 重放 mismatch=0（判分可复现）。
- **B 的地板是设计属性而非模型能力**：由迷你实验（KI-002）定位；规则公开后地板解除
  （ret-path 0.1912 / stateful-calc 0.1174 / chain-sort 0.1168）。
- **门禁 fail-closed 且带 RED 反证**：`leak_check.py` 三族泄漏门禁有 `--selftest`，
  注入违规必须判 LEAK（实测 25% 泄漏者判 LEAK，500 随机种子 500/500）。

**不证明（边界，勿过度解读）**

- C.2 **不证明 Goodhart 定律普遍成立**：单环境（CartPole）、单算法（PPO）、单代理目标。
  换环境/算法/目标需要重跑，不能外推。
- C.2 **不证明超速惩罚与反转的因果**：生存骤降主导（90.3%），超速项仅 9.7%，
  二者在观测数据上不分离——这是记录的事实，不是速度扭曲单独致反转的证据。
- B **不证明「规则公开提升正确率」的因果**：v2 同时换了模型（llama3.1:8b→qwen2.5:3b）与规则可见性，
  两因子一起动，提升**不能**归因于规则公开单独。chain-sort 0.1168 与迷你实验 P 臂 0/12 不一致，
  需强模型复测才能归因，不得据此推翻。
- B **全部是单模型单跑点估计**（n=90），标 [exploratory]：Q2 恢复梯度、Q4 短链外推
  都只是**相容性/现象学证据，非因果**。Q4 本批不可判（逐 k 样本仅 4–30，chain-sort R²≈0）。
- **不做模型横向比较**：不同模型（3b/7b/8b）在不同批次的数字不可直接比较，
  除非控制配置与规则可见性。

## 复算

所有数字都能从仓库内文件重取，命令如下（在仓库根目录，用 `goodhart` venv 解释器）：

```bash
V=/home/liuzewen/.venvs/goodhart/bin/python   # 或用你环境里的解释器

# C.2 表1：真实/代理得分、脱钩比（6 档 α）
$V -c "import csv; print(list(csv.DictReader(open('c2/results/table1_true_score.csv'))))"

# C.2 生存/速度分解：90.3% vs 9.7%（预注册要求的两分量）
# 来源 summary.csv 的 steps_alive / mean_speed 列；论文正文给出 500.0→97.0 步
$V -c "import csv; rows=list(csv.DictReader(open('c2/results/summary.csv'))); print(len(rows),'rows')"

# B 全量 ETL：614 步、valid/correct 计数、分族 step_acc（从 archive 表逐字取）
$V -c "
import json
tot=0
for line in open('etl/results/logs.jsonl'):
    line=line.strip()
    if line:
        tot+=len(json.loads(line)['steps'])
print('steps=',tot)"
cat etl/results/archive_20261012_public_rules/table_detach.csv

# B 判分可复现：重放判分，mismatch 必须为 0（默认日志 logs.jsonl）
$V src/audit_replay.py            # 期望输出「614 步, mismatch=0」「PASS — 判分可复现」

# 门禁 RED 反证：注入 25% 泄漏者必须判 LEAK
$V src/leak_check.py --selftest
```

**证据链纪律**：`logs.jsonl` 的 `raw` 字段是逐字原文（禁止转述）；`schedules.pkl` 不入库
（真值只存 SHA256 锚点），杜绝 git 通道泄漏。重算不一致 = 该数字不可信，按 AGENTS.md 铁律 1 阻塞。