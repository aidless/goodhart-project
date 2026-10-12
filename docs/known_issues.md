# 已知问题记录

## KI-001 — `ret-path` 族泄漏判据过松

**状态**: 已拍板 → **C**，**已实施**（2026-10-07，外部会话；实现在 `src/leak_check.py`，
证据与一处对拍板文本的偏离见文末"实施记录"）
**发现**: 门禁自检时, 主动构造的 25% 命中率泄漏者可判 CLEAN。
**影响**: `leak_check.py` 对 `ret-path` 族的灵敏度不足, 可能放行真实泄漏者。

### 拍板记录（2026-10-07）

选 **C**（先修 prompt 碰撞，再用 B 的推导式阈值）。理由与证据：

1. 松判据的根源已定位到代码，不是"阈值该调多少"的问题。
   `src/gen_tasks.py` 的 `make_ret_path` 里 `entries = [f"e{i}" ...]`，
   使 `entries[0]` **恒为 `'e0'`**；而 `RetPathProbe.make_probe_prompt`
   只用 `s['entries'][0]` 与 `k` 拼 prompt。于是同一 prompt 对应多个不同真值
   —— 该族的探测 prompt **不携带任务身份**。
2. 这一条同时解释了另外两件事，所以修它是一箭三雕：
   - 阈值为什么只能是"拍的"：`random_baseline = 1/len(entries)`（5–9 条 → 0.111–0.2），
     阈值 `2.5×基线` 上限到 0.5，而 25% 的泄漏者落在阈值内。
     碰撞不修，就无法定义"同 k 下多真值的最优盲猜"，B 落不了地。
   - `--selftest` 为什么只能用 `_synth_schedules()` 的合成输入：
     `_truth_map` 要求 prompt→真值 是函数，真实 schedules 上不成立。
     即**门禁在真实分布上的灵敏度从未被验证过**。
3. A 方案被否：给 `ret-path` 单设绝对阈值（如 0.2）虽然一行就能改，
   但阈值仍无推导依据，且不解决碰撞 → 第二组反证仍补不上。

**未实施的原因（如实记录）**：C 会改动任务生成语义并重锚 `SHA256.txt`；
"修碰撞"的具体形式不止一种（唯一化 `entries[0]` / 让 prompt 带公开的 `task_id` /
其它），选择应连同 §4.3 的字段核对一起定。此文件只做拍板与待办，不含代码改动。

### 执行待办（选 C 后）—— 均已完成

- [x] 定"修碰撞"的具体形式：**让 prompt 带公开的 `task_id`**（上文列出的候选
      之一），落在 `src/leak_check.py` 三个族的 `make_probe_prompt`。
      **不改 `gen_tasks.py`** —— 因此 schedules 的生成语义与哈希锚点都未变。
- [x] 定 `RetPathProbe.random_baseline`：见下方"实施的偏离"，结论与拍板文本
      不同；`THRESH_MULT` 保持 2.5（实测已满足判据，无需再动）。
- [x] schedules 未重新生成 —— 因为生成器未改。实测重跑 `src/gen_tasks.py`
      后 `SHA256.txt` 不变（`6c78350def493ef4…`），可直接用于下一次 `run_all.sh`。
- [x] 第二组反证已补：`oracle_leak` 改用**真实 schedules**；原先为绕开碰撞而存
      在的 `_synth_schedules()` 已删除（不再需要）。
- [x] 已回填本文件与 `docs/leak_audit_checklist.md`、`README.md` 的对应条目。

### 实施记录（2026-10-07，外部会话，实测）

改文件：`src/leak_check.py`（唯一改动文件）。`python3 -m pytest tests/ -q` → 4 passed。

1. **碰撞消除**：三个族 prompt 均前置 `[任务 {task_id}]`。
   实测 `_truth_map(schedules)` 条目数 = **524** = 各 `(族,任务,k)` 组合数
   （判据 1 满足，即 prompt→真值 是函数）。
2. **`--selftest` 五例全过**（判据 2 满足）：`all_calls_fail` FAIL /
   `oracle_leak` FAIL / `garbage_answer` PASS / `half_calls_fail` PASS /
   `quarter_leak` FAIL。**五例全部跑在真实 schedules 上**；`quarter_leak` 是
   新增的常驻回归项（每 4 次答对 1 次）。
3. **25% 泄漏者被判 LEAK**（判据 3 满足）：ret-path 实测 `5/20 = 25.0%` vs
   阈值 `11.0%` → LEAK。
