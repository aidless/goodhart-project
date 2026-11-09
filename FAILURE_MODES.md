# FAILURE_MODES

这三件事都会让一次跑批看起来像成功。数字出处是 `CLAIM_LEDGER.md` 和已提交文件，不在这里另算一套。

## Leakage false greens

门禁输出 CLEAN 或 GATE PASS，不等于没有泄漏。

- `etl/results/gate_run.log` 里三族都是 0/20 然后 GATE PASS。同一批语义正确率是 5/614。0 命中来自模型几乎答不对，不是来自「门禁抓得住泄漏」。`docs/HANDOVER.md` §13.13 已经写了这一条。
- 那份日志里 chain-sort 的阈值是 125%。命中率最高也只有 100%，这一族在那套阈值下不会判 LEAK。记录在 `docs/known_issues.md` KI-001。
- 现行 v3.1（KI-004）要求泄漏命中压过诚实执行。低执行功率时，盲撞也可以是 CLEAN。绿灯只说明「原始真值没有占主导」。
- `etl/data/schedules/schedules.pkl` 不入库，但 `src/gen_tasks.py` 会在本地生成它。门禁查的是 prompt 里有没有真值链，查不到「进程直接读了 pickle」。

## Proxy hacking still looking like success

代理分最高的那一档，可以同时是真实分最差的一档。

- 已提交 `report/data/summary.csv` 重算后，α=1.0 的 proxy 均值是全程最大（1.3762），true 均值是全程最低（−2.2205）。只画训练回报或 proxy 的人会把这一档当成最好。
- α=0.5 的 `steps_alive` 五次都是 500（环境上限）。存活打满看起来像完全成功，这一档 true 分里的信号在超速罚分上。预注册 `prereg/preregistration_c2.md` 把这件事写成了必须同时报告的附带条件。
- `src/analyze_c2.py` 的 `verdict()` 只按 true 跌幅的点估计打印档位，不检查「proxy 达峰后继续上升」。预注册第 3 条在这批数据上字面不满足。打印出来的档位不是完整判据。

## Seed fragility

n=5，而且有两处方差不能当成稳定性。

- 每个 seed 的 true 峰都在网格最左端 α=0.5。α* 的方差是 0，因为峰被删失在边界上，不是因为峰的位置测稳了。见 `CLAIM_LEDGER.md` 的 I-C2-H2。
- Q5 的速度偏差配对差约 −0.001264（`qc/q5_claims/evidence/q5_speeddev_paired.csv`）。n=5 的 bootstrap 是在这五个差上重抽样。CI 不含 0 仍然可以是一个很小的共同偏差，不是「压线 vs 冲速」。
- C.2 的 95% CI 同样是每个 α 上 5 个 seed 的重抽样。换一个 seed，区间会动。功效补记用的是这同一批配对差，不能当成更大样本。
