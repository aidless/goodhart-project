# 防泄漏审计清单 (硬约束, 非建议)

## 跑前
- [ ] tasks/ 与 schedules/ 分目录; schedules.pkl 未被任何 prompt 拼接
- [ ] leak_check.py 三族门禁全部打印 CLEAN
- [ ] 门禁判据 = **v3 扰动诱饵** (2026-10-12 起): 诱饵泄漏率 > max(0.05, 2×0.02)
      或绝对命中 ≥ 3 → LEAK; 旧式「命中率 vs 2.5×随机基线」判据已随规则公开
      设计 (KI-002) 废止

## 跑中
- [ ] run_etl.py 的 build_prompt 只含**公开**字段 (逐族核对; v2 设计下规则
      ops/sort_rule/ptr/values 随任务公开, 属预期)
- [ ] 无 prompt 包含 truth_chain (答案键) —— 规则 ≠ 答案键, 公开规则后仍须
      逐步执行才能得到真值

## 跑后
- [ ] audit_replay.py mismatch = 0
- [ ] schedules SHA256 与跑前一致 (未被中途修改)
- [ ] logs.jsonl 的 raw 字段为逐字原文, 无转述

## 违规处理
任一项未过 → 该批数据作废, 修复后重跑。禁止"取部分数据先用"。
## 已知未决项 (非门禁, 但影响判据可信度)

- [x] **`ret-path` 族判据过松** —— **已修 (2026-10-07, KI-001 C)**。
      根因不是阈值该调多少, 而是该族 prompt 不带任务身份 (`entries[0]` 恒为 `'e0'`)。
      已在 `src/leak_check.py` 三族 prompt 前置公开的 `task_id` (碰撞消于 prompt 层,
      `gen_tasks.py` 未动, schedules 与 SHA256 锚点不变); 基线改为
      `1/(该 k 上互异真值个数)`。实测 25% 泄漏者 → `25.0%` vs 阈值 `11.0%` → LEAK,
      且 500 个随机种子下 **500/500** 判 LEAK。
- [x] **门禁自检测的是「门」, 不是「真实数据上的门」** —— **已修**。
      `oracle_leak` 已改用真实 schedules; 为绕开碰撞而设的 `_synth_schedules()`
      已删除。`--selftest` 现为五例 (`all_calls_fail` / `oracle_leak` /
      `garbage_answer` / `half_calls_fail` / `quarter_leak`), 全部跑在真实分布上。

## 仍然未决 (本次实施中发现, 不属 KI-001 原范围)

- [x] **`chain-sort` 族判据** —— **已结清 (2026-10-08)**。原记"阈值偏松"是**误诊**:
      该族隐藏规则只有二值 → 盲猜者可枚举恰好 2 个候选 → 真实盲猜率 ≈0.5。
      25% 泄漏者判 CLEAN 本就正确。已把基线改为 `1/(公开信息下可推导候选数)`,
      并移除 public 白名单里的 `sort_rule`。**该族任何泄漏水平都不可判别**:
      阈值 1.25 > 命中率上限 1.0, 永不触发 LEAK (oracle 自检实测
      `100.0% vs 阈值125.0% → CLEAN`), 检测职能由另两族承担, 属设计局限
      (见 `HANDOVER.md` §13.10(a))。
      **→ 2026-10-12 追记: 该局限已随 v3 扰动诱饵范式消除** —— 规则公开后
      盲猜者集中于诱饵真值 (按构造 ≠ 原始真值), chain-sort 恢复完整检测力
      (selftest oracle 案例实测 100% → LEAK)。上述 2026-10-08 记录按历史保留。
- [x] **门禁链第 3–5 步** —— **基础设施冒烟已通过 (2026-10-08)**: `src/smoke_gate_chain.py`
      用确定性 stub 验证 fail-closed 与 run_etl→audit_replay→analyze_etl 契约,
      产物落临时目录。**真实模型调用仍被『环境无 LLM 凭据』阻塞**, 真实数字尚不存在
      (见 `HANDOVER.md` §13.10(b))。
- [x] **门禁的 schedules 缺失回退是 fail-open** —— **已修 (2026-10-08)**: 旧
      `_default_schedules()` 在真值表缺失时现生成合成表给门禁用 (门在验 A、跑批用 B)。
      现正式门禁走 `_require_schedules()`, 缺失即退出码 2 fail-closed;
      合成表仅供 `--selftest` 且明确报告 (见 `HANDOVER.md` §13.10(c))。

## 跑前补充检查 (2026-10-08 增, 2026-10-12 随 KI-002 设计变更更新)

- [ ] 公开 `tasks.jsonl` **不得含 truth_chain** (答案键), 且**必须含规则字段**
      (`ops` / `sort_rule` / `ptr` / `values`, 按族) —— 由
      `tests/test_smoke.py::test_truth_chain_not_in_public_tasks_but_rules_are` 守护。
      旧契约「规则字段也隐藏」已于 2026-10-12 反转 (KI-002: 规则隐藏时三族
      真值不可推导, 地板是设计属性); 提交 f3a32cc + 24321f2。
- [ ] v3 门禁的构造不变量成立: 每个抽样的诱饵真值 ≠ 原始真值
      (`--selftest` 的 decoy_disjoint 案例守护, 实测 219 个 (任务,k) 全判别)

