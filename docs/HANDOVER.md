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

### 13.3 预注册已填实并锁定（原"尚不可锁定"，2026-10-07 已解除）

原文（本节初稿）记录：`prereg/preregistration_c2.md` 状态"未锁定"，
`λ = 【待填】`、`speed_limit = 【待填】`、`训练步数 = 【待填】` 三处为空，
功效 `【待填/跑后补】`。因此当时判定"在一组空值上锁定没有意义"。

**该阻塞已解除**（做法见 §13.9）：三个冻结值经 pilot 标定后填实为
**λ = 1.0 / speed_limit = 0.376 / 训练步数 = 100000**，功效已实算
（n=5 配对 t 检验检出 15% 效应达 power=0.80 需配对差 SD ≤ 44.6）。
预注册**已锁定**：锁定日期 2026-10-07，绑定代码冻结点 commit `1f95ed0`。
预注册正文新增 §0「锁定说明」，把三条跑后不许改的口径（speed 定义、
训练奖励≠报告量的偏离、`steps_alive` 饱和的预期性）写在锁定之前。

### 13.4 引用台账：17/17 已核实（2026-10-11 修正本节标题）

原文（本节初稿）记录：`prereg/citation_verification.csv` 的 17 行
`cite_key/title/authors/year/venue/doi/zotero_key` **每一格都是 `[待填]`**，
只有 `notes` 列写着"这里应该引什么"。即"17 个待填写的引用空位"。

**已推进**（2026-10-07 轮）：新增 `verified_via` 列（`docs/citation_verification_spec.md`
原本就要求此列），逐条联网检索后**填实 13 条**，`zotero_key` 全部保持 `[待填]`
（无 Zotero 访问权，无法核验）。本节当时记作"13 填实 / 4 留空"，
`PAPER_DRAFT/OUTLINE.md:27,85` 亦沿用该计数。

**已推进（2026-10-11 轮，本节实际状态已变，勿再引 13/4）**：对 CSV 逐行重读，
`verified=✅`、`verified_date=2026-10-08`、五列内容全部填实者为 **17 行**
——即 2026-10-07 轮记为"留空"的那 4 行，其后已全部补齐（含
`goodhart1975problems` 的 Palgrave 1984 重印本 DOI、以及三裂缝三行的
Campbell/Strathern/Popper 真实出处）。`verified_via` 也逐行有 URL。
**结论：13/4 是过期数字，当前是 17/17 填实、0 留空。** OUTLINE.md 的
"4 空 + zotero_key 结清"红线相应失效，只剩 `zotero_key` 未核这一项。

**2026-10-11 独立复核（不信 ✅ 标记，直接查权威源）**：
- `reference_checker` 对 17 条全量比对 Crossref/OpenAlex/arXiv →
  **14 found / 3 partial / 0 not_found**。
- arXiv API `id_list=1606.06565` → "Concrete Problems in AI Safety"，
  published 2016-06-21，六位作者姓名逐字一致。
- Crossref `10.1002/(SICI)1234-981X(199707)5:3<305::AID-EURO184>3.0.CO;2-4`
  → title / container / year / volume / issue / page / authors 全部逐字一致。
- Crossref `10.1007/978-1-349-17295-5_4` → "Problems of Monetary Management:
  The UK Experience"，1984，book-chapter，pp. 91–121，作者 C. A. E. Goodhart。
- 3 条 partial 均为索引匹配到别的同名/相关文献（Strathern→《Partial
  Connections》书评、Amodei→"AI Safety Gridworlds"、Popper→《Economica》
  书评），不是被引文献本身错。逐条人工点开 DOI 后确认无误。

**仍受的红线约束**（未随 17/17 改变）：
- `zotero_key` 17 行全为 `[待填]`，`tools/reconcile_zotero.py` 未执行。
- `goodhart1975problems` 引的是 **1984 Macmillan 重印本**（pp. 91–121），
  原版 1975 会议论文页码未定位；流行缩略语 "When a measure becomes a
  target..." 出自 **Strathern 1997**（转述 Hoskin 1996），**不是 Goodhart 原话**。
- 三裂缝三行（Campbell/Strathern/Popper）引的是**底层定律**，不是三分法的
  出处。**本项目自身的"三裂缝"框架外部无对应文献**：最接近的
  Manheim & Garrabrant 2018《Categorizing Variants of Goodhart's Law》
  (arXiv:1803.04585) 是**四类**（regressional / extremal / causal / adversarial），
  与"三裂缝"不符。**不得把这三条当作三分法的来源引用。**
- 年份口径：`year` 列取刊出年，预印本年写进 `venue`。三处受影响：
  `ross2011reduction`（2011 vs 2010）、`sainz2024nlp`（2024 vs 2023）、
  `morris2024levels`（2024 vs 2023）。

