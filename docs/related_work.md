# 相关工作与先验对照（prior art）

> 本文档把 goodhart-project 的 claim 与**真实、已核验**的先验文献做对照。
> 所有引用均来自 `paper/refs.bib`，其出处为 `prereg/citation_verification.csv`
> （17 行，全部 `verified=✅`，2026-10-07/08 核验），并已于 2026-10-11 经
> `reference_checker` 独立复核（14 found / 3 partial / 0 not_found）。
> 这是**对照**，不是声称这些文献支持本项目的具体结论。

## 本项目 vs 已有先验

| 维度 | 本项目 claim | 先验文献（真实） | 关系 |
|---|---|---|---|
| Goodhart 定律（度量脱钩） | C.2 控制实验：真实得分在代理峰值处崩溃 | Goodhart 1975/1984（`goodhart1975problems`）；Strathern 1997（`strathern1997improving`，'Improving ratings'） | 本项目把口头定律变成单环境控制实验的**可复算证据**；不证明普遍成立 |
| 度量与代理目标 | 代理得分峰值与真实得分脱钩比 1.005 | Campbell 1979（`campbell1979assessing`，Assessing Planned Social Change） | 同属「度量扭曲行为」传统，本项目用强化学习环境量化 |
| 奖励误指定 | 代理目标与真实目标分离 | Pan et al. 2022 ICLR（`pan2022effects`，Reward Misspecification） | 最接近的机制先验；本项目是链式任务视角，非单步奖励 |
| 链式任务/长程 | 90 任务 × 614 步语义正确率 | Kwa et al. 2025 NeurIPS（`kwa2025measuring`，Measuring AI Ability to Complete Long Software Tasks） | 同属「长程任务可靠性」，本项目聚焦**误差累积**而非任务完成率 |
| 推理链可靠性 | 链式错误累积与重锚定假说 | Wei et al. 2022 NeurIPS（`wei2022chain`，Chain-of-Thought） | 对照：CoT 提升推理；本项目测的是链上**错误传播** |
| 预注册 | 判据跑前锁定 | Nosek et al. 2018（`nosek2018preregistration`，Preregistration Revolution） | 方法论先验，本项目按其纪律执行 |
| 可复现 | mismatch=0 重放 + 逐字原文 | Pineau et al. 2021（`pineau2021improving`，Improving Reproducibility in ML Research） | 方法论先验 |
| 算法基座 | PPO / CartPole | Schulman 2017（`schulman2017proximal`）；Barto 1983（`barto1983neuronlike`） | 工具先验，非贡献 |
| 对齐安全 | 代理目标脱钩 | Amodei 2016（`amodei2016concrete`，Concrete Problems in AI Safety）；Ji et al. 2023（`ji2023alignment`，AI Alignment） | 宏观对齐语境，本项目提供可复算子证据 |
| 能力分级 | 不主张 AGI 分级 | Morris et al. 2024（`morris2024levels`，Levels of AGI） | 对照：本项目不进入能力分级讨论，仅测单项可靠性 |

## 关键差异（创新点）

- **预注册判据 + fail-closed 门禁**：脱钩判定在跑之前锁定三档判据（`prereg/preregistration_c2.md`），
  泄漏门禁注入违规必须判 LEAK（`src/leak_check.py --selftest`，500/500）。多数先验讨论停
  在直觉层面，本项目把「脱钩发生了」变成可审计 claim。
- **链式误差分解而非单步**：已有文献（如 Kwa 2025）测任务完成率；本项目把 614 步逐语义判分，
  分解出 cumulative / 错后恢复 / 梯度，定位**误差累积**这一作用面（exploratory）。
- **单向流防泄漏**：`schedules.pkl` 只被 validator 读取，绝不出现在 prompt 里（README 两条铁律）。

## 边界声明（真实）

- 本项目**不证明** Goodhart 定律普遍成立（单环境/单算法/单代理目标）。
- 本项目**不进入** AGI 能力分级或奖励误指定的因果归因（对照文献各有独立证据）。
- 本项目**不做**模型横向比较（3b/7b/8b 数字不可直接比较，除非控制配置与规则可见性）。
