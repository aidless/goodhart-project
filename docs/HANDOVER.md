# 交接文档 — Goodhart 脱钩与链式任务测量项目
版本: v1.0 | 交接日期: 2026-10-07 | 状态: 代码全部未经运行，等待首次执行

---

> **搬运说明（非原文，由搬运者补记，读完后可删除）**
>
> 本文件此前是空占位（§0–§12 只有标题）。本次由外部会话从对话记录中
> **逐字搬运**，来源：`__New chat....txt` 第 4865–5099 行（该条消息末尾自述
> "交接文档到此完整。全文共 12 节"）。
>
> 搬运时修掉了源文本的两处**渲染损伤**（非内容改动）：
> 1. §9 代码块里 "第 0 步" 被重复了一次，并夹入一个多余的行内 ` ```bash `；
>    这里只保留一份，代码块正常闭合。
> 2. 因上面那个未闭合的代码块，§10/§11/§12 的标题在源文本里退化成了
>    "10. …" / "11. …" / "12. …"；这里恢复为 `## 10.` / `## 11.` / `## 12.`。
>
> 除以上两处，正文未做任何改写。
>
> **另一件必须记录的事**：同一份对话记录在第 9009 行还写着
> "这一份我必须直说：我没有 §0–§12 的正文……别让一个看起来像回事的空壳
> 被当成已完成的交接文档"。这与第 4865–5099 行**实际存在**的全文直接矛盾。
> 也就是说，"交接文档缺失"这个判断本身是错的，而这个错误结论正是导致
> 空占位长期存在的原因。两个行号都留在这里，供后人复核。

---

## 0. 给接手人的第一段话

这个项目研究两件事：(1) 代理奖励失真如何导致可测量的目标脱钩（Goodhart 效应，
强化学习实验）；(2) 语言模型在多步链式任务中误差如何累积、以及模型是否会用
"记忆的真值"跳过带病状态（API 实验）。

贯穿全部工作的方法论立场：**把占位符当数据、把未核验引用当事实、把没跑过的
代码当能跑的代码，是本项目要防的三个坏习惯。** 所有防线都为此设计。

三条主线目前**全部卡在"执行"上**，没有任何一条卡在设计上。

---

## 1. 目录结构与文件职责

goodhart-project/
├── README.md                        # 总入口（三条主线 + 唯一优先级）
├── run_all.sh                       # 门禁链: gen_tasks → leak_check → run_etl → audit → analyze
├── prereg/preregistration_c2.md     # C.2 预注册【锁定后正文不得改】
├── src/
│   ├── goodhart_c2.py               # C.2 实验代码（含待执行补丁 P1，见 §3.3）
│   ├── analyze_c2.py                # C.2 分析 → 图1 detach_curve.pdf / 表1
│   ├── gen_tasks.py                 # B: 生成任务 + 隐藏 schedules
│   ├── validators.py                # B: 单向流验证器
│   ├── leak_check.py                # B: 泄漏探针 v2（三任务族统一接口）
│   ├── run_etl.py                   # B: ETL runner，落盘 etl/results/logs.jsonl
│   ├── audit_replay.py              # B: 事后重放审计，mismatch 必须为 0
│   └── analyze_etl.py               # B: 分析管线（含容错字段读取）
├── etl/data/{tasks,schedules}/      # ⚠️ 物理隔离，见 §4.2
├── etl/results/logs.jsonl           # B 原始记录
├── docs/
│   ├── internal_report_skeleton.md  # 10页报告骨架，字数预算已压至 6050
│   ├── agi_question_list.md         # Q1–Q6，Q6 处于冻结态
│   ├── leak_audit_checklist.md      # 防泄漏审计清单（硬约束，非建议）
│   └── HANDOVER.md                  # 本文件
├── templates/dsh_probe_template.yaml# 探测记录标准（逐字原文纪律）
└── citation_verification.csv        # 17 行引用清理队列（见 §5）

---

## 2. 项目框架：三条裂缝