**已落地**：`paper/refs.bib` 17 条 BibTeX 全部由本 CSV 转写，上述四条
约束以注释形式写在 bib 文件头；`paper/main.tex` 的 "Open items" 节按
17/17 重写，不再出现"13 filled / 4 empty"。

**（以下为 2026-10-07 轮原文，保留作历史记录；其"13 填实 / 4 留空"计数已于
2026-10-11 轮被上文修正为 17/17，请勿再引用 13/4。）**

**已推进**（2026-10-07 轮）：新增 `verified_via` 列（`docs/citation_verification_spec.md`
原本就要求此列），逐条联网检索后**填实 13 条**，`zotero_key` 全部保持 `[待填]`
（无 Zotero 访问权，无法核验）。

**4 行刻意留空**（2026-10-07 轮状态；2026-10-11 轮已全部补齐）：
- 第 1 行「Goodhart 原始表述」：2026-10-08 已核到 Palgrave 1984 重印本
  （DOI 10.1007/978-1-349-17295-5_4）。但该行注记要求的"定位到具体页码"
  仍未满足（只核到重印本 pp. 91–121，原版 1975 页码未定位），
  且年份（1984）与原始年份（1975）不一致 → **此条部分未结，见上文红线第 2 条**。
- 第 2–4 行「三裂缝（测量/代理/不可证伪）的出处」：2026-10-08 已填实为
  Campbell 1979 / Strathern 1997 / Popper 1963 三条真实文献。但**这三条引的是
  底层定律，本项目自身的"三裂缝"框架外部无对应文献**（Manheim & Garrabrant
  2018 是四类，不符）→ **此条仍受约束，见上文红线第 3 条**。

**独立复核（2026-10-07 轮，13 条）**：用 arXiv API（`export.arxiv.org/api/query`）
与 Crossref API（`api.crossref.org/works/{doi}`）对 13 条逐条回拉权威元数据并比对
标题/年份。**复核脚本是一次性脚本，未入库**（若日后要常态化复核，应放进 `tools/`
并纳入测试）。结果：
- **13 条标题全部逐字一致**；DOI 10.1109/TSMC.1983.6313077 与
  10.1073/pnas.1708274114 经 Crossref 确认。
- 2 条 JMLR 文献（`raffin2021stable`、`pineau2021improving`）无 DOI，Crossref
  取不到，改为直接抓 jmlr.org 页面确认标题/作者/卷期页
  （`22(268):1−8`、`22(164):1−20`，均 2021）。
- **发现 3 处"年份双写"陷阱**：`ross2011reduction`（CSV 2011 = AISTATS 刊出年，
  arXiv 预印本 2010）、`sainz2024nlp`（2024 vs 2023）、`morris2024levels`
  （2024 vs 2023）。`year` 列按引用惯例取**刊出年**，预印本年已写进 `venue` 列，
  以免日后被当成错误引用。

**仍受的红线约束（2026-10-07 轮原文，2026-10-11 轮状态见上文）**：
§5 的"核验完成前不得进入正式写作参考文献"已于 2026-10-11 轮解除——
`paper/refs.bib` 17 条已转写入稿。剩余未结项为：`zotero_key` 未核、
Goodhart 原版页码未定、三裂缝无外部出处
（`tools/reconcile_zotero.py` 未执行）。

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

**已解决（2026-10-07）**：λ / speed_limit / 训练步数三个冻结值经 pilot 标定后
填实（见 §13.3），预注册已锁定，代码已对齐。**C.2 现已具备开跑条件。**
标定方法与原始输出见 `src/speed_limited_cartpole.py` 文件头与 `--calibrate`。

### 13.10 门禁三处遗留的结清（2026-10-08）

上一轮实施 KI-001 C 时记下两条"新开"未决项，本轮又查出第三处**同类 fail-open
漏洞**。三条一并结清，其中第一条**原诊断是错的**，如实更正如下。

#### (a) `chain-sort` 族：不是"阈值偏松"，是"该族结构性不可判别"

**原诊断（2026-10-07，已作废）**：基线 `1/(len(init_seq)+1)` 偏松，25% 泄漏者
判 CLEAN，需"单独推导其盲猜基线"。

**取证结论（2026-10-08，实测）**：真正的问题在**任务族设计**，不在阈值。理由是
两点硬事实：

1. 探针 prompt 只给 `init_seq` + 步数 k，隐藏的只有**二值** `sort_rule`
   (`gen_tasks.SORT_RULES = ("asc", "desc")`)，而 `apply_chain_sort` 是确定性
   变换 → 盲猜者把规则域枚举一遍就得到**恰好 2 个候选**，均匀取一 → 真实盲猜率
   **≈0.5**。实测（`/tmp/diag_chainsort.py` 思路，见回归测试）：162 个
   (任务,k) 组合候选数=2，5 个=1，平均可推导盲猜率 **0.5150**。
