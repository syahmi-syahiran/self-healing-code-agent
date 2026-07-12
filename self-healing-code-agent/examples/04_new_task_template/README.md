# Example 4 — adding your own task

A task is just a folder. Copy this one into `data/tasks/` and `score.py` picks
it up automatically — no registration, no code change.

```bash
cp -r examples/04_new_task_template data/tasks/004_ordering_bug
python score.py --patcher gold      # now runs 4 tasks instead of 3
```

## The four pieces

| Path | Role |
|---|---|
| `buggy/solution.py` | Where the loop starts. Must actually fail the test. |
| `tests/test_solution.py` | **The oracle.** Exit code 0 = fixed. This defines "done". |
| `gold/solution.py` | A known-good fix. Oracle-only — the agent never sees it. |
| `meta.json` | Config. Must match `schema/task.schema.json`. |

## Rules that matter

1. **The test is the specification.** If the test is weak, a wrong patch scores
   as resolved. Write assertions that pin down the actual contract, including
   edge cases.
2. **The test must fail on `buggy/` and pass on `gold/`.** If it passes on
   `buggy/`, the loop resolves at iteration 0 having done nothing.
3. **Tests run as plain scripts** (`python test_solution.py`), not pytest — use
   `assert` and exit non-zero on failure. Keeps the harness dependency-free.
4. **Never let the agent read `gold/`.** It exists to validate the harness
   (via `GoldPatcher`) and to let you diff proposed patches against a reference.

## Verify it before trusting the score

The test imports `solution`, so the code directory must be on the import path —
that is exactly what the harness does (`PYTHONPATH=<code_dir>`). Reproduce it by
hand from inside the task folder:

```bash
PYTHONPATH=buggy python tests/test_solution.py   # expect: AssertionError (fails)
PYTHONPATH=gold  python tests/test_solution.py   # expect: OK
```

```powershell
# PowerShell
$env:PYTHONPATH="buggy"; python tests\test_solution.py   # expect: fails
$env:PYTHONPATH="gold";  python tests\test_solution.py   # expect: OK
```

If the buggy version *passes*, the test is too weak and the loop will score a
no-op as "resolved".
