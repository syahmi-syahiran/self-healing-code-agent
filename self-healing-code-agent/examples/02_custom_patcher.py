#!/usr/bin/env python3
"""Example 2 — write your own patcher (the pluggable "brain").

A patcher is anything with a `propose(ctx) -> {path: new_contents}` method.
Here we write a dumb rule-based one: no LLM, just regex fixes. It solves two of
the three tasks and fails the third — which is the point. You get a partial
score, and the loop/oracle/metrics stay identical. That is the whole design:
hold the harness constant, iterate on the policy.

    python examples/02_custom_patcher.py
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from agent.loop import run_loop
from agent.patchers import PatchContext

TASKS_DIR = os.path.join(HERE, "data", "tasks")


class RegexPatcher:
    """Applies two hard-coded rewrites. Knows nothing about the task."""

    name = "regex"

    RULES = [
        # off-by-one: range(1, n) -> range(1, n + 1)
        (re.compile(r"range\((\w+),\s*(\w+)\)"), r"range(\1, \2 + 1)"),
        # inverted comparison: `return s != ...` -> `return s == ...`
        (re.compile(r"return (\w+) != "), r"return \1 == "),
    ]

    def propose(self, ctx: PatchContext) -> dict[str, str]:
        out: dict[str, str] = {}
        for path, body in ctx.files.items():
            patched = body
            for pattern, replacement in self.RULES:
                patched = pattern.sub(replacement, patched)
            if patched != body:
                out[path] = patched
        return out  # {} means "no idea" — the loop stops rather than spin


def main() -> None:
    results = []
    for name in sorted(os.listdir(TASKS_DIR)):
        root = os.path.join(TASKS_DIR, name)
        with open(os.path.join(root, "meta.json")) as fh:
            task = json.load(fh)
        res = run_loop(task, root, RegexPatcher(), verbose=True)
        results.append(res)
        print(f"  -> {task['id']}: {'RESOLVED' if res.resolved else 'unresolved'}\n")

    solved = sum(r.resolved for r in results)
    print(f"regex patcher solved {solved}/{len(results)}")
    print("The one it misses needs an added guard clause, not a substitution.")
    print("That gap is exactly what an LLM patcher closes: --patcher claude")


if __name__ == "__main__":
    main()
