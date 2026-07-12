#!/usr/bin/env python3
"""Example 1 — drive the loop programmatically for a single task.

Shows the Python API: load a task, run the loop with a patcher, read the result.

    python examples/01_run_one_task.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from agent.loop import run_loop
from agent.patchers import GoldPatcher

TASK_DIR = os.path.join(HERE, "data", "tasks", "001_off_by_one")

with open(os.path.join(TASK_DIR, "meta.json")) as fh:
    task = json.load(fh)

# Swap GoldPatcher for ClaudePatcher() to run the real LLM loop.
patcher = GoldPatcher(os.path.join(TASK_DIR, "gold"))

result = run_loop(task, TASK_DIR, patcher, verbose=True)

print(f"\ntask       : {result.task_id}")
print(f"resolved   : {result.resolved}")
print(f"iterations : {result.iterations_used}")
print(f"pass@1     : {result.pass_at_1}")

print("\ntrajectory (what the loop did each step):")
for step in result.trajectory:
    status = "PASS" if step.passed else "FAIL"
    changed = ", ".join(step.changed_files) or "-"
    print(f"  iter {step.iteration}: {status:<4}  patched: {changed}")
