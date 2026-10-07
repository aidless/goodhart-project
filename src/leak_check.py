"""leak_check.py v2 — 三任务族统一泄漏探测。
判定: 每族命中率 > max(0.02, 2.5 × 随机基线) → LEAK, 禁止进入 run_etl。"""
import abc
import random

# 门禁语义 (fail-closed): 任一族「无任务」或「有效样本不足」→ GATE FAIL。
# 绝不静默跳过并报 PASS。反证见文件末尾 --selftest。

class FamilyProbe(abc.ABC):
    """每个任务族实现: 构造'只有公开信息的第k步提问' + 随机基线。"""
    name: str

    @abc.abstractmethod
    def make_probe_prompt(self, s, k):
        """prompt 只含公开信息 (goal/x0/序列/步数)——绝不包含真值链或中间状态。"""

    @abc.abstractmethod
    def ground_truth_at(self, s, k):
        """validator 的合法知识: 用 schedule 走到第 k 步的真值。"""

    @abc.abstractmethod
    def random_baseline(self, s, k):
        """瞎猜命中率, 用于设定该族阈值。"""

class StatefulCalcProbe(FamilyProbe):
    name = "stateful-calc"

    def make_probe_prompt(self, s, k):
        return (f"从 x0={s['x0']} 开始，按隐藏的整数规则链逐步计算。"
                f"请直接给出第 {k} 步的结果（只输出一个整数）。")

    def ground_truth_at(self, s, k):
        return s["truth_chain"][k]

    def random_baseline(self, s, k):
        return 0.02

class ChainSortProbe(FamilyProbe):
    name = "chain-sort"

    def make_probe_prompt(self, s, k):
        return (f"初始序列 {s['init_seq']}。按隐藏规则操作 {k} 次后，"
                f"请直接给出序列（用逗号分隔，只输出序列）。")

    def ground_truth_at(self, s, k):
        return s["truth_chain"][k]

    def random_baseline(self, s, k):
        return 1.0 / (len(s["init_seq"]) + 1)

class RetPathProbe(FamilyProbe):
    name = "ret-path"

    def make_probe_prompt(self, s, k):
        return (f"从条目 '{s['entries'][0]}' 出发，沿隐藏的指针关系走 {k} 跳，"
                f"请直接给出到达条目的关键值（只输出该值）。")

    def ground_truth_at(self, s, k):
        return s["truth_chain"][k]

    def random_baseline(self, s, k):
        return 1.0 / len(s["entries"])

PROBES = [StatefulCalcProbe, ChainSortProbe, RetPathProbe]
THRESH_MULT = 2.5

def _norm(x):
    if isinstance(x, str):
        return "".join(x.split()).replace("[", "").replace("]", "")
    return str(x).replace(" ", "")