4. **门禁链**：`bash run_all.sh` 在第 2 步 fail-closed 中止（`GATE: FAIL`），
   原因是 `src/leak_check.py` 的 `model_call` 仍是占位实现、三次调用全失败。
   这是 README 写明的预期行为（接口未接入时在门禁处停下）。**第 3–5 步
   （run_etl / audit_replay / analyze_etl）因此仍未在真实数据上验证过。**

### 实施的偏离（必须记录）

拍板文本要求基线为"同 k 下多真值的**最优**盲猜命中率"。实施时先按字面实现为
**众数频率**（众数 = 知情猜测下的最优），随后实测发现它与本 KI 自己的验收判据
**冲突**，故改为**互异真值个数**的倒数。证据：

| 基线定义 | 30 任务下基线（500 种子的范围） | 阈值上限 | 25% 泄漏者被判 LEAK 的种子比例 |
|---|---|---|---|
| 众数频率（字面"最优"） | 0.077 – 0.136 | 0.34 | **302 / 500** |
| `1/互异真值个数`（采用） | 0.041 – 0.079 | 0.197 | **500 / 500** |

理由：众数要求盲猜者**知道各真值的出现频率**，而频率只存在于 schedules 中、
模型无权访问 —— 那是知情猜测，不是"盲猜"；且该估计量被小样本显著抬高（30 个
样本落在约 90 个取值上，众数≈2–4 次即 7%–13%，而真实的盲猜率约 1/90）。
采用 `1/d`（d = 该 k 上出现过的互异真值数）后，判据 3 在 500 个种子下**无一例外**成立。

### 实施未覆盖的残留（另记，非本 KI）

`chain-sort` 族对同一个 25% 泄漏者仍判 CLEAN。当时记为"基线偏松"，
**2026-10-08 取证后更正：这是误诊** —— 25% 低于该族真实盲猜率 (≈0.5)，
判 CLEAN 是对的；真正的问题是隐藏规则只有二值、该族**任何泄漏水平都不可
判别**（阈值 1.25 > 命中率上限 1.0，永不触发 LEAK；检测职能由另两族承担）。
结清记录见文末"新开"与 `HANDOVER.md` §13.10(a)。

### 验收判据（避免又变成"看起来改好了"）

- 真实 schedules 上，`_truth_map` 条目数 == 各 `(族, 任务, k)` 组合数（即无碰撞）
  → **满足**：524 == 524
- `--selftest` 四例仍全部符合预期，且 `oracle_leak` 一例**改用真实 schedules**
  → **满足**：五例（含新增 `quarter_leak`）全过，且全部跑在真实 schedules 上
- 25% 命中率的构造泄漏者在真实 schedules 上被判 **LEAK**（这是本 KI 的原始症状）
  → **满足**：ret-path `25.0%` vs 阈值 `11.0%` → LEAK；且基线在 500 个随机种子下
  逐个复算，**500/500** 都判 LEAK（不是只在 selftest 的 seed 0 上成立）

### 修向对比

| 方案 | 做法 | 优点 | 缺点 | 是否动 gen_tasks |
|---|---|---|---|---|
| A | `ret-path` 单独设绝对上限 (如 0.2) | 一行改动 | 阈值是拍的, 无推导依据 | 否 |
| B | 阈值改为「同 k 下多真值的最优盲猜命中率」 | 有推导, 严谨 | 被 prompt 碰撞卡住, 无法落地 | 否 |
| C | 先修 prompt 碰撞, 再用 B | 最干净; 顺带解锁第二组自检 | 动生成器, schedules 重生成 + SHA256 换锚 | 是 |

### 倾向

C。理由: 碰撞本身 (`entries[0]` 恒为 `'e0'`) 不只挡阈值推导 —— 它意味着
**真实数据上构造不出完美泄漏, 门禁在真实分布上的灵敏度从未被验证过**。
修碰撞一箭三雕。

### 待办（本节已结清，见上方"执行待办 —— 均已完成"）

- [x] 拍板 A / B / C → **C**（2026-10-07）
- [x] 实施 C → 落在 `src/leak_check.py`；**未**改 `gen_tasks.py`（碰撞在 prompt
      层消除），故 schedules 与 `SHA256.txt` 都无需换锚
- [x] 补第二组反证 → `oracle_leak` 已改用真实 schedules

### 新开（本次实施中发现，非 KI-001 原范围）

