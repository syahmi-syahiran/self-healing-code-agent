# Usage Guide

Everything you need to run, extend, and plug an LLM into the self-healing loop.

- [1. Setup](#1-setup)
- [2. Running it](#2-running-it)
- [3. The CLI](#3-the-cli)
- [4. The Python API](#4-the-python-api)
- [5. Writing your own patcher](#5-writing-your-own-patcher)
- [6. Connecting Claude](#6-connecting-claude)
- [7. Adding tasks](#7-adding-tasks)
- [8. Reading the metrics](#8-reading-the-metrics)
- [9. Troubleshooting](#9-troubleshooting)

---

## 1. Setup

**The harness needs nothing but Python 3.9+.** No pytest, no pip install, no API
key. That is deliberate — you can exercise the whole loop offline.

```bash
git clone https://github.com/syahmi-syahiran/self-healing-code-agent.git
cd self-healing-code-agent/self-healing-code-agent
python score.py --patcher gold
```

You only need dependencies for the **real LLM loop**:

```bash
pip install -r requirements.txt          # installs `anthropic`
export ANTHROPIC_API_KEY=sk-ant-...      # bash
$env:ANTHROPIC_API_KEY="sk-ant-..."      # PowerShell
```

Get a key at [console.anthropic.com](https://console.anthropic.com/settings/keys).

---

## 2. Running it

Three patchers ship in the box. Run them in this order — it's the fastest way to
understand what the harness measures.

```bash
python score.py --patcher noop        # 0%   — baseline: never edits anything
python score.py --patcher gold        # 100% — perfect stand-in, validates the harness
python score.py --patcher claude      # ?    — the real thing (needs an API key)
```

`noop` and `gold` bracket the score. Any real policy lands between them; if it
doesn't, your harness is broken, not your model.

```
Running 3 task(s) with patcher='gold'

  001_off_by_one           RESOLVED    iters=1
  002_bad_operator         RESOLVED    iters=1
  003_empty_edge_case      RESOLVED    iters=1

--------------------------------------------
  resolved_rate       100%   (3/3)
  pass@1              100%
  avg_iters_solved    1.00
--------------------------------------------
```

Add `--verbose` to watch each iteration:

```
[001_off_by_one] iter 0: FAIL -> patched solution.py
[001_off_by_one] iter 1: PASS
```

---

## 3. The CLI

```
python score.py [--patcher {noop,gold,claude}] [--model ID] [--effort LEVEL] [--verbose]
```

| Flag | Default | Meaning |
|---|---|---|
| `--patcher` | `gold` | Which brain to run. `noop` / `gold` need no API key. |
| `--model` | `claude-opus-4-8` | Model id (only used by `--patcher claude`). |
| `--effort` | `high` | `low`\|`medium`\|`high`\|`xhigh`\|`max` — how hard Claude thinks per attempt. |
| `--verbose` | off | Print every loop iteration, not just the final verdict. |

---

## 4. The Python API

Four things, that's the whole surface.

```python
from agent.loop import run_loop          # the loop engine
from agent.patchers import PatchContext  # what a patcher receives
from harness.runner import run_tests     # the oracle
```

### `run_loop(task, task_root, patcher, verbose=False) -> LoopResult`

Drives one task to completion. `task` is the parsed `meta.json`; `task_root` is
the folder containing it.

```python
import json
from agent.loop import run_loop
from agent.patchers import GoldPatcher

task = json.load(open("data/tasks/001_off_by_one/meta.json"))
result = run_loop(task, "data/tasks/001_off_by_one",
                  GoldPatcher("data/tasks/001_off_by_one/gold"))

result.resolved          # True  — did the tests end green?
result.iterations_used   # 1     — how many patches were attempted
result.pass_at_1         # True  — fixed on the very first patch?
result.trajectory        # [IterationRecord, ...] — the full step-by-step record
```

### `IterationRecord`

One entry per loop step, so you can audit *how* it got there:

```python
for step in result.trajectory:
    step.iteration      # 0, 1, 2...
    step.passed         # did tests pass at the START of this step?
    step.changed_files  # ["solution.py"] — what the patcher rewrote
    step.test_output    # the failure text that was fed back to the patcher
```

### `run_tests(code_dir, test_dir, timeout=15) -> TestResult`

The oracle, callable on its own. Runs every `test_*.py` in an isolated
subprocess with `code_dir` importable.

```python
res = run_tests("some/candidate", "some/tests")
res.passed   # bool — exit code 0 across all test files
res.output   # combined stdout+stderr (this is what the patcher gets to read)
```

Runnable version: [`examples/01_run_one_task.py`](examples/01_run_one_task.py).

---

## 5. Writing your own patcher

A patcher is **any object with a `propose` method**. No base class, no registration.

```python
def propose(self, ctx: PatchContext) -> dict[str, str]:
    ...  # returns {relative_path: new_full_file_contents}
```

`ctx` gives you everything the loop knows:

| Field | Type | What it is |
|---|---|---|
| `ctx.files` | `dict[str, str]` | Current (broken) files — path → contents |
| `ctx.test_output` | `str` | The failing test's stdout+stderr. **This is the feedback signal.** |
| `ctx.description` | `str` | Human-readable bug hint from `meta.json` |
| `ctx.iteration` | `int` | 0-based attempt number — use it to escalate strategy |

Return `{}` to say "no idea" — the loop stops early rather than burning its
budget re-running an identical candidate.

```python
class MyPatcher:
    name = "mine"

    def propose(self, ctx):
        if "ZeroDivisionError" in ctx.test_output:
            body = ctx.files["solution.py"]
            return {"solution.py": "    if not nums:\n        return 0.0\n" + body}
        return {}
```

Runnable version: [`examples/02_custom_patcher.py`](examples/02_custom_patcher.py) —
a regex patcher that deliberately solves only 2 of 3, to show a partial score.

---

## 6. Connecting Claude

[`ClaudePatcher`](agent/patchers.py) is the real policy. It hands Claude the
current files plus the failing test output and parses corrected files back out.

```python
from agent.patchers import ClaudePatcher
patcher = ClaudePatcher(model="claude-opus-4-8", effort="high")
```

The call it makes, and why each parameter is there:

```python
client.messages.create(
    model="claude-opus-4-8",
    max_tokens=16000,
    thinking={"type": "adaptive"},        # REQUIRED — see the gotcha below
    output_config={"effort": "high"},     # low | medium | high | xhigh | max
    messages=[{"role": "user", "content": prompt}],
)
```

> ⚠️ **The gotcha that will bite you.** On Claude Opus 4.8, *omitting* `thinking`
> means the model runs with **no thinking at all**. It is not on by default — you
> must set `{"type": "adaptive"}` explicitly. Debugging from a stack trace is
> exactly the kind of multi-step reasoning that thinking helps with, so leaving
> it off quietly costs you accuracy.

Two more things worth knowing:

- **`temperature`, `top_p`, and `top_k` are rejected** (HTTP 400) on Opus 4.8.
  Steer behavior with the prompt and `effort`, not sampling knobs.
- **Content blocks interleave.** With thinking on, `response.content` contains
  `thinking` blocks *and* `text` blocks. Filter by `block.type == "text"` — the
  patcher does this already.

### Choosing a model

| Model | ID | Input / Output per 1M tokens |
|---|---|---|
| Claude Opus 4.8 | `claude-opus-4-8` | $5 / $25 |
| Claude Sonnet 5 | `claude-sonnet-5` | $3 / $15 |
| Claude Haiku 4.5 | `claude-haiku-4-5` | $1 / $5 |

```bash
python score.py --patcher claude --model claude-sonnet-5 --effort medium
```

Each iteration is one call on a small file, so a full 3-task run costs a fraction
of a cent. Raise `--effort` to `xhigh` for genuinely hard bugs; drop to `low` when
you're just smoke-testing the plumbing.

Runnable version: [`examples/03_claude_patcher.py`](examples/03_claude_patcher.py).

---

## 7. Adding tasks

A task is just a folder dropped into `data/tasks/`. `score.py` discovers it
automatically.

```bash
cp -r examples/04_new_task_template data/tasks/004_ordering_bug
python score.py --patcher gold      # now runs 4 tasks
```

Full walkthrough, including the two rules that matter most (**the test is the
spec**, and **it must fail on `buggy/` and pass on `gold/`**):
[`examples/04_new_task_template/README.md`](examples/04_new_task_template/README.md).

To grow this into a serious benchmark, mine tasks the way the public suites do —
**SWE-bench** (real GitHub issues + the failing test + the merged fix),
**Defects4J**, **QuixBugs**, **HumanEval**.

---

## 8. Reading the metrics

| Metric | What it tells you |
|---|---|
| `resolved_rate` | The headline. Fraction of tasks whose tests end green. |
| `pass@1` | Fraction fixed on the **first** patch. Measures one-shot skill. |
| `avg_iters_solved` | Mean attempts among solved tasks. Measures loop **cost**. |

Read them together, not separately:

- **High `resolved_rate`, low `pass@1`** → the loop is doing the work. Iteration
  and feedback are earning their keep.
- **`resolved_rate` == `pass@1`** → the loop isn't contributing; a single-shot
  call would score the same. Either the tasks are too easy, or the failure
  feedback isn't being used.
- **High `avg_iters_solved`** → it gets there, but expensively. Each iteration is
  an API call.

---

## 9. Troubleshooting

**`ModuleNotFoundError: No module named 'solution'`**
You ran a test directly without putting the code dir on the import path. Python
adds the *script's* directory to `sys.path`, not your cwd. The harness sets
`PYTHONPATH` itself; to reproduce by hand:
`PYTHONPATH=buggy python tests/test_solution.py`.

**`no tests found` / `no tasks found`**
Test files must match `test_*.py`. Task folders must contain a `meta.json`.

**Every task is `unresolved` with `--patcher claude`**
Print what the model returned. `_parse_file_blocks` expects `### FILE: <path>`
followed by a fenced code block; if the model answers in prose, it parses to `{}`
and the loop stops. Tighten the prompt or switch to structured outputs.

**A task "resolves" but the fix is obviously wrong**
Your test is too weak — it *is* the specification. Add assertions until a wrong
patch can't pass.

**The loop hangs**
`run_tests` has a 15s timeout per test file and reports `TIMEOUT`. If a patcher
itself hangs (e.g. a network call), that's outside the oracle's timeout — add
your own.
