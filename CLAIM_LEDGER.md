# CLAIM_LEDGER — goodhart-project PAPER_DRAFT（草稿账本）

> 位置：`goodhart-project/CLAIM_LEDGER.md`（与 `PAPER_DRAFT/OUTLINE.md` 配对）。
> 纪律：每条 claim = 陈述 + 预注册出处 + 判定检验 + 证据指针（含文件行号）+ 状态。
> 状态词只用：`verified` / `inconclusive` / `TODO`。`verified` 仅给已跑通且证据落盘项。
> 不 git add/commit/push；不编造数字。

## V-C2-01 — C.2 脱钩主点（verified）

- 陈述：在 α ∈ {0.5,1.0,1.5,2.0,2.5,3.0} 扫描上，真实分于 α=0.5 达峰（444.0，CI [431.9,456.1]）后跌 86.6%–100.5%；α=1.0 档代理全程最大（1.376）而真实崩至 −2.2（CI [−4.5,0.1]），构成 Goodhart 交叉；按预注册三档记「确认脱钩」，并标注第 3 条件字面偏离。
- 预注册出处：`goodhart-project/prereg/preregistration_c2.md: L33-L37`（H1/H0/H2）；`L63-L68`（三档 + detach 定义）；`L72-L76`（强制附带）。
- 判定检验：峰后跌幅 ≥15% + 95% bootstrap CI 不含 0（配对差按 seed；功效补记 SD 15–16 < 44.6 上限，实际功效 ≈1.0）。
- 证据指针：
  - `goodhart-project/c2/results/summary.csv: L1-L31`（31 行 = 表头 + 30 行；L2-L6 α=0.5 全 500 步存活；L7-L11 α=1.0 塌陷）；sha256 `58b64fc881822af7a8ffb5033146c7a7e94505cf91e58c2322bad7b662192c31`（见 `c2_run.log: L36` / `preregistration_c2.md: L96-L97`）
  - `goodhart-project/c2/results/table1_true_score.csv: L2-L7`（六档 mean/CI/proxy/detach；峰 444.0216，谷 −2.2205）
  - `goodhart-project/c2/results/train_config.json: L2-L24`（α/seeds/100k/λ/limit/prereg_synced=true）
  - `goodhart-project/c2_run.log: L5-L35`（30/30 完成）、`L39`（prereg_synced=True 可判读）
  - `goodhart-project/docs/HANDOVER.md: L581-L604`（三条件核对 + 裁定 (a)）、`L606-L618`（定稿措辞）、`L625-L628`（附带条件）
- 状态：**verified**（可入 §2 结果 + §2.4 定稿措辞；引用措辞必须连带第 3 条件偏离标注一起抄）

## V-ETL-01 — ETL 可复现性（verified：判分可重放；性能数字仅作方法学报告，且列名为误导性命名）

- 陈述：ETL 判分管线可复现（audit 重放 mismatch=0）；性能层面只登记「llama3.1:8b 三族**语义正确率极低**（chain-sort 0/197、ret-path 0/204、stateful-calc 5/213 = 0.0235；整任务全对 0/90）、`first_err_median=0.0` 地板效应」，不升任何能力 claim。
  - ✅ **2026-10-08 已修复口径缺陷**：原 `step_acc` 误用 `valid`（JSON 合法率）；现 `src/analyze_etl.py` 用 `Validator.check_step()` 真值判分，区分 `correct`（语义）与 `parse_ok`（合法）。正文引用一律写「语义正确率 5/213」。