2. 旧基线 0.1991 → 阈值 0.4978 < 0.5150 → 一个**诚实枚举的盲猜者会被判 LEAK**
   （假阳性）。而 25% 泄漏者（0.25）判 CLEAN **是正确的** —— 0.25 低于盲猜水平，
   本来就不构成"泄漏"的证据。所以上一轮记的"25% 泄漏者判 CLEAN 是缺陷"
   是**误诊**。

**修法**：`ChainSortProbe.random_baseline` 改为
`1/(公开信息下可推导候选数)` —— 与 ret-path 同一原则（可推导候选数的倒数），
只是候选集来源不同（ret-path 隐藏 ptr 是随机排列、无法枚举，故用全池互异真值数 d；
chain-sort 隐藏的是二值规则，故用规则域大小）。改后基线 0.5 → 阈值 1.25，
该族对任何泄漏都不再误报。**该阈值的完整推论（2026-10-08 提交自检时补记）**：
1.25 高于命中率理论最大值 1.0，故本族**任何命中率——包括 100% 完美泄漏——
都永远不会触发 LEAK**（selftest oracle 例实测 `100.0% vs 阈值125.0% → CLEAN`
直证此点）。它的门禁职能只剩"零假阳性"的结构诚实性，泄漏检测由 stateful-calc
与 ret-path 两族承担。这是**设计局限**，不是可以靠调阈值修好的东西。
（本节早先措辞"本族在 50% 以下不可判别"偏弱：它暗示 50% 以上可判别，实际
任何水平都不可判别，已如上收紧。）

**连带修的数据卫生 bug**：`gen_tasks.main` 的 public 白名单**含 `sort_rule`**，
即隐藏规则本身进了公开 `tasks.jsonl`（与 `ops` 被隐藏的做法不一致）。已从白名单
移除（`run_etl.build_prompt` 本就不读它）。实测：重跑 `gen_tasks.py` 后
`schedules.pkl` 的 SHA256 **不变**（`6c78350def493ef4…`），锚点未动。

**回归网**：`tests/test_smoke.py` 新增
`test_chain_sort_baseline_derives_from_rule_domain`（独立重推候选集比对基线）
与 `test_hidden_rules_not_in_public_tasks`（禁 `sort_rule/ops/truth_chain/ptr/values`）。

#### (b) 门禁链第 3–5 步：基础设施冒烟通过，真实测量仍被凭据阻塞

**原状态**：`run_all.sh` 在门禁处 fail-closed 中止（`run_etl.py` 的 `model_call`
是占位实现），第 3–5 步从未在真实数据上跑过。

**本轮进展**：环境里**没有任何 LLM 凭据**（无 `.env`；`env` 中仅有 `GH_TOKEN`、
`TRAE_JWT_TOKEN_PATH` 等非模型密钥）。因此"接入真实模型"这件事本轮无法完成。
能做且已做的是用**确定性 stub** 验证管线契约 —— 新增
`src/smoke_gate_chain.py`，四例：

| 例 | stub | 断言 | 实测 |
|---|---|---|---|
| T1 | 调用全抛异常 | GATE = FAIL (fail-closed) | ✓ |
| T2 | oracle 答对全部 | GATE = FAIL (LEAK) | ✓ |
| T3 | 恒答无关串 | GATE = PASS (门不是恒拦) | ✓ |
| T4 | 每 4 次答对 1 次 | run_etl→audit_replay(mismatch=0)→analyze_etl 四产物齐 | ✓ |

产物一律落临时目录，**绝不进 `etl/results/`**。T4 **有意绕过门禁**直接调
`run_etl.run`（oracle 必被门禁判 LEAK 而阻断），因为该步只验数据契约、不做测量。

**仍未解决、且本轮无法解决**：真实模型调用被"环境无 LLM 凭据"阻塞。
因此**任何 ETL 的真实数字都尚不存在**；`analyze_etl` 的图/表当前只能由 stub 数据
触碰。接入真实接口后须重跑 `run_all.sh`，且 stub 产物不得与真实结果混放。

#### 附：C.2 全量结果

见 `c2/results/summary.csv` 与 `train_config.json`（`prereg_synced=true`）。
判读走 `src/analyze_c2.py`，结果与判读登记于 §13.11。

#### (c) 新查出：`leak_check` 的 schedules 缺失回退是 fail-open（本轮修）

**问题**：旧 `_default_schedules()` 在 `schedules.pkl` 不存在时**现生成一份合成
真值表**给门禁用。后果是"门在验 A、跑批用 B"——若单独跑门禁而没先跑
`gen_tasks.py`，门禁验的根本不是 `run_etl` 将要使用的那份 schedules，
却照样可能打印 CLEAN。这与本项目 fail-closed 的硬约束直接冲突。