所有研究问题都从三个框架性裂缝衍生：
1. **测量裂缝** — 指标与真目标的偏差（B/ETL 实验针对此）
2. **代理裂缝** — 代理奖励与真目标的偏差（C.2 实验针对此）
3. **不可证伪裂缝** — 只做概念澄清，不产数据（对应 AGI 清单 Q3）

---

## 3. 主线一：C.2 Goodhart 脱钩实验

### 3.1 设计（已锁定于预注册，此处为摘要）
- 环境: CartPole-v1 + 改造版 SpeedLimitedCartPole
  （真实目标 = 存活 − 超速惩罚；代理目标 = 速度^α）
- 六组: G1 真实奖励训练（对照）；G2 仅代理奖励；G3–G6 代理失真梯度
  （G3 α=1.5、G4 α=2.0、G5/G6 在 G3/G4 基础上叠加噪声）
- 每组 5 seeds（42–46），timesteps=40000，PPO（SB3），**不调参**——
  绝对分数无意义，只做组间比较
- 评估: 确定性策略，每模型 50 episodes，**只报真实奖励得分**
- 核心量: detach_ratio = 各组真实得分 / G1 真实得分

### 3.2 假设与判读（预注册第 1、3 节，正文为准）
- H1: G3–G6 的 detach_ratio < 0.5（Goodhart 显现）
- H2: G4 < G3（失真强度单调性）
- H3: G5 < G3 且 G6 < G4（噪声加剧脱钩）
- 三档结论措辞已写死：全确认 / 弱脱钩（不夸大）/ 否证
- **否证时只允许两种归因，二选一**：
  (a) 冲突设计强度不足 → 加大 speed_penalty/α 重跑，属新实验、需新预注册
  (b) 冲突存在但 PPO 未利用漏洞 → 检查 G3–G6 训练曲线代理奖励是否持续高于 G2
- **禁止**: 否证后宣称"Goodhart 在此设置不适用"并当结论发表
- 天花板规则: 若 G1 均值 > 490/500，本批作废，max_episode_steps 改 1000 重跑

### 3.3 已知未决项
- **补丁 P1 未执行**: goodhart_c2.py 中 F1 处残留草稿行 `penv = ...`，
  删除该行、替换为纯数值断言。执行方式见对话记录"补丁 P1"节。
- **F2–F5 为概率性预判**（可能的失败点清单），以首次运行 traceback 为准。
  首跑命令: `python src/goodhart_c2.py`，输出全文贴回给助手。
- 验收状态: **一次都没跑过**。语法检查也未做过。

---

## 4. 主线二：B/ETL 链式任务测量

### 4.1 设计摘要
- 三个任务族: chain-sort / stateful-calc / ret-path
- 每族生成隐藏 schedule（真值链），模型逐步执行，validator 判分
- 核心观测量: 步准确率随 k 的衰减曲线 + **误差分解**
  （single = 单步错；cumulative = 带病状态上继续推理导致的错）
- **关键卖点**: cumulative 比例随 k 上升 → 模型在带病状态上继续推理；
  cumulative 被压平 → 疑似"作弊恢复"（用记忆真值跳过带病状态）。
  此分析标 [exploratory]（预注册只覆盖 C.2）。

### 4.2 防泄漏机制（三重，缺一即失效）
1. **物理隔离**: tasks/ 与 schedules/ 分目录；schedules.pkl 绝不进 prompt
2. **门禁**: run_all.sh 用 `set -e`，leak_check FAIL 则 run_etl 不会执行
   - 泄漏判定: 命中率 > max(0.02, 2.5 × 随机基线)
   - 基线: stateful-calc ≈ 0.02 / chain-sort ≈ 1/L! / ret-path ≈ 1/条目数
3. **事后审计**: audit_replay.py 重放全部分数，mismatch > 0 即非零退出

**这不是建议，是硬约束。** 任何一环被绕过（如为省事把两个目录合并），
泄漏立即重现。

