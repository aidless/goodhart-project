"""最小冒烟测试。将来敢拆 leak_check.py 的前提。

命名 test_*, 用 python3 -m pytest tests/ 跑。
不假设任何未见的文件内容: 全部测试对「文件是否存在」先做 skip 判断,
所以这个文件在任何阶段的仓库里都不会误报失败。
"""
import ast
import hashlib
import json
import pathlib
import pickle
import subprocess
import sys
import tempfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

def test_all_src_files_parse():
    """src/ 全部 .py 必须能被 ast 解析 —— 语法级回归网。"""
    files = sorted(SRC.glob("*.py"))
    assert files, "src/ 下没有任何 .py"
    for p in files:
        ast.parse(p.read_text(encoding="utf-8"))

def test_plot_style_importable():
    """_plot_style 存在则可导入, 且 CJK 探测属性存在。"""
    if not (SRC / "_plot_style.py").exists():
        pytest.skip("_plot_style.py 不存在")
    sys.path.insert(0, str(SRC))
    import _plot_style
    assert hasattr(_plot_style, "_cjk_found")

def test_gen_tasks_is_deterministic():
    """同种子跑两次 gen_tasks.py, tasks.jsonl 的 sha256 必须一致。"""
    script = SRC / "gen_tasks.py"
    tasks = ROOT / "etl" / "data" / "tasks" / "tasks.jsonl"
    if not script.exists() or not tasks.exists():
        pytest.skip("gen_tasks.py 或 tasks.jsonl 不存在")

    import hashlib

    def digest():
        return hashlib.sha256(tasks.read_bytes()).hexdigest()

    before = tasks.read_bytes()
    try:
        subprocess.run([sys.executable, str(script)], cwd=ROOT,
                       check=True, capture_output=True)
        after_digest = digest()
        before_digest = hashlib.sha256(before).hexdigest()
    finally:
        # 无论成败都还原, 不让测试污染工作区
        tasks.write_bytes(before)

    assert before_digest == after_digest, "gen_tasks.py 非确定性输出"

def test_leak_check_selftest_passes():
    """门禁自检必须通过。leak_check.py 不存在则跳过。"""
    script = SRC / "leak_check.py"
    if not script.exists():
        pytest.skip("leak_check.py 不存在")
    r = subprocess.run([sys.executable, str(script), "--selftest"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, f"--selftest 失败:\n{r.stdout}\n{r.stderr}"

def test_chain_sort_baseline_derives_from_rule_domain():
    """chain-sort 盲猜基线 == 1/(规则域内可推导候选数), 且候选 ≤ |规则域|。

    这是 2026-10-08 判据修正的回归网。旧基线 1/(len(init_seq)+1) 无推导依据,
    且低于真实盲猜率 (0.5), 把诚实枚举者误判为 LEAK。见 docs/known_issues.md。
    """
    sched = ROOT / "etl" / "data" / "schedules" / "schedules.pkl"
    if not sched.exists() or not (SRC / "leak_check.py").exists():
        pytest.skip("schedules.pkl 或 leak_check.py 不存在")
    sys.path.insert(0, str(SRC))
    import gen_tasks
    import leak_check

    schedules = pickle.loads(sched.read_bytes())
    probe = leak_check.ChainSortProbe()
    seen = 0
    for s in schedules.values():
        if s["family"] != "chain-sort":
            continue
        for k in range(1, s["n_steps"]):
            outs = set()
            for rule in gen_tasks.SORT_RULES:
                seq = list(s["init_seq"])
                for _ in range(k + 1):        # truth_chain[k] = k+1 次变换
                    seq = gen_tasks.apply_chain_sort(seq, 0, rule)
                outs.add(tuple(seq))
            assert len(outs) <= len(gen_tasks.SORT_RULES), "候选数不能超过规则域"
            assert probe.random_baseline(s, k, [s]) == pytest.approx(1.0 / len(outs))
            seen += 1
    assert seen > 0, "没找到 chain-sort 样本, 判据未真正被验证"

def test_truth_chain_not_in_public_tasks_but_rules_are():
    """公开 tasks.jsonl 不得含真值链; 但规则字段必须随任务公开 (v2 设计)。

    2026-10-12 KI-002 定案反转了旧契约: 旧版把 ops/sort_rule/ptr/values
    也藏进 schedules, 迷你实验证实三族真值不可推导 → 地板是设计属性
    (qc/b_line_solvability/results.json)。新版规则公开、truth_chain 仍绝不
    公开 —— 规则 ≠ 答案键, 公开规则后仍须逐步执行才能得到真值。
    """
    tasks = ROOT / "etl" / "data" / "tasks" / "tasks.jsonl"
    if not tasks.exists():
        pytest.skip("tasks.jsonl 不存在")
    rules_needed = {"stateful-calc": ("ops",),
                    "chain-sort": ("sort_rule",),
                    "ret-path": ("ptr", "values")}
    seen_fams = set()
    for line in tasks.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        assert "truth_chain" not in d, \
            f"{d.get('task_id')} 泄露真值链 truth_chain"
        fam = d.get("family")
        seen_fams.add(fam)
        for field in rules_needed.get(fam, ()):
            assert field in d, \
                f"{d.get('task_id')} 缺少应公开的规则字段 {field!r} (v2 设计)"
    assert seen_fams == set(rules_needed), f"任务族不全: {seen_fams}"

def test_gate_chain_smoke_passes():
    """门禁链第 3–5 步的基础设施冒烟测试必须通过 (确定性 stub, 非模型测量)。"""
    script = SRC / "smoke_gate_chain.py"
    if not script.exists() or not (ROOT / "etl" / "data" / "schedules" / "schedules.pkl").exists():
        pytest.skip("smoke_gate_chain.py 或 schedules.pkl 不存在")
    r = subprocess.run([sys.executable, str(script)], cwd=ROOT,
                       capture_output=True, text=True)
    assert r.returncode == 0, f"门禁链冒烟失败:\n{r.stdout}\n{r.stderr}"

def test_gate_fails_closed_when_schedules_missing():
    """盘上没有真值表时, 门禁必须拒绝放行, 绝不现生成一份顶替 (fail-open 漏洞)。

    在空目录里跑 leak_check.py: `etl/data/schedules/schedules.pkl` 不存在,
    期望非零退出且报出「找不到」, 而不是静默用合成数据验门。
    """
    script = SRC / "leak_check.py"
    if not script.exists():
        pytest.skip("leak_check.py 不存在")
    with tempfile.TemporaryDirectory() as td:
        r = subprocess.run([sys.executable, str(script)], cwd=td,
                           capture_output=True, text=True)
    assert r.returncode != 0, f"缺真值表时门禁竟然放行 (fail-open!):\n{r.stdout}"
    assert "找不到" in (r.stdout + r.stderr), r.stdout + r.stderr

