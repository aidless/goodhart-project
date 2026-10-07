# Goodhart 脱钩与链式任务测量

两个实验的工程骨架：**C.2**（Goodhart 脱钩，CartPole + PPO，真实目标 vs 代理目标）与 **B**（链式任务 ETL 与误差分解）。

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

**C.2 的训练脚本已存在（`src/train_c2.py`），但它尚未与预注册对齐，不能开跑。**
该文件自己标了 `PREREG-SYNC` 占位，并且**其实现与预注册/交接文档描述的设计不一致**
（预注册要求 `SpeedLimitedCartPole` + 代理 `speed^α`；实现是纯 CartPole + 代理
`obs[0]`）。`run_all.sh` 也不包含 C.2 训练环节，所以跑完不会出现图1，这**不是遗漏**。
`analyze_c2.py` 在缺 `summary.csv` 时会以缺文件退出，属预期。
详见 `docs/HANDOVER.md` §13.2、§13.8。

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
- **仍未决**：`chain-sort` 族阈值偏松（25% 泄漏者在该族仍判 CLEAN）；门禁链
  第 3–5 步（run_etl / audit_replay / analyze_etl）因 `model_call` 是占位实现，
  从未在真实数据上跑过。见 `docs/leak_audit_checklist.md`。
- `etl/data/schedules/schedules.pkl` 不入库（防 git 通道泄漏真值），只留 `SHA256.txt` 锚点。
  见 `.gitignore`。