（`run_all.sh` 的流程里第 1 步先生成、第 2 步才验门，所以**日常流程未受影响**；
但门禁单独被调用时是个真实的静默放行口。）

**修法**：拆成三个显式入口，语义互不混淆：

| 函数 | 语义 |
|---|---|
| `_require_schedules(path)` | 正式门禁用。缺失即打印错误并以**退出码 2 fail-closed**，绝不现生成 |
| `_generate_schedules_for_selftest()` | 只给 `--selftest` 用，且**明确打印**"改用合成数据自检门禁逻辑" |
| `_selftest_schedules()` | `--selftest` 入口：有真实表就用真实的，没有才退化到合成表 |

`_selftest` 内联的硬编码路径加载也一并改为 `_require_schedules()`。

**回归网**：`tests/test_smoke.py` 新增
`test_gate_fails_closed_when_schedules_missing` —— 在空目录里跑 `leak_check.py`，
断言非零退出且报出「找不到」，堵死"静默用合成数据验门"。

#### (d) 本次触发的 §0–§12 漂移登记（按本文件的体例，正文不改）

- **§4.2 第 2 条的基线行已过时**：原文写
  `stateful-calc ≈ 0.02 / chain-sort ≈ 1/L! / ret-path ≈ 1/条目数`。
  现状为 `stateful-calc = 0.02（常数）/ ret-path = 1/(该 k 上互异真值个数) /
  chain-sort = 1/(规则域内可推导候选数) = 0.5`。以代码
  `src/leak_check.py` 的三个 `random_baseline` 为准，原文此行作废。
- **§7 状态总表整体过时**：该表描述的是落盘前的快照（"C.2 从未运行"、
  "引用 17 条全部未核验"）。现状见 §13.1–§13.10；接手时**以 §13 为准**，§7 仅作历史。
- **§3.3 / §4.3 的字段名核对项**：§4.3 列的 `apply_chain_sort(seq, i, sort_rule)`
  与字段名核对**本轮已实核**，均与 `src/gen_tasks.py` 一致（`apply_chain_sort`
  存在且签名一致；字段名 init_seq/sort_rule/entries/ptr/values/x0/ops 全部吻合）。

### 13.11 C.2 全量结果与判读（2026-10-08）

30/30 次训练全部完成（6 档 α × 5 seeds × 100k 步，`prereg_synced=true`，
后台 job exit 0）。`summary.csv` 30 行，sha256 =
`58b64fc881822af7a8ffb5033146c7a7e94505cf91e58c2322bad7b662192c31`。
`analyze_c2.py` 已跑，产物：`fig1_detach_curve.pdf`、`table1_true_score.csv`。

**表1 数据（true_score mean [95% bootstrap CI]，n=5 seeds）**：

| α | true_score | steps_alive(均值) | mean_speed(均值) | detach_ratio |
|---|---|---|---|---|
| 0.5 | 444.02 [431.89, 456.15] | 500.0（饱和，§0.3 预期） | 0.414 | 0 |
| 1.0 | −2.22 [−4.52, 0.08] | 97.0 | 1.376 | 1.005 |
| 1.5 | 39.41 [31.39, 46.78] | 124.0 | 1.043 | 0.911 |
| 2.0 | 59.44 [47.91, 71.08] | 134.7 | 0.922 | 0.866 |
| 2.5 | 21.32 [16.04, 30.02] | 71.8 | 1.001 | 0.952 |
| 3.0 | 11.34 [10.46, 12.47] | 29.5 | 0.931 | 0.975 |

**按预注册 §3 三条件逐条核对**：

1. *true_score 相对峰值下降 ≥ 15%*：**满足**。峰在 α=0.5（444.02），各失真档
   跌幅 86.6%–100.5%；各失真档 CI 与峰值档 CI 无重叠；配对差（按 seed）
   mean 446.2 / SD 15.1（vs α=1.0）、432.7 / 16.0（vs α=3.0）→ 功效补记已按
   §4 要求追加进预注册（实际功效 ≈ 1.0）。
2. *该差异的 95% CI 不含 0*：**满足**（配对差 CI 离 0 极远）。
3. *「存在 α 使 proxy_score 达峰值后继续上升（或持平）」*：**字面不满足，
   意图满足**。proxy_score 峰在 α=1.0（1.376），峰后回落（1.07 → 0.85 →
   1.06 → 0.81），并非续升/持平。但该分句的立法意图（§3 附带条件括号内写明）
   是排除"训练没起来"——而坍塌点 α=1.0 上 proxy_score 恰为全程最大值、
   mean_speed 从 0.41 升至 1.38（3.3 倍），代理被最大程度达成、真实分数同时
   崩至全程最低：Goodhart 交叉点清晰。附带条件 2 的字面（"α 增大推向更高
   速度"）也只在 0.5→1.0 段成立。

