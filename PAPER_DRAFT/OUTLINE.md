# PAPER_DRAFT / OUTLINE — Goodhart 脱钩与链式任务测量（草稿，未投稿）

> 状态：开稿草稿（2026-10-08）。数字一律来自落盘证据，禁止手抄/外推。
> 仓库内相对路径：`goodhart-project/PAPER_DRAFT/OUTLINE.md`；账本见 `goodhart-project/CLAIM_LEDGER.md`。
> 不 git add/commit/push。

## 候选标题（1 个主标题 + 1 个备用）

- 主标题：Proxy–True Decoupling under Speed-Reward Distortion in CartPole PPO, with a Reproducible Chained-Task ETL Audit
- 备用标题：When Faster Is Worse: A Preregistered Goodhart Decoupling Curve (α = 0.5–3.0) and Chain-Task Error Decomposition

## 摘要草稿（150 字级，最后重写；本轮只定事实骨架）

问题：在速度类代理目标 `speed^α` 下，代理分数与真实目标（存活 − 超速惩罚）是否脱钩。
方法：CartPole 上 6 档 α × 5 seeds × 100k 步 PPO（预注册锁定）+ 三族链式 ETL（llama3.1:8b，90 任务 / 614 步，audit 重放）。
数据支持的结论：真实分于 α=0.5 达峰 444.0（CI [431.9, 456.1]）后跌 86.6%–100.5%，α=1.0 档代理全程最大（1.376）而真实崩至 −2.2，判「确认脱钩」（第 3 条件字面偏离已标注）；ETL 判分可复现（mismatch=0），步准确率极低且属探索性。
限制：5 seeds / 单环境 / ETL 未过预注册假设检验；Q5 惩罚可见性 null（无作用面）。

## 四节提纲（每节：写什么 + 证据指针 + 文件行号）

### §1 引言与问题（≈500 字；对应 skeleton §1）

- 写什么：测量/代理两条裂缝各 2 句 + 1 例；声明本稿只处理代理裂缝（C.2）+ 测量裂缝（B/ETL），不可证伪裂缝留给 Q3 文档。
- 证据指针（框架，不产数字）：
  - `goodhart-project/docs/internal_report_skeleton.md: L15-L17`（三裂缝分工：只处理前两条）
  - `goodhart-project/docs/agi_question_list.md: L6-L12`（Q1 代理/Q2·Q4 测量活跃队列；Q3 纯写作）
  - `goodhart-project/prereg/citation_verification.csv`（**17/17 已填实、0 留空**（2026-10-11 复核；此处原写"13 填实/4 留空"已过期）；`zotero_key` 17 行仍未核，见 `docs/HANDOVER.md` §13.4）

### §2 C.2 Goodhart 脱钩实验（≈1700 字；对应 skeleton §2）

- 写什么：
  - 2.1 设计：真实 `true_score = steps_alive − λ·max(0, speed − speed_limit)` vs 代理 `proxy_score = mean(speed)^α`，speed=`|x_dot|`；α ∈ {0.5,1.0,1.5,2.0,2.5,3.0}；每档 5 seeds（42–46）；PPO 默认超参 100k 步；评估确定性策略 50 episodes。
  - 2.2 预注册判读：`detach_ratio = 1 − true/true_max`；确认脱钩 = 峰后跌 ≥15% 且 95% CI 不含 0；部分 5%–15%；否证 = 单调不减；强制附带 steps_alive + mean_speed。
  - 2.3 结果：表 1 + 图 1（只报脚本输出）。
  - 2.4 讨论：三档措辞不越档；本批记「确认脱钩」+ 第 3 条件字面偏离标注（定稿措辞照抄 HANDOVER §13.11）。
  - 2.5 限制：天花板/未调参/5 seeds 功效（实测 SD 15–16 < 44.6 上限，实际功效 ≈1.0，但只覆盖本判据）。
