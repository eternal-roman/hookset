# Lineage

How this repository was recovered and what was (and was not) found.

## Search performed (2026-08-14)

| Location | Result |
|----------|--------|
| `C:\Users\elamj\Dev\Research` | Not a git repo. Trading-upgrade notes only. The three starter files (`agentic-*-plan.md`, `agentic-trading-platform-analysis.md`) are **GodzillaBot / Hydra** agentic-upgrade memos, not the TTA bench. |
| `C:\Users\elamj\Dev\Research-2026-06-archive.zip` | Same six markdown files. No protocol source. |
| Every git repo under `Dev\` (all local + remote branches, commit messages, added paths) | Only `model-testing-protocol` carries the bench. |
| `model-testing-protocol` | **Canonical survival.** `main` @ `24791b9` (PARKED 2026-08-07), tag `v0.3.0`, orphan `archive/local-clean-port-orphan`. Remote: `eternal-roman/model-testing-protocol`. |
| Grok worktree `~\.grok\worktrees\dev-model-testing-protocol\mtp` | Unreleased **0.3.1**: `get_available_models`, `list-models`, `MTP_MODELS`, `MODEL_CONFIG_TODO.md`, dry-run `results/`. Not on parked main. |
| `context-binding-protocol` | Hosted the original **gitignored** folders `anchoring-latency-protocol/` and `comparison_test/` (venv + `.env` only; no source). Claude history 2026-06: user marked them "totally separate"; they were then deleted as local cleanup. |
| Cursor plan `fix_comparison_test_d96e9edd` | A **different** `comparison_test/` — CBP vs Graphiti token honesty, not anchoring. |
| GitHub `user:eternal-roman` | MTP exists; no `anchoring-latency-protocol` repo. |
| Antigravity brain `e314825a-65b9-422e-b88c-f36c9bd703ce` | **Original ALP.** 15 prompts × 5 categories, 30 perturbations, 3 complexity tiers, TTFT/ITCV/PSI/CSC/CUR + ALI. Source was gitignored under CBP and later deleted. Prompt text recovered from `implementation_plan.md`. |

## Original intent (from the user's own prompts, 2026-06-19/20)

> "a genuine testing framework that I setup to look at models tendency to **anchor sooner and not conduct inference**"

> "The real code should be a list of questions that are sent to the API and then some scoring code that determines **how soon a model anchors**."

> "it did a great job of finding how soon a model anchors **before doing inference**"

That is the thesis restated in this repo: **longer time-to-anchor = more inference = better**.

## Semantics bug (documented, then fixed)

The first port commit (`fe8b5ce`, package `anchoring_latency_protocol`) computed

```text
anchoring_latency = 1.0 - (anchor_point / 300)
```

which made *early* hooks look *high*. The docstring said the opposite. `b08ed81` (merged `73bc833`) inverted the logprob branch to `idx/n` so **early bad commitment = low score**. `MEASUREMENT_FIX_PLAN.md` records that confusion. Hookset keeps the **corrected** direction and names it TTA / resistance, with `anchoring_latency` as an alias.

## What Hookset takes from MTP

- Classic probe JSON (france / TechCorp / moon / control / targeted) unchanged.
- ALP 15-prompt battery (Antigravity `e314825a`) as suite `alp`: tiktoken onset vs recall, plus call/TTFT time.
- Lexical `find_anchor_point` and logprob commitment / onset helpers.
- Maturity weights `0.5 / 0.3 / 0.2`.
- Dry-run mock behaviors.
- JSONL + ranked report.
- 0.3.1 model discovery (`MTP_MODELS`, list-models) finished as `HOOKSET_MODELS`, `hookset models`, `hookset run --all-models`.

## What was planned and never existed

- `anchor-test compare` (README listed it; not implemented). **Now `hookset compare`.**
- Packaged `models.yaml` + batch `--all-models`. **Now implemented.**
- Graphiti / Neo4j / Kuzu "optional graph" and FastAPI server. Declared optional, never built. **Not revived.**
- The pre-port source on "another branch." Never found. The port *is* the source.

## Migration complete (2026-08-14)

Everything that still had value in parked MTP v0.3.0 and the unreleased 0.3.1 worktree is now in this repo:

| Remainder | Where it lives now |
|-----------|-------------------|
| Classic probes | `src/hookset/data/classic.json` |
| Scoring + logprobs + onset | `src/hookset/detect.py`, `score.py` |
| 0.3.1 model discovery | `src/hookset/catalog.py` (`HOOKSET_MODELS` / `MTP_MODELS`) |
| Recommended-models table | [`docs/MODELS.md`](MODELS.md) |
| Measurement-fix notes | [`docs/history/MEASUREMENT_FIX_PLAN.md`](history/MEASUREMENT_FIX_PLAN.md) |
| Historical mock JSONL | `tests/fixtures/mtp-v0.3.1/` |
| pre-commit + detect-secrets | `.pre-commit-config.yaml` |
| DeepSeek key | `.env.example` + roster |

Old copies are **retired**, not parked:

- Local `C:\Users\elamj\Dev\model-testing-protocol` — deleted after this migration
- Grok worktree `~\.grok\worktrees\dev-model-testing-protocol` — deleted
- GitHub `eternal-roman/model-testing-protocol` — archived, successor is this repo

Do not revive those trees. New work belongs here.