- 预注册出处：无（B/ETL 未预注册；`docs/internal_report_skeleton.md: L34` 明确 [exploratory]；`etl/results/report_snippets.md: L11-L13` 警告未经预注册）。
- 判定检验：`src/audit_replay.py` 重放全部 614 步，mismatch 必须为 0（fail-closed）。
- 证据指针：
  - `goodhart-project/etl/results/logs.jsonl`：`wc -l` = 90 行 = 90 任务（stateful-calc/chain-sort/ret-path 各 30），内含 614 步（实算：`python3 -c` 逐行 `len(steps)` 求和 = 614；`model` 全 `llama3.1:8b`），抽查行段 `L1-L30` / `L31-L60` / `L61-L90` 按族排列
  - 实跑：`python3 src/audit_replay.py`（goodhart-project 根）→ `审计完成: 614 步, mismatch=0 / PASS — 判分可复现`，exit 0（2026-10-08 实测复核通过）
  - `etl/results/table_detach.csv: L1-L4`（表头 + 三行；`step_acc` = 语义正确率 0.0 / 0.0 / 0.0235，`parse_ok` = 合法率同值）
  - **正确率实算（2026-10-08 本次重算）**：`valid` 分族 5/213（stateful-calc）、0/197（chain-sort）、0/204（ret-path），合计 5/614 = 0.8%；**正确步 0/614 = 0.0%；整任务全对 0/90**。与 `docs/HANDOVER.md: L713` 一致
  - 地板效应边界：`first_err_median = 0.0`（三族全 0）→ 无「带病状态上继续推理」样本，误差分解本批无作用面；`docs/HANDOVER.md: L716-L721`（防两误读）、`L728-L732`（Q2/Q4 当前不可分析，出路 = 换更强模型重跑）
  - `goodhart-project/etl/results/report_snippets.md: L5-L9`（自动表）、`L11-L13`（exploratory 声明）
  - `goodhart-project/etl/results/fig_etl_curve.pdf` + `fig_error_decomp.pdf`（存在性引用）
- 状态：**verified**（仅「管线可复现」可入正文方法/结果；性能数字只作描述性报告 + [exploratory]，禁作显著性/机制结论）

## I-Q5-H1 — 惩罚可见性主假设（inconclusive：null，无作用面）

- 陈述：salient vs blind 的 true_score 配对差 mean −0.00035（SD 0.00451），CI 与 0 不可区分；两组 steps_alive 全 500、mean_speed ≈0.107/0.108（限速 28%），罚分合计 0.007/0.008——操纵无作用面，属预注册归因 (a)。
- 预注册出处：`goodhart-project/prereg/preregistration_q5.md: L22-L30`（H1/H2/H0）；`L48-L57`（判读 + 否证只许 (a)/(b)）。
- 判定检验：按 seed 配对差 95% bootstrap CI（2000 次）是否含 0。
- 证据指针：`goodhart-project/q5/results/summary_q5.csv: L1-L11`（表头 + 10 行；L2-L6 blind / L7-L11 salient）；`q5/results/train_config_q5.json: L1-L18`；`preregistration_q5.md: L67-L76`（补记）；`docs/HANDOVER.md: L647-L669`（§13.12 登记）。
- 状态：**inconclusive**（null 结果；入 §4 时只写「本批无差异、归因 (a)」，禁写「可察觉性不重要」一般结论）

## I-Q5-H2 — 惩罚可见性次假设（inconclusive：形式满足、实质不成立）

- 陈述：|mean_speed − limit| 配对差 −0.0013（CI [−0.0016,−0.0009] 不含 0）形式上满足冻结判据，但效应量仅为共同偏差（≈0.269）的 0.5%，两组同为过度保守而非「压线 vs 冲速」。
- 出处/检验同 I-Q5-H1（`preregistration_q5.md: L25-L27` H2；`L50` 检验）。
- 证据指针：同上 + `docs/HANDOVER.md: L658-L661`（双记原文）。
- 状态：**inconclusive**（如实双记；禁作行为学意义断言）

## I-B-MECH — 链式误差分解机制（TODO / exploratory；本批因地板效应**无作用面**）

- 陈述（候选，禁作结论）：cumulative 错误占比随 k 上升 → 带病推理；被压平 → 疑似作弊恢复（记忆真值跳过带病状态）。
- 出处：无预注册（skeleton §3.4 明确 [exploratory]）。
- 检验：未锁定（需先定义 single/cumulative 操作 + 预注册假设检验）。
- ⚠️ **前置阻断（本批不可分析，2026-10-08 补记）**：`first_err_median = 0.0`（三族全 0）→ 模型在第 0 步即错，**不存在「带病状态上继续推理」的样本**；correct 0/614。故 single/cumulative 分解在本批**无作用面**，`fig_error_decomp.pdf` 是地板的形状而非机制形状。解锁需换更强模型重跑（属重跑测量、非新设计）。
- 证据指针：`goodhart-project/etl/results/fig_error_decomp.pdf`（存在性）；`docs/internal_report_skeleton.md: L34-L37`；`docs/HANDOVER.md: L716-L721`（防两误读）、`L728-L732`（Q2/Q4 当前不可分析）；`docs/agi_question_list.md: L9-L10`（Q2/Q4 🟡 地板效应）。
- 状态：**TODO**（本稿 §3.4 只给描述性图 + [exploratory] 段首标 + 地板效应警告，不写因果句）

