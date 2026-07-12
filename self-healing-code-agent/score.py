#!/usr/bin/env python3
"""Evaluate a patcher over the whole task dataset and print loop metrics.

Usage:
    python score.py --patcher gold     # perfect stand-in (no API key)
    python score.py --patcher noop     # baseline: never fixes -> 0% resolved
    python score.py --patcher claude   # real LLM loop (needs anthropic + key)

Metrics reported:
    resolved_rate      fraction of tasks whose tests end green (the headline number)
    pass@1             fraction resolved on the very first patch
    avg_iters_solved   mean patch attempts across the tasks that were solved
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # make agent/ and harness/ importable when run directly

from agent.loop import run_loop
from agent.patchers import NoOpPatcher, GoldPatcher, ClaudePatcher

TASKS_DIR = os.path.join(HERE, "data", "tasks")


def load_tasks() -> list[tuple[dict, str]]:
    out = []
    for name in sorted(os.listdir(TASKS_DIR)):
        root = os.path.join(TASKS_DIR, name)
        meta_path = os.path.join(root, "meta.json")
        if os.path.isfile(meta_path):
            with open(meta_path) as fh:
                out.append((json.load(fh), root))
    return out


def make_patcher(kind: str, task_root: str):
    if kind == "noop":
        return NoOpPatcher()
    if kind == "gold":
        return GoldPatcher(os.path.join(task_root, "gold"))
    if kind == "claude":
        return ClaudePatcher()
    raise SystemExit(f"unknown patcher: {kind}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--patcher", default="gold", choices=["noop", "gold", "claude"])
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    tasks = load_tasks()
    if not tasks:
        raise SystemExit(f"no tasks found under {TASKS_DIR}")

    results = []
    print(f"\nRunning {len(tasks)} task(s) with patcher='{args.patcher}'\n")
    for task, root in tasks:
        patcher = make_patcher(args.patcher, root)
        res = run_loop(task, root, patcher, verbose=args.verbose)
        status = "RESOLVED" if res.resolved else "unresolved"
        print(f"  {task['id']:<24} {status:<11} iters={res.iterations_used}")
        results.append(res)

    n = len(results)
    resolved = [r for r in results if r.resolved]
    resolved_rate = len(resolved) / n
    pass_at_1 = sum(r.pass_at_1 for r in results) / n
    avg_iters = (sum(r.iterations_used for r in resolved) / len(resolved)) if resolved else 0.0

    print("\n" + "-" * 44)
    print(f"  resolved_rate     {resolved_rate:6.0%}   ({len(resolved)}/{n})")
    print(f"  pass@1            {pass_at_1:6.0%}")
    print(f"  avg_iters_solved  {avg_iters:6.2f}")
    print("-" * 44 + "\n")


if __name__ == "__main__":
    main()
