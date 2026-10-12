# ETL 结果片段 (自动生成, 严禁手抄)

## 整体语义正确率

| model | family | step_acc | parse_ok | first_err_median |
|---|---|---|---|---|
| llama3.1:8b | chain-sort | 0.0 | 0.0 | 0.0 |
| llama3.1:8b | ret-path | 0.0 | 0.0 | 0.0 |
| llama3.1:8b | stateful-calc | 0.0235 | 0.0235 | 0.0 |

> step_acc = 语义正确率 (经 Validator 真值判分); parse_ok = JSON 合法率。
> 注意: 以上数字未经预注册假设检验, 引用前对照 preregistration_c2.md 判读规则。