### 4.3 已知未决项（接手人必读）
以下三处依赖原环境字段名，接手时**先核对再跑**：
- `gen_tasks.py` 是否有 `apply_chain_sort(seq, i, sort_rule)` 函数；
  没有则加 5 行或让 ChainSortProbe 内联该逻辑
- 任务字段名是否为 init_seq / sort_rule / entries / ptr / values / x0 / ops
  （leak_check v2 按此写，不符则各改 2–3 处）
- run_etl 落盘字段：analyze_etl 已做容错读取（valid/correct、
  err_type/error_class/err 均可），但 family 字段若缺失会回退到
  task_id 前缀解析——确认前缀解析是否符合你的命名习惯

---

## 5. 主线三：引用核验（唯一的文献卫生线）

- 现状: `citation_verification.csv` 共 17 行，其中约 14 条进入工作队列
- **全部元数据默认 ⚠️（未核验）**——它们产生于助手记忆，未经任何检索确认
- 工作流程: 逐条在浏览器确认 DOI/标题/作者/年份 → 修正或删除 →
  同步清理 Zotero 中对应条目
- 预算: 约 1 小时
- **红线**: 在此完成之前，CSV 中任何条目不得进入正式写作的参考文献
- CSV 中的搜索模板链接本身也未经确认可达，用前先点一遍

---

## 6. 辅助交付物状态

| 交付物 | 状态 | 使用纪律 |
|---|---|---|
| preregistration_c2.md | 内容完整，**日期未填未锁定** | 必须在 C.2 首跑前填写并锁定；跑后正文禁改，事后想法只进"探索性附加"节 |
| analyze_etl.py | 完整 + 容错读取 | 等 B 数据，勿提前手抄数字进报告 |
| leak_check.py v2 | 方法体已填实 | 依赖 §4.3 字段确认 |
| dsh_probe_template.yaml | 完整 | raw 字段只准逐字粘贴，禁止转述；ETL 调用顺手写精简版 |
| agi_question_list.md | 完整 | **Q6 冻结**，解冻条件 = Q1–Q5 至少两条出数据；任何"顺手先做一点"视为违纪 |
| internal_report_skeleton.md | 完整，字数预算 6050 | 2.3/3.3 的数字只准来自脚本输出，禁止手抄；未预注册分析标 [exploratory] |

---

## 7. 当前状态总表

| 事项 | 状态 | 卡点 |
|---|---|---|
| C.2 代码 | 已写，含补丁 P1 待执行 | **从未运行** |
| C.2 预注册 | 文本完成 | 未填日期、未锁定 |
| B 全套代码 | 已写 | **从未运行**；字段名待核对 |
| 防泄漏三重机制 | 已设计+代码 | 未实测 |
| 引用核验 | CSV 已建 | 17 条全部未核验 |
| 分析管线 | 已写 | 等数据 |
| DSH 模板 / AGI 清单 / 报告骨架 | 已写 | 无阻塞 |

---

## 8. 风险清单（接手人最可能踩的坑）

1. 跑了 C.2 才看预注册 → 判读规则失效，防自欺效力归零。
   **预注册必须在首跑前锁定。**
2. 为省事合并 tasks/ 与 schedules/ 目录 → 泄漏防线物理失效。
3. 否证 H1 后顺手改超参重跑并报告"最终"结果 → 违反预注册，
   属于新实验，必须新预注册。
4. 把 CSV 里 ⚠️ 条目直接写进论文 → 引用污染。
5. Q6 解冻冲动 → 已写死条件，见 §6。
6. 手抄数字进报告 → 与脚本输出不符时无从追溯。

---

## 9. 快速启动（接手后按序执行）

