"""B: ETL runner。逐步询问模型, validator 判分, 落盘 logs.jsonl。"""
import json
import os
from validators import Validator, classify_error

def load_tasks(path="etl/data/tasks/tasks.jsonl"):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]

def build_prompt(task, k):
    """只含公开信息 + 第 k 步提问。绝不泄露真值链。"""
    fam = task["family"]
    if fam == "stateful-calc":
        return (f"从 x0={task['x0']} 开始，按隐藏的整数规则链逐步推进。"
                f"请直接给出第 {k+1} 步的结果（只输出一个整数）。")
    elif fam == "chain-sort":
        return (f"初始序列 {task['init_seq']}。按隐藏规则操作 {k+1} 次后，"
                f"请直接给出序列（用逗号分隔，只输出序列）。")
    elif fam == "ret-path":
        return (f"从条目 '{task['entries'][0]}' 出发，沿隐藏的指针关系走 {k+1} 跳，"
                f"请直接给出到达条目的关键值（只输出该值）。")
    return ""

def run(model_call, out_path="etl/results/logs.jsonl"):
    tasks = load_tasks()
    validator = Validator()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, "w") as f:
        for task in tasks:
            tid = task["task_id"]
            n = task["n_steps"]
            steps = []
            prev_valid = True
            for k in range(n):
                prompt = build_prompt(task, k)
                try:
                    raw = model_call(prompt)
                except Exception as e:
                    raw = f"__ERROR__:{e}"
                valid = validator.check_step(tid, k, raw)
                err_type = classify_error(prev_valid, valid)
                steps.append({
                    "k": k,
                    "valid": valid,
                    "err_type": err_type,
                    "raw": raw,
                })
                prev_valid = valid
            rec = {
                "model": os.environ.get("ETL_MODEL_ID", "unknown"),
                "task_id": tid,
                "family": task["family"],
                "run": 0,
                "steps": steps,
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    def model_call(prompt):
        raise RuntimeError("请接入真实模型接口后再跑; 当前为占位")
    run(model_call)