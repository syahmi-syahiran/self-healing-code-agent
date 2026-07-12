"""Patchers = the pluggable "brain" of the loop.

A patcher sees the current (broken) files plus the last test output and proposes
new file contents. It is the only component you swap to change the agent under
test; the loop and the oracle stay fixed. That separation is the whole point of
loop engineering: hold the harness constant, iterate on the policy.

Interface
---------
    propose(ctx: PatchContext) -> dict[str, str]
        returns {relative_path: new_full_contents} for files to overwrite.
        Return {} to make no change (the loop will then hit its budget).
"""
from __future__ import annotations

import glob
import os
from dataclasses import dataclass


@dataclass
class PatchContext:
    files: dict[str, str]   # relpath -> current contents (what the agent may edit)
    test_output: str        # combined stdout/stderr from the last failing run
    description: str        # human-readable task hint
    iteration: int          # 0-based attempt number


class NoOpPatcher:
    """Never edits anything. Use it to observe an UNRESOLVED trajectory:
    the loop should exhaust its budget and report resolved=False."""

    name = "noop"

    def propose(self, ctx: PatchContext) -> dict[str, str]:
        return {}


class GoldPatcher:
    """Perfect stand-in for a real model. Reads the task's gold files and returns
    them, so the harness resolves at pass@1. Use it to validate that the loop,
    oracle, and scoring all work end-to-end WITHOUT needing an API key.

    A real agent must never see gold - this is a test double, not a policy."""

    name = "gold"

    def __init__(self, gold_dir: str):
        self._gold = {}
        for path in glob.glob(os.path.join(gold_dir, "**", "*.py"), recursive=True):
            rel = os.path.relpath(path, gold_dir)
            with open(path) as fh:
                self._gold[rel] = fh.read()

    def propose(self, ctx: PatchContext) -> dict[str, str]:
        # Only return files that actually differ from what's on disk.
        return {p: c for p, c in self._gold.items() if ctx.files.get(p) != c}


class ClaudePatcher:
    """The REAL self-healing policy: ask Claude to rewrite the file given the
    failing test output, then let the loop re-run the oracle. Requires the
    `anthropic` package and ANTHROPIC_API_KEY. Kept dependency-free at import
    time so the demo runs without it.
    """

    name = "claude"

    def __init__(self, model: str = "claude-opus-4-8"):
        self.model = model

    def propose(self, ctx: PatchContext) -> dict[str, str]:
        import anthropic  # imported lazily so the offline demo needs no SDK

        client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
        files_blob = "\n\n".join(
            f"### FILE: {path}\n```python\n{body}\n```" for path, body in ctx.files.items()
        )
        prompt = (
            "You are a debugging agent. A test is failing. Rewrite ONLY the file(s) "
            "needed to make the test pass. Do not read or invent a reference solution.\n\n"
            f"Task hint: {ctx.description}\n\n"
            f"Current files:\n{files_blob}\n\n"
            f"Failing test output:\n```\n{ctx.test_output}\n```\n\n"
            "Respond with each corrected file as a fenced block preceded by "
            "'### FILE: <path>' on its own line. Include the FULL file contents."
        )
        msg = client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in msg.content if block.type == "text")
        return _parse_file_blocks(text)


def _parse_file_blocks(text: str) -> dict[str, str]:
    """Extract {path: contents} from '### FILE: path' + fenced code blocks."""
    out: dict[str, str] = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("### FILE:"):
            path = line.split("### FILE:", 1)[1].strip()
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                i += 1
            i += 1  # skip opening fence
            body: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                body.append(lines[i])
                i += 1
            out[path] = "\n".join(body) + "\n"
        i += 1
    return out