- 证据指针（行号均为当前落盘实测）：
  - 预注册假设/变量：`goodhart-project/prereg/preregistration_c2.md: L33-L37`（H1/H0/H2）；`L42-L48`（真/代理/speed/α 网格/控制）；`L50`（冻结 λ=1.0 / limit=0.376 / 100k）
  - 判读规则：`preregistration_c2.md: L63-L68`（detach 定义 + 三档）；`L72-L76`（强制附带）；`L81-L86`（功效实算 SD ≤44.6）；`L88-L98`（跑后补记：配对差 446.2±15.1 / 432.7±16.0，sha 见 L96-L97）
  - 训练完成：`goodhart-project/c2_run.log: L5-L34`（30 次 `[run]`）；`L35`（写入 30 行）；`L36`（sha256 = 58b64fc8…192c31）；`L39`（prereg_synced=True）
  - 原始曲线：`goodhart-project/c2/results/summary.csv: L1`（表头）；`L2-L6`（α=0.5，steps_alive 全 500.0）；`L7-L11`（α=1.0，true 全 ≤1.65，proxy 全 ≥1.33）；`L12-L16`（α=1.5）；`L17-L21`（α=2.0）；`L22-L26`（α=2.5）；`L27-L31`（α=3.0）；共 31 行 = 表头 + 30 行
  - 聚合表：`goodhart-project/c2/results/table1_true_score.csv: L1`（表头）；`L2`（0.5: 444.0216 [431.894,456.149] proxy 0.6429 detach 0.0）；`L3`（1.0: −2.2205 [−4.519,0.081] proxy 1.3762 detach 1.005）；`L4`（1.5: 39.4061 [31.392,46.777]）；`L5`（2.0: 59.4365 [47.910,71.084]）；`L6`（2.5: 21.3227 [16.043,30.021]）；`L7`（3.0: 11.341 [10.459,12.472]）
  - 配置：`goodhart-project/c2/results/train_config.json: L2-L9`（α 网格）；`L10-L16`（seeds 42–46）；`L17-L19`（100000/1.0/0.376）；`L24`（prereg_synced true）；`L25`（训练 dense `speed^α` vs 报告 `mean(speed)^α` 偏离声明）
  - 图：`goodhart-project/c2/results/fig1_detach_curve.pdf`（analyze_c2 产物，二进制，只引存在性）
  - 判读裁定与定稿措辞：`goodhart-project/docs/HANDOVER.md: L570-L580`（表 1 六档数据）；`L581-L594`（三条件逐条核对：条件 1/2 满足，条件 3 字面不满足、意图满足）；`L596-L604`（裁定 (a) 确认脱钩理由）；`L606-L618`（报告 2.4 定稿措辞，可直接抄入）；`L625-L628`（附带条件）；`L630-L636`（exploratory：非单调/H2 删失，禁作结论）

### §3 B/ETL 链式任务与误差分解（≈2200 字；对应 skeleton §3）

- 写什么：
  - 3.1 三任务族（chain-sort / stateful-calc / ret-path；详表移附录）。
  - 3.2 无泄漏 validator：单向流（schedules 只被 validator 读）+ 门禁（leak_check）+ 事后 audit（mismatch 必须 0）；本批 ETL 真实模型调用已跑（llama3.1:8b），门禁链 3–5 步 stub 冒烟见 HANDOVER §13.10(b)。
  - 3.3 结果：图 2 + 表 2（只报脚本输出）。✅ **口径已修复（2026-10-09）**：`src/analyze_etl.py` 现用 `Validator.check_step()` 真值判分，`table_detach.csv` 分列 `step_acc`（语义正确率）与 `parse_ok`（JSON 合法率）——旧“`step_acc`=合法率”缺陷已消除。当前实测：chain-sort 正确 0/197、ret-path 0/204、stateful-calc 正确 **5/213 = 0.0235**（合计正确 5/614 = 0.8%；整任务全对 0/90）。旧注记“正确步 0/614”作废（系误读，见 `RESULTS_DRAFT.md` §4.2）。
  - 3.4 [exploratory] 误差分解：single vs cumulative；cumulative 随 k 上升 vs 被压平（疑似作弊恢复）——本节最有原创性但**未经预注册**，段首强制标 [exploratory]。⚠️ 且本批**地板效应**：`first_err_median = 0.0`（三族全 0）= 模型几乎在第 0 步就错，不存在「带病状态上继续推理」的样本 → single/cumulative 分解**在本批无作用面**，`fig_error_decomp.pdf` 的曲线是**地板的形状、不是机制的形状**，本节不得作机制解读（`docs/HANDOVER.md: L716-L721`）。
  - 3.5 限制：validator 覆盖度 / 仅三族 / 模型版本注明（llama3.1:8b）/ **地板效应导致 Q2（作弊恢复触发条件）与 Q4（短链外推长链）当前不可分析**——出路是换更强模型重跑（属重跑测量，非新设计），见 `docs/HANDOVER.md: L728-L732` 与 `docs/agi_question_list.md: L9-L10`。