```bash
# 第 0 步: 落盘（若目录未建）
bash setup_goodhart.sh        # 建树 + run_all.sh 门禁

# 第 1 步: 审预注册, 填今天日期, 锁定（唯一"过期作废"的动作, 先做）
$EDITOR prereg/preregistration_c2.md

# 第 2 步: 核对字段名（§4.3 三处）, 按实际环境改 2–3 处

# 第 3 步: C.2 首跑（10 秒级）, 输出全文贴回助手
cp src/goodhart_c2.py /tmp/ && cd /tmp
python -c "import ast; ast.parse(open('goodhart_c2.py').read()); print('语法OK')"
python -m unittest test_goodhart_c2 -v 2>&1 | head -40

# 第 4 步: B 门禁链（leak_check FAIL 会自动中断后续）
cd goodhart-project
bash run_all.sh

# 第 5 步: 引用核验（1 小时, 独立可并行）
#   导入 citation_verification.csv → 14 条工作队列 → 浏览器逐条确认
```

---

## 10. 唯一优先级（写给接手人，防止散步）

三条主线里，只有预注册是"越晚锁越没价值"的。C.2 一跑出数据，判读规则就无法保持中立，防自欺效力归零且不可补回。核引用与 C.2 首跑随时可做，唯独这条锁错过就没了。

因此接手后的动作顺序是硬性的：

1. 锁预注册（今晚，5 分钟）
2. 跑引用核验（1 小时，独立，直接清理污染）
3. 跑 C.2 首跑（10 秒，贴 stdout，进入按 traceback 修复的循环）
4. 核对字段名 → 跑 B 门禁链（依赖 C.2 结论稳定后动，避免并行返工）

反优先级（明确不做）：在 C.2 未跑通前加新实验、调 PPO 超参、写 AGI 综述、准备投稿——全部是在"未验证基础上叠加未验证"。

---

## 11. 诚实边界声明（交接的核心，务必保留）

这份文档本身也要被同样地审视：

1. 全部代码未经运行。§3、§4 里所有"应该能跑"的表述都只是设计意图；真实行为以你的 stdout / traceback 为准。四轮对话中给出的任何代码，验收状态一律是"未验证"。
2. §5 的引用元数据全部 ⚠️。它们产生于助手记忆、未经检索确认。§5 的 1 小时核验就是为此设的。任何链接、DOI、作者名，用前必须自行确认。
3. B6 的 6050 字预算是按 800 字/页估算，若你的模板另有字号行距规定，需重算。
4. B5 零文献引用，Q1–Q6 展开时涉及的一切文献默认 ⚠️，走 §5 流程。
5. 本交接文档由助手撰写、未经运行验证，其价值在于"信息集中与风险标注"，不在于"内容已被证实正确"。接手人应把它当作地图，不是已勘探的地形。
6. 助手不能运行代码、不能写你的磁盘、不能代替你点浏览器。这份文档之后，下一步的球在你的手上。

---

## 12. 交接清单（签字用）

| # | 事项 | 交接状态 | 接手人确认 |
|---|---|---|---|
| 1 | 目录树可建 | 脚本已给（setup_goodhart.sh） | ☐ |
| 2 | 预注册文本完整 | 是，日期未填 | ☐ 已填已锁 |
| 3 | C.2 代码完整 | 是，含待执行补丁 P1 | ☐ 已执行 |
| 4 | B 全套代码完整 | 是，字段名待核对 | ☐ 已核对 |
| 5 | 防泄漏三重机制 | 已设计+编码，未实测 | ☐ 门禁实测 PASS |
| 6 | 引用 CSV | 17 行，全未核验 | ☐ 已核验 |
| 7 | 分析管线 | 完整+容错，等数据 | ☐ |
| 8 | DSH 模板 / AGI 清单 / 报告骨架 | 完整 | ☐ |
| 9 | 风险清单已读（§8） | — | ☐ |
| 10 | 诚实边界已读（§11） | — | ☐ |

---

## 13. 与当前磁盘的差异（§0–§12 的漂移登记）

> **由外部会话于 2026-10-07 逐条对磁盘核实后追加。非原文。**
>
> §0–§12 是从对话记录（第 4865–5099 行）**逐字搬运**的历史快照，写于文件尚未
> 落盘之时。它是"当时的计划"，不是"现在的现实"。本节把两者的差异显性化，
> 以免后人把快照当成现状。**发现差异时以本节为准。**

