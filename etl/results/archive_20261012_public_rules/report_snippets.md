# ETL 结果片段 (自动生成, 严禁手抄)

## 整体语义正确率

| model | family | step_acc | parse_ok | first_err_median |
|---|---|---|---|---|
| qwen2.5:3b | chain-sort | 0.1168 | 0.1168 | 0.0 |
| qwen2.5:3b | ret-path | 0.1912 | 0.1912 | 0.0 |
| qwen2.5:3b | stateful-calc | 0.1174 | 0.1174 | 1.0 |

> step_acc = 语义正确率 (经 Validator 真值判分); parse_ok = JSON 合法率。
> 注意: 以上数字未经预注册假设检验, 引用前对照 preregistration_c2.md 判读规则。