- 证据指针：
  - 原始记录：`goodhart-project/etl/results/logs.jsonl`：共 90 行（`wc -l` = 90；`stateful-calc` 30 + `chain-sort` 30 + `ret-path` 30），合计 614 步，`model` 全为 `llama3.1:8b`（实算命令见账本 V-ETL-02；抽查 `L1-L30` 为 stateful-calc、`L31-L60` 为 chain-sort、`L61-L90` 为 ret-path）
  - 可复现性：`goodhart-project/src/audit_replay.py` 实跑输出 `审计完成: 614 步, mismatch=0 / PASS — 判分可复现`（exit 0；2026-10-08 实测复核通过）
  - 门禁真实跑（非 stub）：`goodhart-project/etl/results/gate_run.log: L1-L5`（非空，328 字节）——`model=llama3.1:8b`、`n_per_family=20` 全量、三族均 CLEAN、`GATE: PASS — 可启动 run_etl`、`EXIT=0`；⚠️ 三族 CLEAN 是因为**实测准确率为 0**（stateful-calc 0/20、chain-sort 0/20、ret-path 0/20）而非能力达标，引用时必须写明，不得读成「模型通过门禁能力线」。对应 `docs/HANDOVER.md: L682`（§13.13 接入方式：`src/ollama_model.py` → 本地 Ollama `/v1/chat/completions`，temperature=0、timeout 60s、失败重试 1 次后 `__UNTESTED__`，`leak_check` 计 failed 且全失败仍 GATE FAIL = fail-closed 语义在真实接口下保持）；`L697-L703`（三族门禁实测表）
  - 聚合表：`goodhart-project/etl/results/table_detach.csv`（表头 `model,family,step_acc,parse_ok,first_err_median`）：chain-sort 0.0/0.0、ret-path 0.0/0.0、stateful-calc **0.0235/0.0235**（`step_acc` = 语义正确率已修复，见 3.3）
  - ~~**正确率实算（本次新增，直接从 logs.jsonl 重算）**：`valid` 计数 stateful-calc 5/213 = 0.0235、chain-sort 0/197、ret-path 0/204 → 合计 valid 5/614 = 0.8%；**正确步 0/614 = 0.0%；整任务全对 0/90**。与 `docs/HANDOVER.md: L713`（"步级合计：valid 5/614（0.8%），correct 0/614"）一致~~ **已 superseded**：上条系旧口径误读；真值判分后 stateful-calc 正确 5/213（合计 5/614），`RESULTS_DRAFT.md` §4.2 为准。`HANDOVER.md: L713` 为历史会话记录，不改（与新表矛盾处以新表为准）。
  - 自动片段：`goodhart-project/etl/results/report_snippets.md`（三行表已与新口径一致；`L11-L13` exploratory + 未经预注册警告）
  - 图：`goodhart-project/etl/results/fig_etl_curve.pdf` + `fig_error_decomp.pdf`（analyze_etl 产物，只引存在性）
  - 任务/真值隔离：`goodhart-project/etl/data/tasks/tasks.jsonl`（公开任务，无真值）；`etl/data/schedules/SHA256.txt`（锚点 `6c78350d…`）；门禁三处结清见 `docs/HANDOVER.md: L453-L562`（§13.10：chain-sort 不可判别/ stub 冒烟 T1–T4 / schedules fail-closed 修法）
  - 报告纪律：`docs/internal_report_skeleton.md: L28-L38`（§3 结构 + [exploratory] 强制标 + 数字只准来自脚本）

