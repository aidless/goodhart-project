"""B: 生成三任务族。真值链只进 schedules, 绝不进 tasks。"""
import hashlib
import json
import os
import pickle
import random

# chain-sort 的隐藏规则域。抽成常量是为了让 leak_check 的盲猜基线
# 能与生成器共用同一个定义 —— 候选数必须由"规则域大小"推导, 不能拍脑袋。
SORT_RULES = ("asc", "desc")


def make_stateful_calc(rng, n_steps=None):
    """整数规则链: 每步施加一个隐藏算子。"""
    x0 = rng.randint(1, 9)
    n = n_steps or rng.randint(4, 10)
    op_pool = ["add3", "mul2", "sub1", "add7", "mul3", "xor5"]
    ops = [rng.choice(op_pool) for _ in range(n)]
    return {"family": "stateful-calc", "x0": x0, "ops": ops, "n_steps": n}

def make_chain_sort(rng, n_steps=None):
    """序列逐步变换。规则: 相邻对按规则比较后交换/累加。"""
    m = rng.randint(3, 6)
    init_seq = [rng.randint(1, 20) for _ in range(m)]
    n = n_steps or rng.randint(4, 9)
    sort_rule = rng.choice(SORT_RULES)
    return {"family": "chain-sort", "init_seq": init_seq,
            "sort_rule": sort_rule, "n_steps": n}

def make_ret_path(rng, n_steps=None):
    """指针链: 从 idx=0 出发沿 ptr 跳 n 步, 每步取 values[idx]。"""
    m = rng.randint(5, 9)
    ptr = list(range(m))
    rng.shuffle(ptr)
    values = [rng.randint(10, 99) for _ in range(m)]
    entries = [f"e{i}" for i in range(m)]
    n = n_steps or rng.randint(4, 9)
    return {"family": "ret-path", "ptr": ptr, "values": values,
            "entries": entries, "n_steps": n}

OPS = {
    "add3": lambda x: x + 3,
    "mul2": lambda x: x * 2,
    "sub1": lambda x: x - 1,
    "add7": lambda x: x + 7,
    "mul3": lambda x: x * 3,
    "xor5": lambda x: x ^ 5,
}

def apply_chain_sort(seq, step_idx, rule):
    """第 step_idx 步的确定性变换：rotate 一位并按 rule 决定是否交换前两元素。

    与 truth 链的每一步严格对应，保证 validator 可重算。
    """
    seq = list(seq)
    if not seq:
        return seq
    # 1) 循环右移一位
    seq = [seq[-1]] + seq[:-1]
    # 2) 按规则决定前两元素是否交换
    if len(seq) >= 2:
        a, b = seq[0], seq[1]
        should_swap = (rule == "asc" and a > b) or (rule == "desc" and a < b)
        if should_swap:
            seq[0], seq[1] = b, a
    return seq

def _truth_chain(s):
    """按族逐步计算真值链。"""
    fam = s["family"]
    chain = []
    if fam == "stateful-calc":
        x = s["x0"]
        for op in s["ops"]:
            x = OPS[op](x)
            chain.append(x)
    elif fam == "chain-sort":
        seq = list(s["init_seq"])
        for i in range(s["n_steps"]):
            seq = apply_chain_sort(seq, i, s["sort_rule"])
            chain.append(list(seq))
    elif fam == "ret-path":
        idx = 0
        for _ in range(s["n_steps"]):
            idx = s["ptr"][idx]
            chain.append(s["values"][idx])
    return chain

def main(n_per_family=30, seed=0,
         tasks_path="etl/data/tasks/tasks.jsonl",
         sched_path="etl/data/schedules/schedules.pkl"):
    rng = random.Random(seed)
    os.makedirs(os.path.dirname(tasks_path), exist_ok=True)
    os.makedirs(os.path.dirname(sched_path), exist_ok=True)

    tasks, schedules = [], {}
    makers = [make_stateful_calc, make_chain_sort, make_ret_path]
    for fam_i, maker in enumerate(makers):
        for i in range(n_per_family):
            s = maker(rng)
            tid = f"{s['family']}-{fam_i}-{i:03d}"
            s["task_id"] = tid
            s["truth_chain"] = _truth_chain(s)
            schedules[tid] = s

            # 公开任务 (v2, 2026-10-12 设计变更): 规则字段 (ops/sort_rule/
            # ptr/values) 随任务公开 —— KI-002 迷你实验证实规则隐藏时三族真值
            # 不可推导, 地板是设计属性 (qc/b_line_solvability/results.json)。
            # 规则 ≠ 答案键: 公开规则后仍须逐步执行才能得到真值。
            # truth_chain 仍然绝不进 tasks, 只在 schedules (validator 侧)。
            public = {k: v for k, v in s.items()
                      if k in ("task_id", "family", "n_steps", "x0",
                               "init_seq", "entries", "sort_rule",
                               "ops", "ptr", "values")}
            public["task_id"] = tid
            tasks.append(public)

    with open(tasks_path, "w") as f:
        for t in tasks:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")

    with open(sched_path, "wb") as f:
        pickle.dump(schedules, f)

    with open(sched_path, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    with open("etl/data/schedules/SHA256.txt", "w") as f:
        f.write(digest + "\n")

    print(f"生成 {len(tasks)} 任务, schedules sha256={digest[:16]}...")

if __name__ == "__main__":
    main()