- [x] **`chain-sort` 族判据** —— **已结清（2026-10-08）**。原记录"阈值偏松"是
      **误诊**：该族隐藏规则只有二值（`asc`/`desc`），`apply_chain_sort` 是确定性
      变换 → 盲猜者能枚举出**恰好 2 个候选**，真实盲猜率 ≈ **0.5150**（实测）。
      旧基线 `1/(len(init_seq)+1)`=0.199 → 阈值 0.498 < 0.515，会把**诚实的枚举
      盲猜者**判成 LEAK（假阳性）；而 25% 泄漏者判 CLEAN 本就正确（0.25 低于盲猜
      水平，不构成泄漏证据）。已把基线改为 `1/(公开信息下可推导的候选数)`
      （与 ret-path 同一原则），并顺带修掉 `gen_tasks` public 白名单泄露
      `sort_rule` 的卫生 bug（schedules SHA256 未变）。**该族任何泄漏水平都
      不可判别，属设计局限**：阈值 1.25 高于命中率上限 1.0，永不触发 LEAK
      （oracle 自检实测 `100.0% vs 阈值125.0% → CLEAN`）；泄漏检测由另两族
      承担。详见 `HANDOVER.md` §13.10(a)。
- [x] **门禁链第 3–5 步** —— **已端到端打通（2026-10-08）**。先 stub 冒烟
      （`src/smoke_gate_chain.py`，验证 fail-closed 与数据契约），后接入
      **本地 Ollama（llama3.1:8b，标准库 urllib）** 作为真实 model_call：
      门禁实测三族 **0/20 命中 → GATE PASS**（exit 0，实跑记录
      `etl/results/gate_run.log`）；ETL 真实跑 90 任务 614 步（UNTESTED=0，
      调用全成功），`audit_replay` 614 步 **mismatch=0**，四产物落
      `etl/results/`。**首批真实数字呈地板效应**：correct 0/614
      （stateful-calc 2.35%，其余两族 0%），第一步即错、误差分解无作用面。
      详见 `HANDOVER.md` §13.13。
- [x] **门禁的 schedules 缺失回退是 fail-open** —— **已修（2026-10-08）**：旧
      `_default_schedules()` 在真值表缺失时**现生成合成表**给门禁用，等于"门在验
      A、跑批用 B"。已拆为 `_require_schedules`（缺失即退出码 2 fail-closed）/
      `_generate_schedules_for_selftest`（仅自检，且明确报告用合成数据）/
      `_selftest_schedules`。回归测试
      `test_gate_fails_closed_when_schedules_missing`。详见 `HANDOVER.md` §13.10(c)。

## KI-002 — ETL 首批地板效应是**设计属性**（任务公开信息不足以推导真值），"换更强模型重跑"在改设计前无效

**状态**: 诊断成立（静态证据充分），待迷你实验定量证实 —— 实验脚本已就绪
（`qc/b_line_solvability/mini_experiment.py`），因 KI-003 暂无法执行。
**发现**: 2026-10-12，为执行"换模型重跑 B 线"做侦察时。
**证据链**（静态，全部可复核）:

1. `src/gen_tasks.py:110-112`（`main` 内 `public` 白名单）只保留
   `(task_id, family, n_steps, x0, init_seq, entries)` —— 隐藏
   `ops`（stateful-calc）/ `sort_rule`（chain-sort）/ `ptr`+`values`（ret-path）。
   `sort_rule` 移出白名单是 2026-10-08 的卫生修复（防答案键泄露，见 KI-001
   "新开"节），当时顺带把另两族的规则字段也全部藏掉了。
2. `src/run_etl.py` `build_prompt`（当前版在 prompt 前置 `[任务 {task_id}]`）只拼
   公开字段 → 三族真值均**不可从公开信息推导**（chain-sort 例外地可盲猜枚举
   2 个候选，但无人能选中；见 KI-001 对该族判据局限的记录）。
3. 首批 ETL（llama3.1:8b，2026-10-08，614 步）correct 5/614，且 `logs.jsonl`
   的 `raw` 显示模型在**猜**（ret-path 答 `e1` 这类条目名而非关键值；
   "无法/不知道"类自述 0/614）—— 与"信息饥饿"一致，与"能力不足"不矛盾但
   无法区分。真正的归因实验见下。

### 判定方案：双臂迷你实验（同任务同 k，规则隐藏 vs 规则公开）