### §4 结论、限制与下一步（≈400–600 字；对应 skeleton §5–§6）

- 写什么：三裂缝触及/空白；只列一个下一步（C.2 确认脱钩 → Q5 已跑完但 null（归因 (a)）；**Q6 已于 2026-10-08 由作者拍板解冻**，但解冻 ≠ 自动开工，需全新任务设计、另立项防「第二个计划过载」；ETL 低准确率只作方法学报告，不升 claim）。
- 证据指针：
  - Q5 已跑完（null 亦是数据）：`goodhart-project/q5/results/summary_q5.csv: L1`（表头）+ `L2-L6`（blind 5 seeds，true ≈499.99，steps_alive 全 500.0，mean_speed ≈0.107）+ `L7-L11`（salient 同量级）；`q5/results/train_config_q5.json: L1-L18`（2 arm × 5 seeds × 100k，prereg_synced true）
  - Q5 预注册/判读：`goodhart-project/prereg/preregistration_q5.md: L22-L30`（H1/H2/H0）；`L48-L54`（判读 + 否证只许归因 (a)/(b)）；`L67-L76`（补记：配对差 −0.00035±0.00451，罚分合计 0.007/0.008，归因 (a)，sha L74-L75）
  - Q5 判读登记：`docs/HANDOVER.md: L647-L669`（§13.12：H1 未确认、H2 形式满足实质不成立、归因 (a) 成立、禁外推）；`L678-L680`（Q6 解冻条件已满足、当时**待作者决定**——此指针已过时，见下）；`L733-L734`（**以本条为准**：Q6 作者已拍板解冻，解冻 = 允许立项设计 ≠ 自动开工，为防计划过载设计另立项、不并入现有线）；`L728-L732`（Q2/Q4 当前不可分析：本批 correct=0 无部分正确步可分解，出路是换更强模型重跑而非新设计）
  - AGI 清单：`docs/agi_question_list.md: L8`（Q1 ✅ 已产出）；`L12`（Q5 ✅）；`L9-L10`（Q2/Q4 🟡 地板效应 correct 0/614，当前不可分析）；`L17`（Q6 **🔓 已解冻 2026-10-08，作者拍板**）；`L26`（Q6 违纪线：未解冻前「顺手先做一点」即违纪）
  - 结论纪律：`docs/internal_report_skeleton.md: L49-L53`（下一步只列一个）；`L4-L8`（写作纪律：禁手抄/禁越档/引用待核）

## Venue 建议（一句）

建议投控制/RL 安全方向的 workshop 或安全 track 首轮打磨（例如 NeurIPS/ICML 的 Safe RL / Safe Control 类 workshop），正刊待 Q2/Q4 长链外推与多 seed 功效补强后再定。

## 不写什么（防越档清单）

- 不写 H2（α* 稳定性）正面结论：α* 左删失于网格最左端（每个 seed 峰全在 α=0.5），方差 0 属退化（HANDOVER L635-L636）。
- 不写 ETL 误差分解因果结论：未经预注册，一律 [exploratory]。
- 不写 Q5「可察觉性不重要」一般结论：预注册禁令（preregistration_q5.md L51-L54；HANDOVER L666）。
- 不写任何显著性断言超出 CI/配对差已报范围。**引用已解除 [待核] 限制**（2026-10-11：`citation_verification.csv` 17/17 填实并经 reference_checker + arXiv/Crossref 双源独立复核，14 found / 3 partial / 0 not_found；`paper/refs.bib` 17 条已转写入稿）。剩余约束只剩 `zotero_key` 未核，以及 §13.4 红线三条（Goodhart 原版页码、三裂缝无外部出处、Goodhart 缩略语实为 Strathern）。
