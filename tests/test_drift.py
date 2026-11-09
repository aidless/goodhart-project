"""README / 账本 / 已提交结果的漂移测试。"""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_drift_check_matches_committed_files():
    r = subprocess.run(
        [sys.executable, str(ROOT / "src" / "drift_check.py")],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stdout + "\n" + r.stderr
