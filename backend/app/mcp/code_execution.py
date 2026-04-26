import ast
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from app.core.config import settings


BLOCKED_IMPORTS = {"os", "subprocess", "socket", "pathlib", "shutil", "requests"}


def _validate_source(source: str) -> None:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name.split(".")[0] for alias in node.names]
            if any(name in BLOCKED_IMPORTS for name in names):
                raise ValueError("Submitted code imports a blocked module.")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in {"eval", "exec", "open", "compile", "__import__"}:
                raise ValueError("Submitted code uses a blocked function.")


def run_python_solution(code: str, test_cases: list[dict[str, Any]]) -> dict[str, Any]:
    _validate_source(code)
    harness = """
import json
import os
import solution

tests = json.loads(os.environ["TEST_CASES"])
results = []
for case in tests:
    value = json.loads(case["input"])
    expected = json.loads(case["expected"])
    if isinstance(value, list):
        actual = solution.solve(*value)
    else:
        actual = solution.solve(value)
    results.append({"passed": actual == expected, "actual": actual, "expected": expected})
print(json.dumps(results))
"""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "solution.py").write_text(code, encoding="utf-8")
        env = os.environ.copy()
        env["TEST_CASES"] = json.dumps(test_cases)
        proc = subprocess.run(
            [sys.executable, "-c", harness],
            cwd=root,
            env=env,
            text=True,
            capture_output=True,
            timeout=settings.code_timeout_seconds,
        )
    if proc.returncode != 0:
        return {"passed": False, "score": 0.0, "feedback": proc.stderr[-1000:], "cases": []}
    cases = json.loads(proc.stdout)
    passed = sum(1 for case in cases if case["passed"])
    total = max(len(cases), 1)
    return {
        "passed": passed == total,
        "score": passed / total,
        "feedback": f"{passed}/{total} test cases passed.",
        "cases": cases,
    }
