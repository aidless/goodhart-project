#!/usr/bin/env bash
# 离线证据路径。不训练 PPO, 不调用模型。
# 解释器默认 python3, 可用 PYTHON=python 覆盖。
set -euo pipefail

cd "$(dirname "$0")"

if [ -n "${PYTHON:-}" ]; then
  PY="$PYTHON"
elif [ -x .venv/bin/python ]; then
  PY=".venv/bin/python"
else
  PY="python3"
fi

if ! command -v "$PY" >/dev/null 2>&1; then
  echo "错误: 找不到解释器 '$PY'。请设置 PYTHON=<你的解释器> 后重试。" >&2
  exit 127
fi

echo "=== offline evidence: no PPO training, no model calls ==="

echo "=== [1/7] 依赖 (numpy pandas matplotlib; 不含 torch) ==="
"$PY" -c "import numpy, pandas, matplotlib; print('基础依赖 OK')"

echo "=== [2/7] 生成任务。schedules.pkl 不入库 ==="
"$PY" src/gen_tasks.py

echo "=== [3/7] leak_check --selftest (不访问模型) ==="
"$PY" src/leak_check.py --selftest

echo "=== [4/7] 重放已提交 logs ==="
"$PY" src/audit_replay.py etl/results/archive_20261008_hidden_rules/logs.jsonl
"$PY" src/audit_replay.py etl/results/archive_20261012_public_rules/logs.jsonl
"$PY" src/audit_replay.py etl/results/logs_chainsort_qwen7b.jsonl
"$PY" src/audit_replay.py etl/results/logs_chainsort_v2_showstate_qwen3b.jsonl
"$PY" src/audit_replay.py etl/results/logs_chainsort_v2_showstate_qwen7b.jsonl

echo "=== [5/7] 从已提交 summary 重算 C.2 表 (写到 gitignore 的 c2/results/) ==="
"$PY" src/analyze_c2.py report/data/summary.csv c2/results

echo "=== [6/7] 从已提交归档重算 ETL 表 (不写回 archive_) ==="
"$PY" src/analyze_etl.py etl/results/archive_20261008_hidden_rules/logs.jsonl etl/results/offline_recompute/b1
"$PY" src/analyze_etl.py etl/results/archive_20261012_public_rules/logs.jsonl etl/results/offline_recompute/b2

echo "=== [7/7] drift check, 含本地重算产物 ==="
"$PY" src/drift_check.py --require-recompute

echo "=== pytest ==="
"$PY" -m pytest tests -q

echo "离线路径完成。训练是可选项, 不在 CI 里: python3 src/train_c2.py 与 python3 src/train_q5.py (需要 torch 与 stable-baselines3)。"