## I-C2-H2 — α* 稳定性次假设（TODO：删失退化，不作正面证据）

- 陈述：每个 seed 的 true 峰全在 α=0.5（网格最左端），α* 左删失，方差 0 属退化，不能作为 H2 正面证据。
- 出处：`preregistration_c2.md: L37`（H2）；判读见 `docs/HANDOVER.md: L635-L636`。
- 证据指针：`c2/results/summary.csv: L2-L31`（逐 seed 峰位可重算；本账本不另算，只引退化定性）。
- 状态：**TODO**（正文不写 H2 确认；方法 §2.5 可记一笔删失局限）

## I-VENUE — 投稿口径（TODO）

- 陈述：首轮走 control/RL 安全 workshop 打磨，正刊待 Q2/Q4 长链外推 + 多 seed 功效补强。
- 证据：无（决策项，非数据 claim）。
- 状态：**TODO**（OUTLINE 已给一句建议；待作者拍板）

## F-ETL-COLUMN — `step_acc` 列名误导（TODO：待改脚本或论文侧改写，本轮只登记）

- 陈述（非科学 claim，是**报告纪律缺陷**）：`etl/results/table_detach.csv` 与 `report_snippets.md` 的 `step_acc` 列名与实际统计量（`valid` 合法率）不符，存在被下游误读为「模型答对率」的风险。
- 证据：`goodhart-project/src/analyze_etl.py: L40`、`L94`、`L102`、`L114`、`L117`（命名链）；落盘表 `etl/results/table_detach.csv: L1-L4`；独立重算 valid 5/614 vs correct 0/614（本账本「复算命令」节末条）。
- 判定：正文侧已按 V-ETL-01 口径警告改写；**脚本侧是否改名/补列（valid 与 correct 并列）待作者决定**——本轮未改 `src/`，避免动到其他线共用的分析脚本。
- 状态：**TODO**

## 复算命令（本账本数字的重算入口，不手抄）

```bash
# C.2 行数 + sha（期望 31 行 / 58b64fc8…192c31）
wc -l goodhart-project/c2/results/summary.csv && sha256sum goodhart-project/c2/results/summary.csv
# C.2 分档均值重算（应与 table1_true_score.csv L2-L7 一致）
python3 -c "import csv; rows=list(csv.DictReader(open('goodhart-project/c2/results/summary.csv'))); ..."
# ETL 任务/步数/模型（期望 90 / 614 / llama3.1:8b）
python3 -c "import json; ..."
# ETL 审计（期望 614 步 mismatch=0, exit 0）
python3 src/audit_replay.py
# 【2026-10-08 新增】ETL 正确率 vs valid 率实算（期望 correct 0/614、valid 5/614、分族 5/213·0/197·0/204）
python3 -c "
import json
from collections import defaultdict
f=defaultdict(lambda:{'steps':0,'valid':0,'ok':0})
for l in open('goodhart-project/etl/results/logs.jsonl'):
    r=json.loads(l)
    for st in r['steps']:
        d=f[r['family']]; d['steps']+=1; d['valid']+=bool(st.get('valid')); d['ok']+=bool(st.get('ok'))
print({k:dict(v) for k,v in f.items()})"
```

> 上述最后一条是「`step_acc` 实为 `valid` 率」这一发现的复算入口：脚本 `analyze_etl.py`
> 取 `valid` 却命名为 `step_acc`，只跑 `report_snippets.md` 会误读成准确率。
> 交叉验证：`docs/HANDOVER.md: L713`（valid 5/614 = 0.8%、correct 0/614）。
