# 🔁 Self-Healing Code Agent

An agent that fixes buggy code by writing → testing → reading the failure →
patching → re-testing, until the tests pass or it runs out of budget.

The canonical **agentic loop**, small enough to read in one sitting and
**runnable with zero dependencies** — Python stdlib only, no API key needed.

```
observe ──► tests pass? ──yes──► STOP (resolved)
(run tests)      │
                 no
                 ▼
              act (patcher proposes a fix)
                 ▼
              apply patch ──► re-observe
                 │
                 └─► budget exhausted? ──► STOP (unresolved)
```

## Run it

```bash
python score.py --patcher gold --verbose   # perfect stand-in -> 100%
python score.py --patcher noop             # baseline that never fixes -> 0%
python score.py --patcher claude           # real LLM loop (needs an API key)
```

`noop` and `gold` bracket the score. Any real policy lands between them — if it
doesn't, your harness is broken, not your model.

## 📖 Documentation

**[USAGE.md](USAGE.md)** is the full guide: setup, CLI, Python API, writing your
own patcher, connecting Claude, adding tasks, reading the metrics, troubleshooting.

Four runnable examples:

| Example | Shows |
|---|---|
| [`01_run_one_task.py`](examples/01_run_one_task.py) | Driving the loop from Python; reading the trajectory |
| [`02_custom_patcher.py`](examples/02_custom_patcher.py) | Writing your own brain — a regex patcher that solves 2/3 |
| [`03_claude_patcher.py`](examples/03_claude_patcher.py) | The real LLM loop, calling Claude |
| [`04_new_task_template/`](examples/04_new_task_template/) | Adding your own bug-fix task |

## Why this is "loop engineering"

The interesting work isn't the LLM call. It's everything that makes the loop
**reliable**:

| Concern | Where it lives |
|---|---|
| **Termination** (never infinite) | `agent/loop.py` — stop on pass or `max_iterations` |
| **Isolation** (a crash can't corrupt state) | each run works on a temp copy of the code |
| **Error recovery** (learn from failure) | the failing test output is fed into the next `PatchContext` |
| **Observability** (what happened each step) | every step is recorded in a `trajectory` |
| **The oracle** (how it knows it's done) | `harness/runner.py` — tests exit 0 = resolved |
| **Pluggable policy** (swap the brain, keep the harness) | `agent/patchers.py` |

## Layout

```
self-healing-code-agent/
├── USAGE.md                    # the full guide
├── examples/                   # four runnable examples
├── schema/task.schema.json     # what a task is
├── data/tasks/<id>/            # the DATASET
│   ├── buggy/     solution.py  # where the loop starts (broken)
│   ├── gold/      solution.py  # known-good — ORACLE ONLY, hidden from the agent
│   ├── tests/     test_*.py    # the oracle: exit 0 == fixed
│   └── meta.json               # task config
├── harness/runner.py           # runs tests in isolation -> pass/fail + output
├── agent/patchers.py           # NoOp / Gold / Claude policies
├── agent/loop.py               # the loop engine
└── score.py                    # run a patcher over all tasks -> metrics
```

## The dataset is the hard part

The loop code is small; the leverage is in the **task set + oracle**. Each task
is `(buggy code, a test that defines "fixed", an optional gold reference)`.

**The test is the specification.** If it's weak, a wrong patch scores as
resolved. To grow this toward something serious, mine tasks the way the public
suites do: **SWE-bench** (real GitHub issues + failing test + merged fix),
**Defects4J**, **QuixBugs**, **HumanEval**.

## Metrics

| Metric | What it tells you |
|---|---|
| **resolved_rate** | The headline — fraction of tasks that end green |
| **pass@1** | Fraction fixed on the first patch (one-shot skill) |
| **avg_iters_solved** | Mean attempts among solved tasks (loop cost) |

If `resolved_rate == pass@1`, the loop isn't contributing — a single-shot call
would score the same. The gap between them is what iteration buys you.