### 13.1 快照里引用了、但磁盘上不存在的文件

| 快照位置 | 引用的文件 | 磁盘实况 |
|---|---|---|
| §1 目录树、§3.3、§9 第 3 步 | `src/goodhart_c2.py` | **不存在**。C.2 的实际训练脚本是 `src/train_c2.py`（6863 B） |
| §9 第 0 步 | `setup_goodhart.sh` | **不存在**（项目已在磁盘上，无需该脚本） |
| §9 第 3 步 | `test_goodhart_c2`（unittest） | **不存在**。现有测试是 `tests/test_smoke.py`（4 例） |
| §3.3 补丁 P1 | `goodhart_c2.py` 里 F1 处的草稿行 `penv = ...` | 该文件不存在；全仓 `grep penv src/` **零命中**。**P1 已无对象，视为作废** |

### 13.2 §3.1 的 C.2 设计 与 `src/train_c2.py` 的实际实现**不吻合**

这是最严重的一条：**按快照（和预注册）的描述去跑 `train_c2.py`，测的不是那个实验。**

| 项 | §3.1 / 预注册 §2 的要求 | `src/train_c2.py` 实际 |
|---|---|---|
| 环境 | `CartPole-v1` + 改造版 `SpeedLimitedCartPole` | 纯 `CartPole-v1`，**无** SpeedLimited 改造 |
| 真实目标 | `steps_alive − λ·max(0, speed − speed_limit)` | 直接用环境原生 reward（= 存活步数），**无超速惩罚** |
| 代理目标 | `proxy = mean(speed)^α`（速度的 α 次幂） | `proxy = obs[0]`（**小车位置**，与速度无关） |
| α 的角色 | 代理目标的**指数** | 真实/代理的**凸组合权重** `(1−α)·true + α·proxy` |
| α 网格 | `{0.5, 1.0, 1.5, 2.0, 2.5, 3.0}`，6 档 | `[0.0, 0.25, 0.5, 0.75, 1.0]`，5 档 |
| seeds | 42–46 | `[0, 1, 2, 3, 4]` |
| timesteps | 40000 | 100000 |
| 分组 | G1–G6（G5/G6 在 G3/G4 上叠噪声） | 无噪声组，G1–G6 结构不存在 |
| `detach_ratio` | §3.1 写 `= 各组真实得分 / G1 真实得分`；预注册 §3 写 `= 1 − true/true_max` | `train_c2.py` 不产出该量（交由 `analyze_c2.py`） |

注意上表最后一行：**§3.1 与预注册 §3 对 `detach_ratio` 的定义本身就互相矛盾**，
两个定义不是同一个量。锁定预注册前必须先解决这处内部冲突。

`train_c2.py` 的文件头已自述"所有标 `# PREREG-SYNC` 的行都是占位值，必须逐条对齐
预注册后才可用于正式实验"，且输出 `train_config.json` 时写死 `"prereq_synced": False`。
**即：代码自己也知道它没对齐。** 这不是文档滞后，是"设计↔实现"分叉。

**买一送一（2026-10-07 新增发现）**：`train_c2.py` 与 `analyze_c2.py` 的**列契约
也不一致**。前者写出的 CSV 列是 `alpha, seed, timesteps, proxy_kind,
true_return_mean`；后者 `load_summary()` 硬性要求 `{alpha, seed, proxy_score,
true_score}`，不符即 `raise ValueError`，并在文件头声明还需要 `steps_alive,
mean_speed`。**即使装好 sb3 跑通训练，`analyze_c2.py` 也会直接因缺字段退出。**
所以 C.2 断的不只是环境与超参，中间还断了一条数据接口。（`train_c2.py` 文件头
自称"列与 analyze_c2.py 期望的格式一致" —— 这句自述是错的。）

### 13.3 预注册本身尚不可锁定

`prereg/preregistration_c2.md` 的状态是"未锁定"，且**参数冻结值是空的**：

