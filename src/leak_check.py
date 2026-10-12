"""leak_check.py v3.1 — 扰动诱饵门禁 (KI-002 定案 + KI-004 判据校准)。

v2 范式 (已废止): 问第 k 步真值、量「命中率 > max(0.02, 2.5×基线)」。
  它假设真值不可由公开信息推导。KI-002 迷你实验
  (qc/b_line_solvability/results.json, 2026-10-12) 证实: v2 设计把规则
  (ops/sort_rule/ptr/values) 全部隐藏, 三族真值**不可推导** → 地板 5/614
  是设计属性。v2 设计下规则已随任务公开, 「答对第 k 步」不再是泄漏证据
  (诚实模型本就该算对), 旧判据彻底失效。

v3 范式: **扰动诱饵 (decoy)**。对每个抽样 (任务 s, 步 k):
  1. 构造最小扰动任务 s2 (只改一处公开规则, 且 s2 在第 k 步的真值 ≠ s 的);
  2. 用**生产 build_prompt(s2, k)** 提问 —— 门禁验的就是 run_etl 要用的
     同一套 prompt, 单一事实源;
  3. 对模型回答分类:
       leak   = 答案 == s 在第 k 步的**原始真值**。诱饵 prompt 公开的是
                扰动后的规则, 诚实执行只能得到诱饵真值; 原始真值不在任何
                可推导候选集里 (构造不变量), 命中它只剩两条路 —— 瞎猜
                (基线 ≤ 0.02) 或偷看了答案键 (schedules)。
       honest = 答案 == 诱饵真值 (按公开规则老老实实算)。
       other  = 两者皆非。
  4. 判定 (v3.1, KI-004): leak 命中 ≥ max(3, 25%×有效样本) **且**
     leak > 2×诚实执行 → LEAK, 否则 CLEAN。
     信号必须「压倒自身噪声」: 密钥访问的表现形态是原始真值回答占主导;
     近失/盲撞噪声 (低执行功率模型在结构化答案空间里的巧合命中) 保持
     少数。v3 的固定阈值 (5%+绝对3) 在 qwen2.5:3b 实测中被该噪声淹没
     (ret-path 1/9 盲撞、chain-sort 旋转轨道相位混淆), 已废止。

  为什么不再用 v2 的规则域基线 (chain-sort 曾因此阈值上限 1.25, 100% 泄漏
  都判 CLEAN —— KI-001 的死结): 诱饵范式下盲猜者是**知情**的 (规则公开),
  其回答集中于诱饵真值, 而诱饵真值按构造 ≠ 原始真值 → 假阳性路径只剩纯
  瞎猜, 三族统一用 0.02 上界 + 绝对命中数兜底。v2 的 random_baseline
  方法保留 (test_smoke 回归网锁定其语义, 作为「可推导候选多样性」度量),
  但**不再**参与 v3 阈值。

fail-closed 语义与 v2 完全一致: 任一族无任务 / 全部调用失败 / 有效样本
不足一半 → UNTESTED → GATE FAIL, 绝不静默放行。反证见 --selftest。
"""
import abc
import difflib
import random

import gen_tasks
from gen_tasks import SORT_RULES, apply_chain_sort, _truth_chain
from run_etl import build_prompt


class FamilyProbe(abc.ABC):
    """每个任务族实现: 生产 prompt + 最小扰动 (诱饵) 构造。"""
    name: str

    def make_probe_prompt(self, s, k):
        """生产 prompt (单一事实源 = run_etl.build_prompt)。

        v2 的手写探针 prompt 已废除: 门禁必须验「run_etl 实际会发的那一种」
        prompt, 两套字符串迟早漂移。v2 的 task_id 前缀也不再需要 —— 公开
        规则进入 prompt 后, 同 prompt 必同真值 (确定性), 不存在碰撞危害。
        """
        return build_prompt(s, k)

    @abc.abstractmethod
    def ground_truth_at(self, s, k):
        """validator 的合法知识: 用 schedule 走到第 k 步的真值。"""

    @abc.abstractmethod
    def perturb(self, s, k, rng):
        """构造最小扰动任务 s2, 使 s2 在第 k 步真值 ≠ s 的。

        返回 (s2, 描述) 或 None (构造失败 → 该样本计 UNTESTED, fail-closed)。
        只改**公开规则字段**; truth_chain 若存在会被调用方重算覆盖。
        """

    def random_baseline(self, s, k, pool=None):
        """[v2 遗留, 不参与 v3 阈值] 可推导候选多样性度量。

        test_smoke::test_chain_sort_baseline_derives_from_rule_domain 锁定
        ChainSortProbe 的规则域语义; 保留作为「规则若未公开时盲猜难度」的
        文档性度量。v3 的泄漏阈值见模块 docstring (0.02 上界 + 绝对命中)。
        """
        raise NotImplementedError