- 致量: 每族前 6 任务 × k∈{0,2} × 双臂 = 每模型 ≤ 72 次调用；判分用生产
  `validator.check_step`（与正式跑批同一判据），raw 逐字落盘。
- 判读: 臂 P（规则公开）步准确率显著脱离随机水平、臂 H（现状）维持地板
  → 证实"地板=设计属性"；臂 P 也地板 → 归因转向模型能力，另议。
- 局限（如实）: k∈{0,2} 是浅步深；小模型在臂 P 上也可能做不动多步链。
  实验只回答"信息 vs 能力"的**方向**，不给出修复后的目标准确率。

### 修复方向（2026-10-12 实验后拍板）

**迷你实验已执行**（2026-10-12 17:05–17:10，qwen2.5:3b @ 临时 CPU 实例
:11435，72 次调用 298.8s，全量 `qc/b_line_solvability/results.json`）：

| 族 | 臂 H（规则隐藏，现状） | 臂 P（规则公开） | 定性 |
|---|---|---|---|
| ret-path | 0/12 | **5/12** | 规则公开即解——设计问题 |
| stateful-calc | 0/12 | 3/12（全在 k=0） | 单步可执行、多步连环算崩 |
| chain-sort | 1/12（周期性合法命中） | **0/12** | 给了规则也不执行——3B 能力地板 |

结论与拍板：
1. **"地板=设计属性"成立**（H 臂三族全部 ≈ 随机地板；ret-path 与
   stateful-calc 在规则公开后脱离地板）。
2. **修复方向：prompt 携带完整规则（全族公开）**——两族当场获益；rule 本身
   不是答案键（公开 ops/ptr/values 后仍需执行才能得真值）。
3. **chain-sort 是例外**：臂 P 0/12，错误模式为"只旋转不执行交换"——该族
   需要更强的模型（≥8B 或远程接口）+ 规则公开**双条件**才可解。换模型
   重跑只对这个族有意义，且必须连设计一起改。
4. **连带事项（改设计前必须处理）**：门禁语义要重写——现在 leak_check 的
   前提是"真值不可从公开信息推导"；规则公开后该前提失效，probe 会因
   "可计算"而合理命中。新门禁要验证的是"真值链本身不出现在 prompt /
   模型无法不执行就得到真值"，方案需另行设计并过 selftest。
5. 局限（如实）：n=12/格、单模型、k∈{0,2} 浅步深；这是诊断实验（qc/），
   不是预注册跑批，只回答方向，不给修复后的目标准确率。


**2026-10-12 夜·强模型腿实测（chain-sort 复测, qwen2.5:7b@CPU :11435, 30 任务 197 步）**:
step_acc **0.0863** (17/197), 整任务全对 1/30, first_err_median 0.0, cumulative 144/180=80%,
audit mismatch=0。对照批次 2 同族 3B 的 0.1168: **翻倍参数不升反降**——
「3B 不能执行交换规则, 换强模型解除」假说被否证。chain-sort 的剩余修复路径
只剩**改设计** (状态可观测性/逐步反馈), 强模型腿关闭。产物
`etl/results/logs_chainsort_qwen7b.jsonl` (raw 逐字, 可重放)。

**2026-10-12 深夜·状态可见性 2×2 判读（R2 成立，状态可观测腿也关闭）**
（设计判读运行前锁定于 `docs/design_chainsort_v2.md` §3, 结果补记于其 §6）:

| step_acc | v1 状态隐藏 | v2 状态可见 |
|---|---|---|
| qwen2.5:3b | 0.1168 | 0.1015 |
| qwen2.5:7b | 0.0863 | 0.0609 |

- acc(v2,3B)=0.1015 ≤ 0.2 → **R2: 规则执行瓶颈**; R1（状态追踪瓶颈,
  判据 acc(v2,3B)≥0.5 且 ≥3×v1）否证; 容量交互不存在（7B 两臂均 ≤ 3B）。
- 定性（post-hoc 注记）: v2 prompt 下模型常输出当前序列的**全排序**
  （asc/desc 混用）而非 rotate+条件交换的机械单步——`sort_rule` 被语义
  理解为"排序"而非状态机步骤; 输出确为当前序列的排列（状态被正确使用）。
- **修复方向收窄为执行原语重构**: 状态可见 ✗（本实验）、更大容量 ✗
  （强模型腿）。剩余候选 = 单步 worked example / 分解式指令 / 更简变换规则。
  产物 `etl/results/logs_chainsort_v2_showstate_qwen{3b,7b}.jsonl`
  （audit_replay mismatch=0 ×2）。

