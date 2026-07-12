"""The ORACLE for the self-healing loop.

Runs a task's tests against a candidate code directory in an isolated subprocess
and reports pass/fail plus captured output. Isolation matters: the loop mutates
code every iteration, and a crashing candidate must not take the loop down with it.
"""
from __future__ import annotations

import glob
import os
import subprocess
import sys
from dataclasses import dataclass


@dataclass
class TestResult:
    passed: bool
    output: str  # combined stdout+stderr the patcher gets to read back


def run_tests(code_dir: str, test_dir: str, timeout: int = 15) -> TestResult:
    """Run every test_*.py in test_dir with code_dir importable. Exit 0 == pass."""
    test_files = sorted(glob.glob(os.path.join(test_dir, "test_*.py")))
    if not test_files:
        return TestResult(False, f"no test_*.py found in {test_dir}")

    # Make both the candidate code and the tests importable.
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([code_dir, test_dir, env.get("PYTHONPATH", "")])

    chunks = []
    for tf in test_files:
        try:
            proc = subprocess.run(
                [sys.executable, tf],
                cwd=code_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return TestResult(False, f"{os.path.basename(tf)}: TIMEOUT after {timeout}s")
        chunks.append(
            f"$ python {os.path.basename(tf)}\n"
            f"[exit {proc.returncode}]\n{proc.stdout}{proc.stderr}"
        )
        if proc.returncode != 0:
            return TestResult(False, "\n".join(chunks))
    return TestResult(True, "\n".join(chunks))