- `λ = 【待填】`、`speed_limit = 【待填】`、`训练步数 = 【待填】`（§2）
- 功效估计 `【待填/跑后补】`（§4）

§10 把"锁预注册"列为唯一"越晚越没价值"的动作，但**在一组空值上锁定没有意义**
——锁的是具体规则，不是空表格。要锁，必须先把冻结值填实，且按 13.2 先把
设计↔实现的分叉收敛。**在那之前，"已锁定"三个字不该落到这个文件上。**

### 13.4 引用台账比 §5 描述的更空

§5 说"17 行…全部元数据默认 ⚠️ —— 它们产生于助手记忆，未经任何检索确认"。
实况更彻底：`prereg/citation_verification.csv` 的 17 行**没有任何元数据**，
`cite_key/title/authors/year/venue/doi/zotero_key` **每一格都是 `[待填]`**，
只有 `notes` 列写着"这里应该引什么"（如"PPO 原始文献""预注册方法论"）。

也就是说：**这不是"17 条待核验的引用"，而是"17 个待填写的引用空位"。**
§5 的"核验流程"（逐条确 DOI/标题/作者）在当前状态下无从执行——没有可核之物。
真正的下一步是"检索并填入"，其后才是核验。方法论见
`docs/citation_verification_spec.md`（该文件在 §1 的目录树里没有列出）。

### 13.5 目录树（§1）漏列 / 错位

**实际存在但 §1 未列出**：`docs/known_issues.md`、`docs/citation_verification_spec.md`、
`docs/handover_interview.md`、`src/_plot_style.py`、`tests/test_smoke.py`、
`tools/reconcile_zotero.py`、`requirements.txt`、`.gitignore`。

**§1 位置错**：`citation_verification.csv` 被列在仓库根，实际在 `prereg/`
（README 的目录树是对的）。

### 13.6 README 与磁盘的差异

- README §"当前覆盖范围"称"C.2 目前…缺训练脚本"——但 `src/train_c2.py` **已存在**。
- README §目录树称 `docs/HANDOVER.md`"需手工补齐 §0–§12"——**本次已补齐**，
  且新增本节 §13。
- README §已知问题原称 `ret-path` 族阈值待修——**本次已修**（KI-001 C），
  README 该条已同步更新。

### 13.7 未创建的输出目录

`etl/results/` 与 `c2/results/` **都不存在**（脚本运行时会 `os.makedirs` 自动建）。
故 §1 与 README 目录树里画出的 `logs.jsonl` / `summary.csv` / 图1–图3 **尚无产出**。

### 13.8 依赖状态（2026-10-07 实测，含安装后的复验）

已装齐。`numpy 2.5.2` / `pandas` / `matplotlib` / `torch 2.14.1+cu130` /
`gymnasium 1.2.0` / `scipy` 由系统环境提供；**`stable_baselines3 2.9.0` 已于本次装入**。

**venv 不能建在仓库内 —— 这是一个本机硬事实**：仓库路径
`/home/liuzewen/F:\deepseek/goodhart-project` 的目录名含路径分隔符 `:`
（`F:\deepseek` 那个反斜杠+冒号是真名的字符），Python 3.11+ 的 venv 安全检查
会直接拒绝：

```
Error: Refusing to create a venv in ... because it contains the PATH separator :.
```

因此 README / §9 里写的 `python3 -m venv .venv` **在本机不可能成功**，
必须改建在无冒号路径。实际采用的方案（`--system-site-packages` 复用系统那
2.5 GB 的 CUDA torch，避免重复下载）：

```bash
python3 -m venv --system-site-packages /home/liuzewen/.venvs/goodhart
/home/liuzewen/.venvs/goodhart/bin/python -m pip install -r requirements.txt
```

复验（`/home/liuzewen/.venvs/goodhart/bin/python`）：`sb3 2.9.0` 与
`gymnasium 1.2.0` 兼容 —— `PPO('MlpPolicy', 'CartPole-v1')` 可构造成功。

