# --- acceptance_backfill (EVAL_ACCEPTANCE_STANDARD.md P4) ---
# 证据来源: run_all.sh
# 本机预期红（B 类）：run_all.sh 第 2 步泄漏门禁要调本地 ollama
# (http://127.0.0.1:11434, llama3.1:8b)，服务缺席时门禁 fail-closed（GATE: FAIL）。
# 因此原命令保留为 ci-eval:，eval: 换成仓内离线套件 tests/（8 passed）。
.PHONY: eval ci-eval

eval:
	python3 -m pytest tests -q

ci-eval:
	bash run_all.sh
