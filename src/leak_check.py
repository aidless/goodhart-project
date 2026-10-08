"""leak_check.py v2 — 三任务族统一泄漏探测。
判定: 每族命中率 > max(0.02, 2.5 × 随机基线) → LEAK, 禁止进入 run_etl。"""
import abc
import random

from gen_tasks import SORT_RULES, apply_chain_sort

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
        """盲猜命中率 = 1/(公开信息下可推导的候选数)。

        prompt 给了 init_seq 与步数 k, **隐藏的只有规则域 SORT_RULES**,
        而 apply_chain_sort 是确定性变换 —— 盲猜者把规则域枚举一遍即可得到
        全部候选序列, 再均匀取一个。多数任务两个 rule 给出不同序列 → 恰好
        2 个候选 → 命中率 0.5。

        旧基线 1/(len(init_seq)+1) (0.14–0.25) 既无推导依据 (候选是**规则**
        不是位置, 与序列长度无关), 又**低于**真实盲猜率: 阈值 2.5×0.2≈0.50
        会把一个诚实枚举的盲猜者 (0.5) 判成 LEAK (假阳性)。改用可推导候选数
        后基线 0.5 → 阈值 1.25, 该族对任何泄漏都不再误报。

        ⚠️ 该阈值的完整推论: 1.25 高于命中率理论最大值 1.0, 故本族**任何
        命中率 (含 100% 完美泄漏) 都不会触发 LEAK** (selftest oracle 例实测
        「100.0% vs 阈值125.0% → CLEAN」)。本族的门禁职能只剩"零假阳性"的
        结构诚实性, 泄漏检测由 stateful-calc 与 ret-path 两族承担 —— 这是
        「隐藏规则只有二值」带来的设计局限, 不是调阈值能修的。

        与 RetPathProbe 的 1/d 不同: 那里隐藏的 ptr 是随机排列, 盲猜者无法
        枚举, d 是全池互异真值数 (≈30); 这里隐藏的是二值规则, d 必须按
        **规则域大小**算, 才是同一个 prompt 下真实的选择数。两者是同一个
        原则 (可推导候选数的倒数), 只是候选集的来源不同。
        """
        outs = set()
        for rule in SORT_RULES:
            seq = list(s["init_seq"])
            for i in range(k + 1):        # truth_chain[k] = 施加 k+1 次变换
                seq = apply_chain_sort(seq, i, rule)
            outs.add(tuple(seq))
        return 1.0 / len(outs)

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

# 门禁必须验这一份真值表 (run_etl 用的也是它)。缺失即 fail-closed, 见
# _require_schedules —— 绝不现生成一份顶替, 否则门在验 A、跑批用 B。
SCHEDULES_PATH = "etl/data/schedules/schedules.pkl"

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
            # 真实 model_call 按约定失败重试1次后返回 "__UNTESTED__" 不抛异常;
            # 这里必须计为 failed (不计入 total), 否则全失败会被误判 CLEAN
            # (fail-open)。全失败时 total==0 → UNTESTED → GATE FAIL。
            if got == "__UNTESTED__":
                failed += 1
                if failed == 1:
                    print(f"[{probe.name}] 调用失败样例: "
                          f"RuntimeError: ollama 两次失败 → __UNTESTED__")
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

    全部五例都跑在**同一份 schedules** 上 —— 修掉 prompt 碰撞后 (KI-001 C),
    ret-path 不再需要合成输入, 门禁在真实分布上的灵敏度由此被直接证明。
    该份数据默认是真实 schedules; 仅当盘上还没有真值表时, 调用方
    `_selftest_schedules` 才会退化为合成表并明确报告。
    """
    if real_schedules is None:
        real_schedules = _require_schedules()

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


def _require_schedules(path=SCHEDULES_PATH):
    """读 schedules.pkl。**缺失即 fail-closed**, 绝不现生成一份来顶替。

    门禁必须验「run_etl 将要使用的那一份」真值表。若这里在缺失时现生成,
    门禁验的就是另一份数据 —— 那是静默的 fail-open (门在验 A, 跑批用 B)。
    """
    import os
    import pickle
    if not os.path.exists(path):
        print(f"错误: 找不到 {path} —— 门禁无法验证真实 schedules。\n"
              "  请先跑 `python3 src/gen_tasks.py` 生成, 再跑门禁\n"
              "  (run_all.sh 已按此顺序: 第 1 步生成, 第 2 步门禁)。\n"
              "  门禁拒绝在缺少真值表时放行 (fail-closed)。")
        raise SystemExit(2)
    with open(path, "rb") as f:
        return pickle.load(f)


def _generate_schedules_for_selftest(n_per_family=30, seed=0):
    """仅为 --selftest 造一份**合成** schedules。

    ⚠️ 这份数据不是 run_etl 会用的那份, 门禁正式跑批时绝不使用它。
    这里生成它只是为了在「盘上还没有真值表」时也能自检门禁逻辑本身。
    """
    print("[selftest] 未找到真实 schedules.pkl — 改用合成数据自检门禁逻辑")
    import gen_tasks
    rng = random.Random(seed)
    sched = {}
    makers = [gen_tasks.make_stateful_calc, gen_tasks.make_chain_sort,
              gen_tasks.make_ret_path]
    for fam_i, maker in enumerate(makers):
        for i in range(n_per_family):
            s = maker(rng)
            s["task_id"] = f"{s['family']}-{fam_i}-{i:03d}"
            s["truth_chain"] = gen_tasks._truth_chain(s)
            sched[s["task_id"]] = s
    return sched


def _selftest_schedules(path=SCHEDULES_PATH):
    """--selftest 专用入口: 有真实表就用真实的, 没有才退化为合成表。"""
    import os
    if os.path.exists(path):
        return _require_schedules(path)
    return _generate_schedules_for_selftest()


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    if "--selftest" in sys.argv:
        raise SystemExit(0 if _selftest(_selftest_schedules()) else 1)

    # 正式跑门禁: 必须用真实 schedules; 缺失则 fail-closed 退出 (码 2)。
    schedules = _require_schedules()

    # 真实模型接口: 本地 ollama (urllib 标准库, timeout 60s, max_tokens 50,
    # 失败重试1次后返回 __UNTESTED__ 不抛异常; fail-closed 由 run_leak_check
    # 把 __UNTESTED__ 计 failed 来保持, 见上)。
    import os as _os
    from ollama_model import model_call as _real_model_call, OLLAMA_MODEL, OLLAMA_URL
    _n = 20
    if "--n-per-family" in sys.argv:
        _i = sys.argv.index("--n-per-family")
        try:
            _n = int(sys.argv[_i + 1])
        except (IndexError, ValueError):
            print("用法: leak_check.py [--n-per-family N]"); raise SystemExit(2)
    elif _os.environ.get("LEAK_N_PER_FAMILY"):
        try:
            _n = int(_os.environ["LEAK_N_PER_FAMILY"])
        except ValueError:
            print("LEAK_N_PER_FAMILY 必须为整数"); raise SystemExit(2)
    print(f"[gate] model={OLLAMA_MODEL} url={OLLAMA_URL} n_per_family={_n} "
          f"(如为 5 即降采样, 如实记录, 不虚报 20/20)")

    ok = run_leak_check(schedules, _real_model_call, n_per_family=_n)
    raise SystemExit(0 if ok else 1)
