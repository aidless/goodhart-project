#!/usr/bin/env bash
# 全流程一键脚本。任何一步失败即中止 (set -e)。
# 解释器: 默认 python3, 可用 PYTHON=python 覆盖 (部分系统无 python3 别名)。
set -euo pipefail

cd "$(dirname "$0")"

PY="${PYTHON:-python3}"

if ! command -v "$PY" >/dev/null 2>&1; then
  echo "错误: 找不到解释器 '$PY'。请设置 PYTHON=<你的解释器> 后重试。" >&2
  exit 127
fi

echo "=== [0/5] 环境检查 (解释器: $PY) ==="
"$PY" -c "import numpy, pandas, matplotlib; print('基础依赖 OK')"

echo "=== [1/5] 生成任务与隐藏 schedules ==="
"$PY" src/gen_tasks.py

echo "=== [2/5] 泄漏门禁 (未过则中止) ==="
"$PY" src/leak_check.py

echo "=== [3/5] 跑 ETL ==="
"$PY" src/run_etl.py

echo "=== [4/5] 事后审计 (mismatch 必须为 0) ==="
"$PY" src/audit_replay.py

echo "=== [5/5] 分析出图 ==="
"$PY" src/analyze_etl.py

echo "全部完成。结果见 etl/results/"