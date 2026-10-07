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
    def random_baseline(self, s, k, pool=None):
        """瞎猜命中率, 用于设定该族阈值。

        pool = 该族的全部 schedule 对象。需要"同 k 下多真值"统计的实现
        (见 RetPathProbe) 用它推导基线; 其余实现忽略。
        """

class StatefulCalcProbe(FamilyProbe):
    name = "stateful-calc"

    def make_probe_prompt(self, s, k):
        # 带公开的 task_id: 不同任务可能撞同一 x0, 不带身份则 prompt 碰撞
        return (f"[任务 {s['task_id']}] 从 x0={s['x0']} 开始，"
                f"按隐藏的整数规则链逐步计算。"
                f"请直接给出第 {k} 步的结果（只输出一个整数）。")

    def ground_truth_at(self, s, k):
        return s["truth_chain"][k]

    def random_baseline(self, s, k, pool=None):
        return 0.02

class ChainSortProbe(FamilyProbe):
    name = "chain-sort"

    def make_probe_prompt(self, s, k):
        return (f"[任务 {s['task_id']}] 初始序列 {s['init_seq']}。"
                f"按隐藏规则操作 {k} 次后，"
                f"请直接给出序列（用逗号分隔，只输出序列）。")

    def ground_truth_at(self, s, k):
        return s["truth_chain"][k]

    def random_baseline(self, s, k, pool=None):
        return 1.0 / (len(s["init_seq"]) + 1)

class RetPathProbe(FamilyProbe):
    name = "ret-path"

    def make_probe_prompt(self, s, k):
        # 带公开的 task_id: entries[0] 恒为 'e0', 不带身份则同 k 的 prompt 全撞
        return (f"[任务 {s['task_id']}] 从条目 '{s['entries'][0]}' 出发，"
                f"沿隐藏的指针关系走 {k} 跳，"
                f"请直接给出到达条目的关键值（只输出该值）。")

    def ground_truth_at(self, s, k):
        return s["truth_chain"][k]

    def random_baseline(self, s, k, pool=None):
        """同 k 下多真值的盲猜命中率 = 1/(互异真值个数) (KI-001 C 的推导式基线)。

        盲猜者看得到族与步数 k, 但**看不到 schedules**, 因此不知道各真值的
        出现频率, 只能在该 k 上出现过的 d 个候选值里均匀取一个 → 命中率 1/d。
        旧基线 1/len(entries) (0.111–0.2) 使阈值上限到 0.5, 25% 的泄漏者被放行。

        为什么不是"众数频率": 众数要求盲猜者**知道频率**, 那是知情猜测而非
        盲猜; 且实测该估计量被小样本显著抬高 (30 个任务下 0.077–0.136),
        500 个随机种子里有 198 个会让 25% 泄漏者过关, 与 KI-001 的验收判据
        冲突, 故不采用。
        """
        if not pool:
            return 1.0 / len(s["entries"])
        distinct = set()
        for t in pool:
            chain = t.get("truth_chain") or []
            if k < len(chain):
                distinct.add(_norm(chain[k]))
        if not distinct:
            return 1.0 / len(s["entries"])
        return 1.0 / len(distinct)

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
        pool_scheds = [schedules[t] for t in pool]
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
            baseline_sum += probe.random_baseline(s, k, pool_scheds)
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

    要求 prompt→真值 是**函数**。三个族的 make_probe_prompt 都带上公开的
    task_id, 因此 (族, 任务, k) 唯一决定 prompt —— 真实 schedules 上不再碰撞。
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


def _selftest(real_schedules=None):
    """门禁非空性反证 (AGENTS.md 第 8 条): 证明 leak_check 能真失败。

    五条反证, 每条都断言 GATE 结果; 任一不符 → selftest 自身 FAIL (exit 1)。
      all_calls_fail    模型接口不可用     → 必须 FAIL (fail-closed)
      oracle_leak       完美泄漏 (给真值)  → 必须 FAIL (LEAK)
      garbage_answer    与真值无关的回答   → 必须 PASS (否则门是装饰, 永远拦)
      half_calls_fail   半数调用失败       → 必须 PASS, 且失败数须被报出
      quarter_leak      25% 命中率的泄漏者 → 必须 FAIL (KI-001 的原始症状)

    全部五例都跑在**真实 schedules** 上 —— 修掉 prompt 碰撞后 (KI-001 C),
    ret-path 不再需要合成输入, 门禁在真实分布上的灵敏度由此被直接证明。
    """
    if real_schedules is None:
        import pickle
        with open("etl/data/schedules/schedules.pkl", "rb") as f:
            real_schedules = pickle.load(f)

    def all_fail(prompt):
        raise RuntimeError("接口不可用")

    tmap = _truth_map(real_schedules)

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

    counter25 = {"n": 0}

    def quarter_leak(prompt):
        # 每 4 次答对 1 次 → 命中率 25%。KI-001 的原症状就是这个泄漏者
        # 曾能被判 CLEAN (旧基线 1/len(entries) 使阈值上限到 0.5)。
        counter25["n"] += 1
        if counter25["n"] % 4 == 0:
            return tmap[prompt]
        return "__NO_ANSWER__"

    cases = [
        ("all_calls_fail", real_schedules, all_fail, False),
        ("oracle_leak", real_schedules, oracle, False),
        ("garbage_answer", real_schedules, garbage, True),
        ("half_calls_fail", real_schedules, half_fail, True),
        ("quarter_leak", real_schedules, quarter_leak, False),
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