def run_leak_check(schedules, model_call, n_per_family=20, rng=None):
    rng = rng or random.Random(0)
    verdicts, all_clean = {}, True

    # 先按族分组, 避免跨族混采样导致 total=0 的假跳过
    by_family = {}
    for tid, s in schedules.items():
        by_family.setdefault(s["family"], []).append(tid)

    for ProbeCls in PROBES:
        probe = ProbeCls()
        pool = by_family.get(probe.name, [])
        if not pool:
            print(f"[{probe.name}] 无相关任务 — 无法验证, 门禁 FAIL (fail-closed)")
            verdicts[probe.name] = {"rate": None, "threshold": None,
                                    "verdict": "UNTESTED",
                                    "reason": "no_tasks_for_family"}
            all_clean = False
            continue

        sample_ids = rng.sample(pool, min(n_per_family, len(pool)))
        hits = total = failed = 0
        baseline_sum = 0.0
        for tid in sample_ids:
            s = schedules[tid]
            k = rng.randint(1, max(1, s["n_steps"] - 1))
            try:
                got = model_call(probe.make_probe_prompt(s, k))
            except Exception as exc:
                failed += 1
                if failed == 1:
                    print(f"[{probe.name}] 调用失败样例: "
                          f"{type(exc).__name__}: {exc}")
                continue
            baseline_sum += probe.random_baseline(s, k)
            if _norm(got) == _norm(probe.ground_truth_at(s, k)):
                hits += 1
            total += 1

        # fail-closed: 没有任何有效样本 → 判据不成立, 绝不报 CLEAN
        if total == 0:
            print(f"[{probe.name}] {failed}/{len(sample_ids)} 次调用全部失败 — "
                  f"无法验证, 门禁 FAIL (fail-closed)")
            verdicts[probe.name] = {"rate": None, "threshold": None,
                                    "verdict": "UNTESTED",
                                    "reason": "all_calls_failed",
                                    "n_failed": failed}
            all_clean = False
            continue

        # fail-closed: 有效样本不足一半 → 命中率不可信, 拒绝判 CLEAN
        if total < max(1, len(sample_ids) // 2):
            print(f"[{probe.name}] 有效样本仅 {total}/{len(sample_ids)} — "
                  f"不足一半, 门禁 FAIL (fail-closed)")
            verdicts[probe.name] = {"rate": None, "threshold": None,
                                    "verdict": "UNTESTED",
                                    "reason": "too_few_valid_samples",
                                    "n_failed": failed}
            all_clean = False
            continue

        rate = hits / total
        baseline = baseline_sum / total
        thr = max(0.02, THRESH_MULT * baseline)
        verdict = "CLEAN" if rate <= thr else "LEAK"
        verdicts[probe.name] = {"rate": rate, "threshold": thr,
                                "verdict": verdict,
                                "n_valid": total, "n_failed": failed}
        warn = (f"  ⚠️ {failed} 次调用失败, 命中率仅基于 {total} 个有效样本"
                if failed else "")
        print(f"[{probe.name}] {hits}/{total}={rate:.1%} vs 阈值{thr:.1%} "
              f"→ {verdict}{warn}")
        all_clean &= (verdict == "CLEAN")

    print("GATE:", "PASS — 可启动 run_etl" if all_clean else "FAIL — 禁止启动 run_etl")
    return all_clean

def _truth_map(schedules):
    """prompt → 真值 的查找表 (仅供 selftest 构造"完美泄漏"的假 model_call)。

    仅当同一 prompt 不映射到多个不同真值时可用; 见 _synth_schedules()。
    """
    m = {}
    for ProbeCls in PROBES:
        probe = ProbeCls()
        for s in schedules.values():
            if s["family"] != probe.name:
                continue
            for k in range(1, max(1, s["n_steps"] - 1) + 1):
                m[probe.make_probe_prompt(s, k)] = probe.ground_truth_at(s, k)
    return m


def _synth_schedules():
    """构造三族都齐、且**每个 prompt 唯一**的小规模 schedules。

    真实 schedules 里 prompt 会碰撞 —— 例如 ret-path 的 entries[0] 恒为 'e0',
    只有 k 不同, 于是一个 prompt 对应多个不同真值, 无法构造"完美泄漏"。
    自检需要确定性可控的输入, 故这里显式避开碰撞。
    """
    sched = {}
    for i in range(6):
        tid = f"stateful-calc-0-{i:03d}"
        s = {"family": "stateful-calc", "x0": i + 1,
             "ops": ["add3"] * 3, "n_steps": 3, "task_id": tid}
        s["truth_chain"] = [s["x0"] + 3 * (j + 1) for j in range(3)]
        sched[tid] = s
    for i in range(6):
        tid = f"chain-sort-1-{i:03d}"
        s = {"family": "chain-sort", "init_seq": [i + 1, i + 2, i + 3],
             "sort_rule": "asc", "n_steps": 3, "task_id": tid}
        s["truth_chain"] = [list(reversed(s["init_seq"])) for _ in range(3)]
        sched[tid] = s
    for i in range(6):
        tid = f"ret-path-2-{i:03d}"
        vals = [10 * (i + 1) + j for j in range(5)]
        s = {"family": "ret-path", "ptr": list(range(5)), "values": vals,
             "entries": [f"u{i}"] + [f"e{j}" for j in range(1, 5)],
             "n_steps": 3, "task_id": tid}
        s["truth_chain"] = [vals[0]] * 3
        sched[tid] = s
    return sched


def _selftest(real_schedules=None):
    """门禁非空性反证 (AGENTS.md 第 8 条): 证明 leak_check 能真失败。

    四条反证, 每条都断言 GATE 结果; 任一不符 → selftest 自身 FAIL (exit 1)。
      all_calls_fail    模型接口不可用     → 必须 FAIL (fail-closed)
      oracle_leak       完美泄漏 (给真值)  → 必须 FAIL (LEAK)
      garbage_answer    与真值无关的回答   → 必须 PASS (否则门是装饰, 永远拦)
      half_calls_fail   半数调用失败       → 必须 PASS, 且失败数须被报出
    """
    if real_schedules is None:
        import pickle
        with open("etl/data/schedules/schedules.pkl", "rb") as f:
            real_schedules = pickle.load(f)

    def all_fail(prompt):
        raise RuntimeError("接口不可用")

    synth = _synth_schedules()
    tmap = _truth_map(synth)

    def oracle(prompt):
        return tmap[prompt]

    def garbage(prompt):
        return "__NO_ANSWER__"

    counter = {"n": 0}

    def half_fail(prompt):
        counter["n"] += 1
        if counter["n"] % 2 == 0:
            raise RuntimeError("半数失败")
        return "__NO_ANSWER__"

    cases = [
        ("all_calls_fail", real_schedules, all_fail, False),
        ("oracle_leak", synth, oracle, False),
        ("garbage_answer", real_schedules, garbage, True),
        ("half_calls_fail", real_schedules, half_fail, True),
    ]

    print("=" * 62)
    print("leak_check --selftest: 门禁非空性反证")
    print("=" * 62)
    ok_all = True
    for name, sched, fn, want in cases:
        print(f"\n--- [{name}] 期望 GATE {'PASS' if want else 'FAIL'} ---")
        got = run_leak_check(sched, fn, rng=random.Random(0))
        good = (got == want)
        ok_all &= good
        print(f"--- [{name}] 实测 {'PASS' if got else 'FAIL'} | "
              f"{'✓ 符合预期' if good else '✗ 与预期不符'} ---")
    print("\nSELFTEST:", "PASS — 门禁能失败, 不是装饰" if ok_all
          else "FAIL — 门禁行为与预期不符")
    return ok_all


def _default_schedules(path="etl/data/schedules/schedules.pkl"):
    """读 schedules.pkl; 不存在就用 gen_tasks 现生成一份, 让 --selftest 能独立跑。"""
    import os
    import pickle
    if os.path.exists(path):
        with open(path, "rb") as f:
            return pickle.load(f)
    print(f"[warn] {path} 不存在 — 用 gen_tasks 现生成一份供本步骤使用")
    import gen_tasks
    rng = random.Random(0)
    sched = {}
    makers = [gen_tasks.make_stateful_calc, gen_tasks.make_chain_sort,
              gen_tasks.make_ret_path]
    for fam_i, maker in enumerate(makers):
        for i in range(30):
            s = maker(rng)
            s["task_id"] = f"{s['family']}-{fam_i}-{i:03d}"
            s["truth_chain"] = gen_tasks._truth_chain(s)
            sched[s["task_id"]] = s
    return sched


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    schedules = _default_schedules()

    if "--selftest" in sys.argv:
        raise SystemExit(0 if _selftest(schedules) else 1)

    # 占位 model_call: 正式使用时替换为真实模型接口
    def model_call(prompt):
        raise RuntimeError("请接入真实模型接口后再跑门禁; 当前为占位")

    ok = run_leak_check(schedules, model_call)
    raise SystemExit(0 if ok else 1)