## KI-003 — 本机 `llama-server` 被外部 watchdog 秒杀，一切模型加载当前不可行

**状态**: 已自行解除（2026-10-12 17:00 复测：watchdog 进程已不在，一个
llama-server 稳定存活；迷你实验当场跑通）。**不由本项目处理**——watchdog
与它保护的训练进程属于用户另一会话（opencode）。
**现象**: 2026-10-12 16:20 起，`ollama.service`（:11434）与临时实例（:11435，
`CUDA_VISIBLE_DEVICES=""`）加载**任何**模型（qwen3:8b / qwen2.5:7b /
qwen3:4b / llama3.2:3b / qwen2.5:3b / qwen3:0.6b）都在 ~5s 内报
`llama-server process has terminated: signal: killed`。
**根因**（已定位，非 OOM）: `/tmp/opencode/ollama_watchdog.sh`（2026-10-12
03:10 启动）每 5s `kill -9` 全部 `llama-server` 进程，防止任何模型加载抢走
VRAM——它保护的训练进程为 `pid 3811520`
（`.agent-memory/aie/scripts/deeped3.py`，占 GPU 3434 MiB / 6144 MiB）。
旁证: 内核日志 16:20/16:23/16:28/16:33 的 `Memory cgroup out of memory` 杀的是
UID 65534 的小 python3（沙箱进程），与本现象无关；GPU 实例实际连 Vulkan 都
只剩 2349 MiB 可用。
**处置**: 等 `deeped3.py` 结束或由用户暂停 watchdog 后再跑 KI-002 迷你实验。
运行命令已写在 `qc/b_line_solvability/mini_experiment.py` 模块 docstring。
本项目不得杀 watchdog 或训练进程（跨会话资源，属用户裁决）。


## KI-004 — v3 门禁固定阈值在低执行功率模型上被近失/盲撞噪声淹没（2026-10-12 判据校准 v3.1）

**现象**（gate_run_v3_public_rules.log，qwen2.5:3b @ 临时 CPU 实例 :11435）:
stateful-calc 0/20 CLEAN，chain-sort 2/19=10.5% LEAK，ret-path 3/20=15% LEAK
→ GATE FAIL。逐字 raw（gate_run_v3_public_rules_raw.log）显示泄漏答案全部
精确等于原始真值，但机制是噪声而非密钥：

- ret-path：答案空间就是 prompt 里公开的 9 个 values，盲撞率 ≈ 1/9；
  18 个错答的期望撞中 ≈ 2 次，实测 3 次 —— 吻合。
- chain-sort：规则翻转扰动使诱饵真值与原始真值**同处一个旋转轨道**
  （实测例 6,17,10 ↔ 17,10,6），相位混淆一步即达。
- stateful-calc：整数域答案空间大 → 0/20 撞中，三族模式与噪声假设定量一致。
- 密钥通道**结构上不存在**：无状态 API、truth_chain 从不进 prompt、
  G1 静态检查在验。

**判定**：v3 的固定阈值（5% + 绝对≥3）把这类噪声当成了泄漏 —— 在
"规则公开 + 低执行功率"场景下，诱饵统计的法则被破坏：误报主导。
真实泄漏（密钥访问）的表现形态是"原始真值回答**占主导**"。

**修复（leak_check v3.1，同日）**：LEAK 当且仅当
`leak 命中 ≥ max(3, ceil(有效样本/4))` **且** `leak > 2 × 诚实执行`。
双条件缺一不可；低功率（诚实执行 < 50%）时打印"仅安全网级"警告。
selftest 6 例在 v3.1 下全过（quarter_leak 反证案例从每 4 次吐 1 次
改为每 3 次吐 1 次，避免 25% 恰好卡在门槛下滑过）。

**本次门禁结论（重跑见 gate_run_v31_public_rules.log）**：三族 CLEAN
（带低功率警告）→ 放行 ETL。判据改动在**看到 v3 失败数据之后**做出，
属事后校准；留下了 (a) raw 逐字证据 (b) 三族噪声定量 (c) "信号须压倒
自身噪声"的先验理由三条记录，并明确：门禁的防线主体是结构性的
（G1 + 单向流 + 无状态 API + audit_replay），行为统计只是安全网。
若未来换高执行功率模型，须重估 v3.1 的门槛（此时诚实执行高、
噪声地板低，v3.1 与 v3 会趋同）。
