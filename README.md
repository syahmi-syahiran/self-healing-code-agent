# 🔁 Loop Engineering in AI

Reference implementations of **agentic loops** — the observe → act → re-observe
cycle that autonomous AI agents run until a task is done.

The interesting engineering isn't the LLM call. It's everything that makes the
loop *reliable*: how it terminates, how it recovers from failure, how it knows
it's finished, and how you measure whether it's getting better.

## What's here

### [`self-healing-code-agent/`](self-healing-code-agent/)

An agent that fixes buggy code by writing → testing → reading the failure →
patching → re-testing, until the tests pass or it runs out of budget.

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

Runs with **zero dependencies** (Python stdlib only) — no API key needed to
exercise the harness. Plug in a real Claude patcher when you want the loop to
actually reason.

```bash
cd self-healing-code-agent
python score.py --patcher gold --verbose   # perfect stand-in -> 100% resolved
python score.py --patcher noop             # baseline that never fixes -> 0%
python score.py --patcher claude           # real LLM loop (needs ANTHROPIC_API_KEY)
```

📖 **[Full usage guide](self-healing-code-agent/USAGE.md)** — setup, CLI, Python
API, writing your own patcher, connecting Claude, adding tasks, troubleshooting.
🧪 **[Runnable examples](self-healing-code-agent/examples/)** — programmatic API,
a custom patcher, the real Claude loop, and a new-task template.

## The core lesson: every loop needs an oracle

A loop can only self-correct if something tells it whether the last attempt was
good. That oracle is what defines the loop — and it's usually the hard part, not
the agent:

| Oracle type | Example | Benchmarks built on it |
|---|---|---|
| **Executable check** | unit tests, code runs | SWE-bench, HumanEval |
| **Gold reference** | the correct answer | GSM8K, MultiWOZ |
| **Relevance judgment** | graded documents | MS MARCO, BEIR |
| **Human/AI preference** | A vs. B ratings | RLHF preference pairs |
| **Constraint/validator** | schema, business rules | your own spec |

In `self-healing-code-agent`, the oracle is **"do the tests exit 0?"** — which is
why it's the cleanest loop to learn on.

## Other loop scenarios worth building

| Scenario | Loop | Dataset you'd need |
|---|---|---|
| Self-correcting extraction | validate → retry | gold entity/relation labels |
| Iterative RAG | retrieve → critique → re-retrieve | Q&A + supporting source IDs |
| Reflection | generate → critique → revise | inputs + reference or rubric |
| Active learning | train → find uncertain → label → retrain | unlabeled pool + oracle |
| Red-teaming | attack → judge → refine | seed prompts + safety classifier |
| Incident response | detect → hypothesize → diagnose → fix | labeled incident timelines |

## License

MIT
