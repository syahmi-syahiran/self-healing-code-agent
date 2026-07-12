#!/usr/bin/env python3
"""Example 3 — the real LLM loop, calling Claude.

This is the loop actually reasoning: Claude sees the broken file plus the
failing test output, proposes a rewrite, the oracle re-runs the tests, and if it
still fails the NEW failure is fed back on the next iteration.

Requires:
    pip install anthropic
    export ANTHROPIC_API_KEY=sk-ant-...      # (PowerShell: $env:ANTHROPIC_API_KEY="...")

    python examples/03_claude_patcher.py

Cost note: each iteration is one Claude call on a tiny file. Claude Opus 4.8 is
$5/$25 per million input/output tokens, so a full 3-task run is fractions of a
cent. Drop to --effort low, or pass model="claude-sonnet-5" ($3/$15), to spend
less; raise to "xhigh" for harder bugs.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from agent.loop import run_loop
from agent.patchers import ClaudePatcher

TASKS_DIR = os.path.join(HERE, "data", "tasks")


def main() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY first (see the docstring above).")

    # effort controls how hard Claude thinks per attempt: low | medium | high | xhigh | max
    patcher = ClaudePatcher(model="claude-opus-4-8", effort="high")

    results = []
    for name in sorted(os.listdir(TASKS_DIR)):
        root = os.path.join(TASKS_DIR, name)
        with open(os.path.join(root, "meta.json")) as fh:
            task = json.load(fh)

        print(f"\n=== {task['id']} ===")
        print(f"bug: {task['description']}")
        res = run_loop(task, root, patcher, verbose=True)
        results.append(res)
        print(f"--> {'RESOLVED' if res.resolved else 'unresolved'} "
              f"in {res.iterations_used} iteration(s)")

    solved = sum(r.resolved for r in results)
    at_1 = sum(r.pass_at_1 for r in results)
    print(f"\nresolved {solved}/{len(results)}   pass@1 {at_1}/{len(results)}")


if __name__ == "__main__":
    main()
