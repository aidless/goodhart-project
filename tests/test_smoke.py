"""最小冒烟测试。将来敢拆 leak_check.py 的前提。

命名 test_*, 用 python3 -m pytest tests/ 跑。
不假设任何未见的文件内容: 全部测试对「文件是否存在」先做 skip 判断,
所以这个文件在任何阶段的仓库里都不会误报失败。
"""
import ast
import pathlib
import subprocess
import sys

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