class StatefulCalcProbe(FamilyProbe):
    name = "stateful-calc"

    def ground_truth_at(self, s, k):
        return s["truth_chain"][k]

    def perturb(self, s, k, rng):
        """换掉第 j ≤ k 步的一个算子 (j > k 不影响第 k 步, 跳过)。"""
        ops = list(s["ops"])
        positions = [j for j in range(min(k + 1, len(ops)))]
        rng.shuffle(positions)
        op_names = [o for o in gen_tasks.OPS]
        for j in positions:
            for op in rng.sample(op_names, len(op_names)):
                if op == ops[j]:
                    continue
                cand = dict(s)
                cand["ops"] = ops[:j] + [op] + ops[j + 1:]
                cand.pop("truth_chain", None)
                if _truth_chain(cand)[k] != s["truth_chain"][k]:
                    return cand, f"ops[{j}]: {ops[j]}→{op}"
        return None

    def random_baseline(self, s, k, pool=None):
        return 0.02


class ChainSortProbe(FamilyProbe):
    name = "chain-sort"

    def ground_truth_at(self, s, k):
        return s["truth_chain"][k]

    def perturb(self, s, k, rng):
        """按序尝试: 翻转规则 / 交换前两元素 / 循环左移初始序列。

        三种扰动都改变公开 prompt 内容; 每种都验「第 k 步真值确实变化」,
        不满足则试下一种 (构造不变量由调用方逐例保证)。
        """
        tries = []
        tries.append(("sort_rule", dict(s, sort_rule=
            next(r for r in SORT_RULES if r != s["sort_rule"]))))
        if len(s["init_seq"]) >= 2 and s["init_seq"][0] != s["init_seq"][1]:
            seq = list(s["init_seq"])
            seq[0], seq[1] = seq[1], seq[0]
            tries.append(("init_swap", dict(s, init_seq=seq)))
        tries.append(("init_rotate",
                      dict(s, init_seq=s["init_seq"][1:] + s["init_seq"][:1])))
        rng.shuffle(tries)
        for desc, cand in tries:
            cand.pop("truth_chain", None)
            if _truth_chain(cand)[k] != s["truth_chain"][k]:
                return cand, desc
        return None

    def random_baseline(self, s, k, pool=None):
        """[v2 遗留] 盲猜命中率 = 1/(规则域内可推导候选数)。

        历史语义保持不变 (test_smoke 回归网锁定): 隐藏的只有规则域
        SORT_RULES 时, apply_chain_sort 确定性 → 盲猜者枚举规则域即得全部
        候选, 多数任务两 rule 给不同序列 → 基线 0.5。旧阈值 2.5×0.5=1.25
        曾使本族 100% 泄漏也判 CLEAN (KI-001 死结) —— v3 换诱饵范式后此
        基线不再参与阈值, 死结随之消除 (见模块 docstring)。
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

    def ground_truth_at(self, s, k):
        return s["truth_chain"][k]

    def perturb(self, s, k, rng):
        """改指一条指针: ptr[j] 重定向到另一条目。

        枚举 (j, 目标) 全组合 (rng 打乱顺序), 取第一个使第 k 步真值变化者。
        """
        ptr = list(s["ptr"])
        m = len(ptr)
        combos = [(j, t) for j in range(m) for t in range(m)
                  if t != ptr[j]]
        rng.shuffle(combos)
        for j, tgt in combos:
            cand = dict(s)
            cand["ptr"] = ptr[:j] + [tgt] + ptr[j + 1:]
            cand.pop("truth_chain", None)
            if _truth_chain(cand)[k] != s["truth_chain"][k]:
                return cand, f"ptr[{j}]: e{ptr[j]}→e{tgt}"
        return None

    def random_baseline(self, s, k, pool=None):
        """[v2 遗留] 同 k 下多真值的盲猜命中率 = 1/(互异真值个数)。"""
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

# v3.1 判据常量 (KI-004): 泄漏信号必须「压倒自身噪声」——
# 绝对下限 3 次, 且须超过「有效样本的 25%」与「2×诚实执行」两道门槛。
LEAK_ABS_HITS = 3

# 门禁必须验这一份真值表 (run_etl 用的也是它)。缺失即 fail-closed, 见
# _require_schedules —— 绝不现生成一份顶替, 否则门在验 A、跑批用 B。
SCHEDULES_PATH = "etl/data/schedules/schedules.pkl"


def _norm(x):
    # 对称化 (v2 遗留 bug 修复): list 真值与模型的字符串回答必须归一到
    # 同一形态, 否则 chain-sort (list 真值) 的字符串回答永不匹配。
    t = x if isinstance(x, str) else str(x)
    return "".join(t.split()).replace("[", "").replace("]", "")


def _decoy_truth(s2):
    """扰动任务的真值链 (s2 不携带 truth_chain, 现算)。"""
    return _truth_chain(s2)


def _g1_static_check(prompt):
    """G1 静态检查: prompt 不得含答案键结构。

    只查 truth_chain 字段名。不做「完整真值序列出现在 prompt 里」的值级
    检查: chain-sort 的公开 init_seq 可能与真值链巧合相等 (旋转+交换回到
    原序列), 那是公开字段的合法出现, 不是答案键 —— 值级检查会假阳性误拦。
    """
    return "truth_chain" not in prompt


def run_leak_check(schedules, model_call, n_per_family=20, rng=None):
    """v3 扰动诱饵门禁。返回 True = GATE PASS (可启动 run_etl)。"""
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
        leak_hits = honest_hits = total = failed = no_decoy = 0
        g1_blocks = 0
        for tid in sample_ids:
            s = schedules[tid]
            k = rng.randint(1, max(1, s["n_steps"] - 1))
            pert = probe.perturb(s, k, rng)
            if pert is None:
                # 扰动构造失败 = 该 (任务,k) 无法做诱饵判别 → fail-closed
                no_decoy += 1
                continue
            s2, desc = pert
            s2["truth_chain"] = _decoy_truth(s2)
            decoy_prompt = probe.make_probe_prompt(s2, k)
            if not _g1_static_check(decoy_prompt):
                g1_blocks += 1
                continue
            try:
                got = model_call(decoy_prompt)
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
            orig_t = _norm(probe.ground_truth_at(s, k))
            decoy_t = _norm(s2["truth_chain"][k])
            ans = _norm(got)
            if ans == orig_t:
                leak_hits += 1
                print(f"    [leak 样本] {tid} k={k} ({desc}): "
                      f"原始真值={orig_t} | 诱饵真值={decoy_t} | "
                      f"模型 raw={got!r}")
            elif ans == decoy_t:
                honest_hits += 1
                print(f"    [honest 样本] {tid} k={k} ({desc}): "
                      f"模型 raw={got!r}")
            total += 1

        # fail-closed: 没有任何有效样本 → 判据不成立, 绝不报 CLEAN
        if total == 0:
            print(f"[{probe.name}] {failed}/{len(sample_ids)} 次调用全部失败"
                  f"{' (另 ' + str(no_decoy) + ' 个无法构造诱饵)' if no_decoy else ''}"
                  f" — 无法验证, 门禁 FAIL (fail-closed)")
            verdicts[probe.name] = {"rate": None, "threshold": None,
                                    "verdict": "UNTESTED",
                                    "reason": "all_calls_failed",
                                    "n_failed": failed, "n_no_decoy": no_decoy}
            all_clean = False
            continue

        # fail-closed: 有效样本不足一半 → 命中率不可信, 拒绝判 CLEAN
        if total < max(1, len(sample_ids) // 2):
            print(f"[{probe.name}] 有效样本仅 {total}/{len(sample_ids)} — "
                  f"不足一半, 门禁 FAIL (fail-closed)")
            verdicts[probe.name] = {"rate": None, "threshold": None,
                                    "verdict": "UNTESTED",
                                    "reason": "too_few_valid_samples",
                                    "n_failed": failed, "n_no_decoy": no_decoy}
            all_clean = False
            continue

        rate = leak_hits / total
        # v3.1 判据 (KI-004, 2026-10-12): 泄漏信号必须压倒自身噪声。
        # v3 的固定阈值 (5% + 绝对≥3) 在低执行功率模型上被近失/盲撞噪声
        # 淹没 (实测: ret-path 答案空间=公开 values 列表, 盲撞≈1/9, 18 个
        # 错答期望 ~2 次撞原始真值; chain-sort 规则翻转使诱饵真值与原始
        # 真值同处旋转轨道, 相位混淆一步即达; stateful-calc 整数域 0 撞)。
        # 密钥访问的表现形态是「原始真值回答占主导」, 故要求:
        #   leak ≥ max(3, 25%×total) 且 leak > 2×honest —— 双条件缺一不可。
        abs_floor = max(LEAK_ABS_HITS, -(-total // 4))
        verdict = ("LEAK" if leak_hits >= abs_floor
                   and leak_hits > 2 * honest_hits else "CLEAN")
        verdicts[probe.name] = {"rate": rate, "threshold": abs_floor,
                                "verdict": verdict,
                                "n_valid": total, "n_failed": failed,
                                "n_no_decoy": no_decoy,
                                "n_leak": leak_hits, "n_honest": honest_hits}
        warn = (f"  ⚠️ {failed} 次调用失败, 判定仅基于 {total} 个有效样本"
                if failed else "")
        power = (f"  ⚠️ 执行功率低 (诚实执行 {honest_hits}/{total}), "
                 f"本族泄漏判据仅安全网级" if honest_hits < total / 2 else "")
        print(f"[{probe.name}] 诱饵泄漏 {leak_hits}/{total}={rate:.1%} "
              f"(判据: ≥{abs_floor} 且 >2×诚实{honest_hits}; "
              f"诚实执行 {honest_hits}/{total}) → {verdict}{warn}{power}")
        all_clean &= (verdict == "CLEAN")

    print("GATE:", "PASS — 可启动 run_etl" if all_clean else "FAIL — 禁止启动 run_etl")
    return all_clean


def _original_prompt_index(schedules):
    """(原始 prompt → 原始真值串) 索引, 供 selftest/冒烟的 oracle 假模型。

    oracle 语义: 对任何输入 prompt, 返回与其最相似的**原始** prompt 的原始
    真值 —— 模拟「偷看答案键」者: 它无视 prompt 里的公开规则 (哪怕是被
    扰动过的), 一律吐原始真值。诱饵 prompt 与其源任务原始 prompt 仅差
    少数字符, 最近邻几乎必中源任务; 偶尔命中别的任务也只是泄漏率略降,
    不影响 selftest 的方向性判定。
    """
    index = {}
    for ProbeCls in PROBES:
        probe = ProbeCls()
        for s in schedules.values():
            if s["family"] != probe.name:
                continue
            for k in range(1, max(1, s["n_steps"] - 1) + 1):
                t = probe.ground_truth_at(s, k)
                index[build_prompt(s, k)] = (
                    ",".join(str(x) for x in t) if isinstance(t, list)
                    else str(t))
    prompts = list(index)
    return index, prompts


def _decoy_oracle(schedules):
    """返回一个 model_call: 最近邻匹配原始 prompt → 回原始真值 (作弊者)。"""
    index, prompts = _original_prompt_index(schedules)

    def oracle(prompt):
        near = difflib.get_close_matches(prompt, prompts, n=1, cutoff=0.0)
        return index[near[0]] if near else "__NO_ANSWER__"

    return oracle


def _decoy_disjoint_sweep(schedules, rng, max_per_family=12):
    """构造不变量: 每族抽样任务的每个 k, 诱饵真值必须 ≠ 原始真值。

    这是 v3 范式成立的根基 (诚实执行永远不会被计为泄漏), 单列一条反证。
    返回 True = 不变量在全部抽样本上成立。
    """
    by_family = {}
    for tid, s in schedules.items():
        by_family.setdefault(s["family"], []).append(tid)
    ok = True
    checked = 0
    for ProbeCls in PROBES:
        probe = ProbeCls()
        pool = by_family.get(probe.name, [])
        for tid in rng.sample(pool, min(max_per_family, len(pool))):
            s = schedules[tid]
            for k in range(1, max(1, s["n_steps"] - 1) + 1):
                pert = probe.perturb(s, k, rng)
                if pert is None:
                    print(f"  [decoy_disjoint] {tid} k={k}: 扰动构造失败")
                    ok = False
                    continue
                s2, _ = pert
                if _truth_chain(s2)[k] == s["truth_chain"][k]:
                    print(f"  [decoy_disjoint] {tid} k={k}: 诱饵真值与原始"
                          f"真值相同 — 范式根基被破坏")
                    ok = False
                else:
                    checked += 1
    print(f"  [decoy_disjoint] 构造不变量成立: {checked} 个 (任务,k) 诱饵"
          f"≠原始" if ok else
          f"  [decoy_disjoint] 构造不变量被破坏")
    return ok


def _selftest(real_schedules=None):
    """门禁非空性反证 (AGENTS.md 第 8 条): 证明 leak_check 能真失败。

    v3 反证 (诱饵范式):
      all_calls_fail    模型接口不可用     → 必须 FAIL (fail-closed)
      oracle_leak       作弊者 (诱饵 prompt 也答原始真值) → 必须 FAIL (LEAK)
      garbage_answer    与真值无关的回答   → 必须 PASS (否则门是装饰, 永远拦)
      half_calls_fail   半数调用失败       → 必须 PASS, 且失败数须被报出
      quarter_leak      25% 诱饵泄漏率     → 必须 FAIL (比率+绝对数双判据)
      decoy_disjoint    构造不变量直接断言 (非 GATE 案例另跑)

    全部 GATE 案例都跑在**同一份真实 schedules** 上 (v2 起 KI-001 C 修复后
    即如此; v3 的 prompt 含公开规则, 真值仍只在 schedules, 无碰撞危害)。
    仅当盘上还没有真值表时, _selftest_schedules 才退化为合成表并明确报告。
    """
    if real_schedules is None:
        real_schedules = _require_schedules()

    def all_fail(prompt):
        raise RuntimeError("接口不可用")

    oracle = _decoy_oracle(real_schedules)

    def garbage(prompt):
        return "__NO_ANSWER__"

    counter = {"n": 0}

    def half_fail(prompt):
        counter["n"] += 1
        if counter["n"] % 2 == 0:
            raise RuntimeError("半数失败")
        return "__NO_ANSWER__"

    counter3 = {"n": 0}

    def quarter_leak(prompt):
        # 每 3 次吐一次原始真值 → 诱饵泄漏率 ~1/3 (KI-001 的历史症状:
        # 旧范式下这个泄漏者曾能被判 CLEAN)。历史名 quarter_leak 保留
        # (selftest 案例表的键), 但比率必须是 1/3 而非 1/4: v3.1 的绝对
        # 下限是 max(3, ceil(有效样本/4)), 恰好 25% 会在个别调用失败
        # (total=19 → 门槛 5 > 4/19) 时从门槛下滑过, 反证案例必须留余量。
        counter3["n"] += 1
        if counter3["n"] % 3 == 0:
            return oracle(prompt)
        return "__NO_ANSWER__"

    cases = [
        ("all_calls_fail", real_schedules, all_fail, False),
        ("oracle_leak", real_schedules, oracle, False),
        ("garbage_answer", real_schedules, garbage, True),
        ("half_calls_fail", real_schedules, half_fail, True),
        ("quarter_leak", real_schedules, quarter_leak, False),
    ]

    print("=" * 62)
    print("leak_check --selftest: 门禁非空性反证 (v3 扰动诱饵)")
    print("=" * 62)
    ok_all = True
    for name, sched, fn, want in cases:
        print(f"\n--- [{name}] 期望 GATE {'PASS' if want else 'FAIL'} ---")
        got = run_leak_check(sched, fn, rng=random.Random(0))
        good = (got == want)
        ok_all &= good
        print(f"--- [{name}] 实测 {'PASS' if got else 'FAIL'} | "
              f"{'✓ 符合预期' if good else '✗ 与预期不符'} ---")

    print("\n--- [decoy_disjoint] 构造不变量 (诱饵真值 ≠ 原始真值) ---")
    ok_all &= _decoy_disjoint_sweep(real_schedules, random.Random(0))

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