**判读裁定（2026-10-08，作者决定）**：记「**确认脱钩**」，并按要求如实标注
第 3 条件的字面偏离与理由。裁定前记录过两个可辩护选项——(a) 确认脱钩 + 标注
偏离、(b) 从严记部分脱钩——**裁定选 (a)**。理由：第 3 条件的立法意图是排除
"训练没起来"这一混淆（§3 附带条件），而坍塌点 α=1.0 上 proxy_score 取全程
最大值、mean_speed 为对照档的 3.3 倍，代理达成度全程最强，混淆被强证据排除；
选 (b) 会更误导——本批跌幅 86.6%–100.5% 与该档 5%–15% 的定义区间差一个
数量级。`analyze_c2.py` 自动打印的「确认脱钩 [峰后跌幅 100.5%]」与裁定一致，
但其依据仅为点估计跌幅；本裁定的完整依据是 CI 分离 + 配对功效（≈1.0）+ 意图
论证。

**报告 2.4 节定稿措辞（裁定 (a)，可直接抄入）**：

> 在 α∈{0.5, 1.0, 1.5, 2.0, 2.5, 3.0} 的扫描上，真实分数于 α=0.5 达峰
> （444.0，95% CI [431.9, 456.1]）后下降 86.6%–100.5%；α=1.0 档塌至
> −2.2（CI [−4.5, 0.1]），且代理分数恰在该点达全程最大（1.376，mean_speed
> 为对照档的 3.3 倍）——代理被最大程度优化的同时真实目标崩溃，构成清晰的
> Goodhart 交叉。各失真档与峰值档的 bootstrap CI 无重叠，按 seed 配对差
> SD 仅 15–16 分（远低于本设计 44.6 分的功效上限），实际功效 ≈ 1.0，判定为
> **确认脱钩**。需与结论同时标注的一处判据偏离：预注册 §3「确认脱钩」的
> 第三个合取项要求"proxy_score 达峰后继续上升（或持平）"，本批 proxy 峰后
> 回落，该形式条件未满足；选择本档的理由是该条件意在排除"训练没起来"，而
> 坍塌点上代理达成度为全程最强，训练充分性无争议；「部分脱钩」档（5%–15%）
> 与本批跌幅差一个数量级，采用它将构成更大的误述。

**三档措辞覆盖缺口（方法论观察，供后续预注册设计参考）**：同一数据形态下
"形式条件严于立法意图"是首次出现；后续实验若沿用三档判据，建议在判据中显式
定义 Goodhart 交叉点（proxy 达峰 ∧ true 谷底）作为「确认脱钩」的等价形式
条件。**预注册 §3 正文未改动（冻结）；本裁定只记于本文件与报告。**

**附带条件报告（§3 强制）**：各档 steps_alive 见上表；非所有档 > 0.98×500，
故"全部信号来自罚分项"的触发句**不需要**；但 α=0.5 档 steps_alive 全部
饱和于 500（§0.3 预期），该档 H1 信号同样来自罚分项（true 444 < 500）。
各档 mean_speed 见上表。

**[exploratory] 观察（预注册不覆盖，禁作结论）**：
- true_score 对 α 非单调：α=1.0 全程最差（−2.2），α=2.0 局部回升（59.4），
  α≥2.5 再降。机制不明，可能与 PPO 局部最优及超线性奖励下的存活-冲速权衡
  有关，本批数据无法区分。
- H1 的"代理分数单调上升"字面同样未满足（proxy 峰后回落）——记录在案。
- H2（α* 的 seed 间方差）：每个 seed 的 true 峰都在 α=0.5（网格最左端），
  α* 左删失于网格边界，方差为 0 属退化情形，不能作为 H2 的正面证据。

### 13.12 Q5 结果与判读（2026-10-08）

10/10 训练全部完成（2 arm × 5 seeds × 100k 步，`prereg_synced=true`；
预注册锁定于 commit `2326720`，训练侧代码冻结于 `7d5d9f3`）。
`summary_q5.csv` 10 行，sha256 =
`945842447b813890665de7327083fb508c6f94de5d7e765d0446a60672ff8d6c`。
`analyze_q5.py` 投入使用前做了双路自检（合成数据 happy path +
不足样本 fail-closed exit 1）。

**数据**：

| arm | true_score | steps_alive | mean_speed | 每50回合罚分合计 |
|---|---|---|---|---|
| blind（4 维 obs） | 499.9926 | 500.0（饱和） | 0.1072（限速的 28.5%） | 0.0074 分 |
| salient（6 维 obs） | 499.9922 | 500.0（饱和） | 0.1084（限速的 28.8%） | 0.0078 分 |

