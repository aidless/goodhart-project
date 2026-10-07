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

- [ ] **`ret-path` 族判据过松**: 随机基线 = `1/len(entries)`, 阈值上限可达 0.5。
      命中率仅约 25% 的泄漏者也可能被判 CLEAN。
      修向: 对 `ret-path` 单独设绝对阈值 (如 0.2), 或改基线为「同 k 下多真值的
      最优盲猜」——后者更严谨, 但需先解决 prompt 碰撞 (见下一条)。
- [ ] **门禁自检测的是「门」, 不是「真实数据上的门」**:
      `--selftest` 的 `oracle_leak` 用 `_synth_schedules()` 构造无碰撞输入,
      因为真实 schedules 里 `ret-path` 的 `entries[0]` 恒为 `'e0'`, prompt 会碰撞
      (同一 prompt 对应多个不同真值), 构造不出「完美泄漏」。
      缺第二组反证: 一份无碰撞的真实分布 schedules。
      在补上之前, 门禁的「能失败」只在合成输入上被证明过。
