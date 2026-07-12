"""The self-healing loop engine.

    observe (run tests)  ->  if pass: STOP (resolved)
        |                        ^
        v                        |
    act (patcher proposes) -> apply -> re-observe  (until budget spent)

Loop-engineering concerns made explicit here:
  * Termination      : tests pass, OR iteration budget exhausted (never infinite).
  * Isolation        : each run happens in a throwaway copy of the code.
  * Error recovery   : the failing test output is fed back into the next attempt.
  * Observability    : every iteration is recorded in a trajectory for scoring.
"""
from __future__ import annotations

import glob
import os
import shutil
import tempfile
from dataclasses import dataclass, field

from harness.runner import run_tests
from agent.patchers import PatchContext


@dataclass
class IterationRecord:
    iteration: int
    passed: bool
    changed_files: list[str]
    test_output: str


@dataclass
class LoopResult:
    task_id: str
    resolved: bool
    iterations_used: int          # attempts made before stopping
    patcher: str
    trajectory: list[IterationRecord] = field(default_factory=list)

    @property
    def pass_at_1(self) -> bool:
        """Resolved after a single patch (the first act)."""
        return self.resolved and self.iterations_used <= 1


def _load_dir(path: str) -> dict[str, str]:
    files = {}
    for p in glob.glob(os.path.join(path, "**", "*.py"), recursive=True):
        with open(p) as fh:
            files[os.path.relpath(p, path)] = fh.read()
    return files


def run_loop(task: dict, task_root: str, patcher, verbose: bool = False) -> LoopResult:
    """Drive the loop for one task. `patcher` implements propose(PatchContext)."""
    max_iters = task.get("max_iterations", 6)
    buggy_dir = os.path.join(task_root, task["buggy_dir"])
    test_dir = os.path.join(task_root, task["test_dir"])

    # Work on an isolated copy so the dataset on disk is never mutated.
    workdir = tempfile.mkdtemp(prefix=f"heal_{task['id']}_")
    try:
        shutil.copytree(buggy_dir, workdir, dirs_exist_ok=True)
        result = LoopResult(task_id=task["id"], resolved=False,
                            iterations_used=0, patcher=getattr(patcher, "name", "custom"))

        for it in range(max_iters):
            # --- observe -------------------------------------------------
            test_res = run_tests(workdir, test_dir)
            if test_res.passed:
                result.resolved = True
                result.trajectory.append(IterationRecord(it, True, [], test_res.output))
                if verbose:
                    print(f"    [{task['id']}] iter {it}: PASS")
                break

            # --- act -----------------------------------------------------
            ctx = PatchContext(
                files=_load_dir(workdir),
                test_output=test_res.output,
                description=task.get("description", ""),
                iteration=it,
            )
            patch = patcher.propose(ctx)
            for rel, contents in patch.items():
                dest = os.path.join(workdir, rel)
                os.makedirs(os.path.dirname(dest) or workdir, exist_ok=True)
                with open(dest, "w") as fh:
                    fh.write(contents)

            result.iterations_used = it + 1
            result.trajectory.append(
                IterationRecord(it, False, sorted(patch.keys()), test_res.output)
            )
            if verbose:
                changed = ", ".join(sorted(patch.keys())) or "(no change)"
                print(f"    [{task['id']}] iter {it}: FAIL -> patched {changed}")

            if not patch:
                # A patcher that proposes nothing will never progress; stop early
                # rather than burning the whole budget on identical reruns.
                break

        # Final observation if we stopped by budget right after a patch.
        if not result.resolved:
            final = run_tests(workdir, test_dir)
            result.resolved = final.passed
            if final.passed:
                result.trajectory.append(
                    IterationRecord(result.iterations_used, True, [], final.output)
                )
        return result
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