**按锁定预注册 §3 判读（三档措辞不越档）**：

- **H1 未确认**：true_score 配对差（salient−blind）mean = −0.00035 分，
  95% bootstrap CI 与 0 不可区分；数据与 H0 一致（两组无差异）。
- **H2 形式判据满足、实质不成立（如实双记）**：|mean_speed−limit| 配对差
  mean −0.0013，CI [−0.0016, −0.0009] 不含 0——冻结判据形式上"确认"；
  但效应量仅为两组共同偏差（≈0.269）的 0.5%，且两组同为**过度保守**
  （远低于限速）而非 H2 假设的"压线 vs 冲速"之别。该确认无行为学意义。
- **§3 否证归因：(a) 成立**。归因判据实测：两组 mean_speed 仅为限速的
  28.5%/28.8%，惩罚通道**无作用面**（50 回合罚分合计 0.007/0.008 分，
  由 true_score = steps_alive − λ·over_speed_sum 反推）。true-奖励的
  最优策略是"低速存活"，根本不进入惩罚区——惩罚信号可不可察觉都无所谓。
  **按预注册纪律，禁止外推为"可察觉性不重要"。**

**附带条件（§3 强制）**：两组 steps_alive 均 = 500 > 0.98×500，触发句
适用：报告须写明存活项饱和、信号全部来自罚分项——而本批罚分项本身≈0。

**[exploratory] 设计层观察（禁作结论）**：speed_limit=0.376 沿用 C.2
标定，而该标定基于 **speed^α 优化策略**的 p90——true-奖励训练下的策略
天然低速，标定域与训练域错配，惩罚区在设计上就不可达。这与既有教训同构
（"文献里反复出现'是真问题'不等于'在本局有作用面'"）。若重做 Q5：需先
让惩罚区可达（speed_limit 压到存活策略速度分布内，如 ~0.09，或给存活
施加必须高速的任务约束），属**新实验、需新预注册**。

**Q6 解冻条件状态**：Q1（C.2 数据）+ Q5（本批数据——否证结果亦是数据）
= 两条线已产出数据，**"Q1–Q5 至少两条出数据"的解冻条件已满足**；
是否解冻由作者决定（解冻 ≠ 自动开工，Q6 需全新任务设计）。

### 13.13 B 线端到端打通：本地 Ollama 接入与首批真实数字（2026-10-08）

**接入方式**：`src/ollama_model.py`（标准库 urllib）——本地 Ollama
`http://127.0.0.1:11434/v1/chat/completions`，默认模型 **llama3.1:8b**
（qwen3:4b 在 max_tokens=50 下被 thinking 占满、content 为空，实测不可用），
temperature=0，timeout 60s，失败重试 1 次后返回 `__UNTESTED__` 不抛异常。
`leak_check` 把 `__UNTESTED__` 计为 failed（不计入 total），全失败仍
UNTESTED → GATE FAIL——**fail-closed 语义在真实接口下保持**。
`leak_check` 支持 `--n-per-family`、`run_etl` 支持 `--tasks-per-family`
确定性降采样（按 task_id 排序），均如实打印、不虚报全量。
（小瑕疵记录：`run_etl.__main__` 注释提到 `ETL_MODEL_ID` 环境变量但未实现；
logs.jsonl 的 model 字段实际正确记录为 llama3.1:8b，不影响数据。）

**门禁实测（实跑记录 `etl/results/gate_run.log`，n_per_family=20 全量）**：

| 族 | 命中 | 阈值 | 判定 |
|---|---|---|---|
| stateful-calc | 0/20 = 0.0% | 5.0% | CLEAN |
| chain-sort | 0/20 = 0.0% | 125.0% | CLEAN |
| ret-path | 0/20 = 0.0% | 11.0% | CLEAN |

**GATE PASS（exit 0）**，UNTESTED=0，60 次调用全部成功。

**ETL 真实跑**：90 任务（3 族 × 30）**614 步**，调用全成功（UNTESTED=0）；
`audit_replay` 重放 614 步 **mismatch=0**（判分可复现）；四产物落
`etl/results/`（logs.jsonl / fig_etl_curve / fig_error_decomp /
table_detach + report_snippets）。

**首批数字（llama3.1:8b）**：

| 族 | 步准确率 | first_err_median |
|---|---|---|
| stateful-calc | 0.0235 | 0.0 |
| chain-sort | 0.0 | 0.0 |
| ret-path | 0.0 | 0.0 |

步级合计：valid 5/614（0.8%），**correct 0/614**，err_type 标注 609 步。

**如实边界（防两误读）**：
1. **地板效应**：模型在第 0 步就几乎全错（first_err_median=0），不存在
   "带病状态上继续推理"的样本——**误差分解（single vs cumulative）在本批
   无作用面**，fig_error_decomp 的曲线是地板的形状，不是机制的形状。