两条非致命提示，跑 C.2 前应处理：
1. `UserWarning: You are trying to run PPO on the GPU, but it is primarily intended
   to run on the CPU when not using a CNN policy` → 训练时显式 `device="cpu"`
   （或 `export CUDA_VISIBLE_DEVICES=`），否则可能更慢并有告警噪声。
2. 某处仍 `import gym`（旧版），触发 "Gym has been unmaintained since 2022…"。
   `requirements.txt` 只写 `gymnasium`，故这条来自某个依赖的间接导入，不影响运行。

**依赖已不构成阻塞。C.2 仍不应开跑 —— 卡点是 13.2 的设计分叉与列契约断裂
（跑通训练 `analyze_c2.py` 也会因缺 `proxy_score/true_score` 直接 raise），
以及 13.3 的预注册未填未锁。**

### 13.9 C.2 路线决策与设计裁决（2026-10-07 拍板）

针对 13.2/13.3，选择**改代码对齐预注册**（而非改预注册对齐代码）。

理由：预注册是实验设计的冻结快照，代码是它的实现。反向改（让假设去适配
已有实现）等于"先有实现、再改假设"，正是本项目 §11 要防的流程性自欺。
因此 `train_c2.py` 与预注册不符的每一处，都以预注册正文为准改写代码。

**逐项裁决**（争议点均以 `prereg/preregistration_c2.md` 正文为准）：

| 项 | 裁决 | 依据 |
|---|---|---|
| `detach_ratio` 定义冲突（13.2） | 采预注册 §3 `= 1 − true_score/true_score_max`；§3.1 的"各组/G1 真实得分"措辞**作废** | §3.2 明写"预注册第 1、3 节，正文为准"；`analyze_c2.py` 现有实现（`true_peak = piv["true_score"].max()`）已与此一致 |
| 分组结构 | 只做预注册 §2 的 **α 六档扫描**（{0.5,1.0,1.5,2.0,2.5,3.0}）；§3.1 的 G1–G6、G5/G6 噪声组**作废** | 预注册 §2、§5 只定义 6 档 × 5 seeds = 30 次训练，无 G 分组、无噪声组 |
| seeds | 沿用 §3.1 给出的具体值 **42–46** | 预注册 §2 只写"每档 5 seeds"，未钉具体值；§3.1 的具体值不与该要求冲突，取之可减少一处自由度 |
| 训练奖励形式 | 每步 dense reward = `speed^α`；回合回报 = `Σ speed_t^α` | RL 无法直接优化"回合结束后才算得出的 `mean(speed)^α`"。**记为一处偏离**，见下 |
| 报告的 `proxy_score` | 严格按预注册定义 `mean(speed)^α`（回合内 `Σ speed_t / n` 的 α 次幂） | 保证图1/表1 画的是预注册写的那个量，与训练损失函数形式解耦 |
| `speed` 的定义 | `\|x_dot\|`（小车水平速度绝对值），预注册未定义故由实现者钉死 | 记录于此，避免跑后被质疑"速度是什么" |
| λ / speed_limit / 训练步数 | 预注册留空。实现者**用 pilot 标定后回填预注册，再锁定**。标定发生在锁定前，属"跑前选定"，不是事后改 | 预注册 §2 明确预留 `【待填】`，即设计参数本就应在锁前定实 |

**偏离记录（必须与预注册并列存放）**：训练用的每步奖励 `speed^α` 与预注册
写的 `mean(speed)^α` 不是严格同一个函数。二者对 `mean(speed)` 单调同向，
但 `Σ speed^α ≠ (mean speed)^α`。此偏离不改变 H1 的判读对象（判读看的是
按预注册定义算出的 `proxy_score` 与 `true_score`），但必须在报告 2.5 节写明。

**仍未决、需在锁定前解决的**：λ / speed_limit / 训练步数三个冻结值（见 13.3），
标定方法见 `src/speed_limited_cartpole.py` 的文件头。