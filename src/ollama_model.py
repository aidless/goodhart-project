"""ollama_model.py — 本地 Ollama 真实 model_call (标准库 urllib)。

约定 (任务要求):
- endpoint: http://127.0.0.1:11434/v1/chat/completions (无 key)
- 模型: 默认 llama3.1:8b (qwen3:4b 在 max_tokens=50 下被 thinking 占满,
  实测 content 为空且 finish=length, 不可用; 见返回报告)。
  可用环境变量 OLLAMA_MODEL 覆盖, 但默认按任务要求二选一中的可用者。
- timeout 60s, max_tokens 50, 失败重试 1 次后返回 "__UNTESTED__" 不抛异常。
- fail-closed 语义由调用方保持:
  leak_check 把 "__UNTESTED__" 计为 failed (不计入 total),
  全失败时 total==0 → UNTESTED → GATE FAIL;
  run_etl 把 "__UNTESTED__" 当普通回答记入 raw, validator 判 invalid,
  audit_replay 仍可复现 (mismatch=0)。

只用标准库, 不联网 pip, 不打印 key (本接口无 key)。
"""
import json
import os
import urllib.request

OLLAMA_URL = os.environ.get(
    "OLLAMA_URL", "http://127.0.0.1:11434/v1/chat/completions")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
TIMEOUT_S = 60
MAX_TOKENS = 50
UNTESTED = "__UNTESTED__"
SYSTEM_PROMPT = "只输出最终答案，不要解释。数字直接输出数字，序列用逗号分隔输出序列。"


def _post(prompt, timeout=TIMEOUT_S):
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": MAX_TOKENS,
        "temperature": 0,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL, data=data,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = json.loads(r.read().decode("utf-8"))
    try:
        content = body["choices"][0]["message"].get("content")
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"ollama 响应格式异常: {e}")
    if content is None or not str(content).strip():
        raise RuntimeError("ollama 返回空 content (可能被 thinking 占满)")
    return str(content)


def model_call(prompt):
    """真实模型调用。失败重试 1 次, 仍失败返回 UNTESTED, 不抛异常。"""
    last_err = None
    for _ in range(2):  # 初次 + 重试 1 次
        try:
            return _post(prompt)
        except Exception as e:  # noqa: BLE001 — 任何网络/解析/空回包都记 UNTESTED
            last_err = e
    # 两次都失败: 不抛, 记 UNTESTED (调用方按 fail-closed 计 failed)
    _ = last_err
    return UNTESTED


def check_models_available(timeout=10):
    """GET /v1/models 确认模型存在。返回 id 列表。"""
    base = OLLAMA_URL.rsplit("/chat/completions", 1)[0]
    url = base + "/models"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = json.loads(r.read().decode("utf-8"))
    ids = [m.get("id") for m in body.get("data", [])]
    return ids