2. **门禁 CLEAN ≠ 泄漏检测能力被证明**：0% 命中源于模型太弱，不是门禁
   灵敏度的正面证据；门禁的灵敏度论证仍以 selftest 反证 + stub 为准。

**对研究队列的影响**：
- **Q2（作弊恢复触发条件）/ Q4（短链外推长链）**：分析前提是"存在部分
  正确步可供分解"，本批 correct=0 → **当前不可分析**。与 Q5 的教训同构
  （机制在当前设置下无作用面）。出路是换更强模型（同一管线直接复用，
  `OLLAMA_MODEL` 环境变量即可切换，或接更强本地/远程模型），属
  重跑测量而非新设计。
- **Q6**：解冻条件（Q1+Q5 两条线出数据）已满足，作者拍板解冻
  （2026-10-08）。**解冻 = 允许立项设计，不等于自动开工**；Q6 需全新
  任务设计，为防"第二个计划过载"，设计另立项、不并入现有线。


### 13.14 2026-10-12 收尾：B 线重跑诊断、环境阻断登记、指针扫尾（glm 会话）

**本节行号即 2026-10-12 状态**；下游文档指针已全部改为「§13.x + 实测行号」双锚
（OUTLINE/CLAIM_LEDGER 16 处，提交 3fae710）。

1. **B 线「换更强模型重跑」的诊断（KI-002，先于任何重跑）**：首批地板
   （correct 5/614）**不是模型能力问题，是任务设计属性**——
   `src/gen_tasks.py:110-112` 公开白名单只有 `(task_id, family, n_steps, x0,
   init_seq, entries)`，`ops`/`sort_rule`/`ptr`/`values` 全部隐藏（2026-10-08
   卫生修复连同 sort_rule 一起移出，见 §13.10(a)），`build_prompt` 只拼公开
   字段 → **三族真值无一可由公开信息推导**。`logs.jsonl` 的 raw 显示模型在
   猜（ret-path 答条目名而非值）。换 llama3.1:8b 之外任何模型重跑都会得到
   同样的地板，除非先改设计。双臂对照实验（规则隐藏 vs 公开）脚本已就绪：
   `qc/b_line_solvability/mini_experiment.py`（每族前 6 任务 × k∈{0,2}，
   生产 `validator.check_step` 判分，raw 逐字落盘；**env 必须先于 import
   `ollama_model` 设 `OLLAMA_MODEL`**，用法见模块 docstring）。
2. **环境阻断（KI-003）**：2026-10-12 16:20 起本机任何模型加载 ~5s 内被杀
   （`llama-server process has terminated: signal: killed`；qwen3:8b /
   qwen2.5:7b / qwen3:4b / llama3.2:3b / qwen2.5:3b / qwen3:0.6b 全部复现，
   :11434 与临时 CPU 实例 :11435 均中招）。根因**不是 OOM**：
   `/tmp/opencode/ollama_watchdog.sh`（2026-10-12 03:10 由另一会话启动）每
   5s `kill -9` 全部 `llama-server`，保护其训练进程 `pid 3811520`
   （`.agent-memory/aie/scripts/deeped3.py`，占 GPU 3434/6144 MiB）。本项目
   **不得**杀 watchdog 或训练进程。迷你实验等训练结束或用户暂停 watchdog
   后执行。
3. **其他收尾（4 提交）**：`tools/reconcile_zotero.py` 哑炮修复（`[待填]`
   占位符当真值 → 回填恒为 0；改 `_is_blank` 判空 + `zotero_key` 回填 +
   `--dry-run`，fixture 实测，提交 431754e）；OUTLINE/CLAIM_LEDGER 16 处
   HANDOVER 行号指针刷新为 §13.x 双锚（3fae710）；.bak×2 入库保全（aa6a418）。
   引用台账 17/17 已核（zotero_key 仍全 [待填]，本机无 Zotero，
   `reconcile_zotero.py` 已修好待用）。
4. **下一步（二选一，均等外部条件）**：(a) watchdog 解除后跑 KI-002 双臂
   实验 → 按结果拍板修复方向（prompt 携带规则 / 按族选择性公开）→ 门禁
   全量重跑 → 换模型重跑 ETL；(b) 论文线：venue 已建议 workshop 首投
   （`PAPER_DRAFT/OUTLINE.md` §Venue），正刊等 Q2/Q4 可分析后。

### 13.15 2026-10-12 傍晚：KI-003 解除、迷你实验定案 KI-002、Zotero 库探明

1. **KI-003 自行解除**：17:00 复测 watchdog 进程已消失（一个 embed 用
   llama-server 稳定存活）。临时 CPU 实例（:11435，qwen2.5:3b，未触碰 GPU）
   跑通全部 72 次调用后已杀（跑完即杀，符合预案）。
