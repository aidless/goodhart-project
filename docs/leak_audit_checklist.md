# 防泄漏审计清单 (硬约束, 非建议)

## 跑前
- [ ] tasks/ 与 schedules/ 分目录; schedules.pkl 未被任何 prompt 拼接
- [ ] leak_check.py 三族门禁全部打印 CLEAN
- [ ] 门禁阈值 = max(0.02, 2.5 × 随机基线), 未被人为放宽

## 跑中
- [ ] run_etl.py 的 build_prompt 只含公开字段 (逐族核对)
- [ ] 无 prompt 包含 truth_chain / ops / ptr / values

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

- [ ] **`chain-sort` 族阈值偏松**: 基线 `1/(len(init_seq)+1)` → 阈值约 36%–63%,
      同一个 25% 泄漏者在该族判 CLEAN。需为"候选是序列"的族单独推导盲猜基线。
- [ ] **门禁链第 3–5 步从未在真实数据上跑过**: `run_all.sh` 在门禁处 fail-closed
      中止 (`model_call` 是占位实现)。接入真实模型接口后才谈得上验证
      run_etl / audit_replay / analyze_etl。
