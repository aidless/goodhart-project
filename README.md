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
│   └── HANDOVER.md                  # 跨会话交接（需手工补齐 §0–§12）
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

**C.2 目前有预注册与分析脚本，但缺训练脚本**——产出 `c2/results/summary.csv` 的
CartPole+PPO 训练环节尚未编写。所以 `run_all.sh` 跑完不会出现图1，这**不是遗漏**，
是下一步工作项。`analyze_c2.py` 在缺 `summary.csv` 时会以缺文件退出，属预期。

## 快速开始

```bash
# 本机 Debian 系 Python 3.12 启用了 PEP 668 (externally-managed-environment),
# 直连 pip install 会被系统策略拒绝 (exit 1)。走 venv:
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

# 解释器默认 python3; 若你的环境只有 python, 用:
#   PYTHON=python bash run_all.sh
bash run_all.sh
```

接口未接入时会在门禁处停下（`leak_check.py` 以 exit 1 拒判），属**预期行为**。

## 已知问题

- `leak_check.py` 中 `ret-path` 族的随机基线为 `1/len(entries)`，阈值上限可达 0.5。
  这意味着命中率仅约 25% 的泄漏者也可能被判 CLEAN。**判据过松**，待修。
  见 `docs/leak_audit_checklist.md`。
- `etl/data/schedules/schedules.pkl` 不入库（防 git 通道泄漏真值），只留 `SHA256.txt` 锚点。
  见 `.gitignore`。