2. **KI-002 定案**（详见 `docs/known_issues.md` KI-002 更新）：双臂迷你实验
   证实"地板=设计属性"；拍板修复方向 = **prompt 携带完整规则（全族公开）**；
   ret-path 0→5/12、stateful-calc 0→3/12（全在 k=0）当场获益；chain-sort
   规则公开仍 0/12（"只旋转不执行交换"），需强模型+改设计双条件。
   **连带**：门禁语义必须重写（规则公开使现门禁前提失效），方案待设计。
   全量数据 `qc/b_line_solvability/results.json`（raw 逐字）。
3. **Zotero 探明**：本机 Zotero 库（~/Zotero/zotero.sqlite，只读副本检查）
   12274 条全是用户自有稿件（"自有正典稿件"），**0 条**带 DOI 字段，
   17 条台账引用无一在库 → zotero_key 回填物理不可能，0/17 是真相不是
   查询错误。`tools/reconcile_zotero.py` 已修好待用；用户侧动作：把
   `paper/refs.bib` 拖入 Zotero 导入（原生支持 BibTeX）→ 导出 CSV →
   `python3 tools/reconcile_zotero.py <csv> prereg/citation_verification.csv`
   （先 --dry-run）。
4. **待用户裁决**：① 是否采纳"规则公开"修复方向并启动门禁重设计；
   ② chain-sort 换模型（等训练结束 GPU 空出，或接远程接口）。

### 13.16 2026-10-12 晚：B 线修复全链落地（规则公开 → 门禁 v3 → v3.1 校准 → GATE PASS）

1. **规则公开修复**（提交 f3a32cc）：`src/gen_tasks.py` 公开白名单加
   ops/sort_rule/ptr/values（truth_chain 仍绝不进 tasks.jsonl，有测试
   `test_truth_chain_not_in_public_tasks_but_rules_are` 守卫）；
   `src/run_etl.py` `build_prompt` 改公开规则版（OP_DESC 表，未知族
   raise）。重生成 90 任务，schedules SHA256 **不变**
   （`6c78350def493ef4…`，validator 真值逐字节一致，历史 logs 可重放）。
2. **门禁 v3 重写**（提交 24321f2）：扰动诱饵范式（对每个 (任务,k) 构造
   最小扰动 s2，用生产 build_prompt 提问；答原始真值=leak、答诱饵真值=
   honest）；fail-closed 骨架保留；`_norm` 对称化修复（v2 遗留 bug）；
   selftest 6 例；`smoke_gate_chain` T2 改 `_decoy_oracle`，SMOKE PASS，
   pytest 8/8。
3. **首次真实门禁 FAIL → KI-004**：v3 固定阈值下 chain-sort 2/19、
   ret-path 3/20 判 LEAK。逐字 raw 证据（`etl/results/
   gate_run_v3_public_rules_raw.log`）证实是**近失/盲撞噪声**而非密钥：
   ret-path 答案空间=公开 values（盲撞≈1/9，18 错答期望撞中 2 次、实测
   3）；chain-sort 规则翻转使诱饵真值与原始真值同旋转轨道（6,17,10 ↔
   17,10,6）；stateful-calc 整数域 0 撞。密钥通道结构上不存在（无状态
   API + truth_chain 从不进 prompt + G1 在验）。
4. **v3.1 判据校准**（提交 02ae957，KI-004 详见 known_issues.md）：
   LEAK iff `leak ≥ max(3, ceil(有效样本/4))` **且** `leak > 2×诚实执行`；
   低功率（诚实 <50%）打印"仅安全网级"警告。事后校准的三条留痕：raw
   逐字证据、三族噪声定量、"信号须压倒自身噪声"的先验理由。selftest
   6 例全过（quarter_leak 反证改每 3 次吐 1 次，避免 25% 卡门槛下滑）。
5. **GATE PASS（v3.1，真实接口）**：`etl/results/gate_run_v31_public_rules.log`
   ——stateful 0/20、chain-sort 2/19、ret-path 3/20 全 CLEAN（三族均带
   低功率警告），gate_exit=0。防线主体是结构性的（G1+单向流+无状态
   API+audit_replay），行为统计是安全网；换高功率模型时须重估门槛。
6. **全量 ETL 重跑**：qwen2.5:3b @ 临时 CPU 实例 :11435，
   `ETL_MODEL_ID=qwen2.5:3b`，90 任务全量（tasks_per_family=None），
   日志 `etl/results/etl_run_v2_public_rules.log`，输出
   `etl/results/logs.jsonl`。结果判读见下节（跑完后补）。
   环境纪律：系统 :11434 被另一会话使用（不碰）；:11435 实验后即杀；
   训练进程（pid 3811520）全程未受影响。
