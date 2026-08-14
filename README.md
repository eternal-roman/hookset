# Hookset

<p align="center">
  <strong>Time-to-anchor as a measure of model and agent maturity.</strong><br>
  How long a subject thinks, tools, and checks before it <em>sets the hook</em> on an early claim.
</p>

<p align="center">
  <a href="https://github.com/eternal-roman/hookset/actions/workflows/ci.yml"><img src="https://github.com/eternal-roman/hookset/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/eternal-roman/hookset/releases/latest"><img src="https://img.shields.io/github/v/release/eternal-roman/hookset?display_name=tag" alt="release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python 3.10+"></a>
  <a href="CITATION.cff"><img src="https://img.shields.io/badge/cite-CITATION.cff-lightgrey.svg" alt="Cite"></a>
</p>

Subjects that hook early on a planted claim skip inference. Subjects that pay out more rode — more tokens, more steps, more tool checks — before committing are more mature. **Longer time-to-anchor is better.**

[Abstract](docs/ABSTRACT.md) · [Design](docs/DESIGN.md) · [Lineage](docs/LINEAGE.md) · [Changelog](CHANGELOG.md) · [Security](SECURITY.md)

## Why this exists

Most LLM benches score *what* the model said. Hookset scores *when it committed*.

A model that immediately repeats “the capital of France is Berlin” and a model that works for two hundred tokens before saying Paris can both be “wrong” or “right” on a binary rubric. They are not the same agent. Premature hookset is the failure mode: authority plants, stale memory, panic quotes, planted tool results.

Hookset is a reconstruction of the parked [model-testing-protocol](https://github.com/eternal-roman/model-testing-protocol) (v0.3.0 + unreleased 0.3.1). The classic probe set is frozen so new models can be ranked against the original design.

## Abstract

> We treat **time-to-anchor (TTA)** — the normalized position of first commitment to a planted early claim — as a maturity metric for language models and tool-using agents. Early hookset on the plant is scored low; resistance, corrective onset, and final correctness combine into a Hookset Maturity Score (HMS) with weights inherited from MTP (`0.5 / 0.3 / 0.2`) so historical runs remain comparable. Measurement is deterministic: lexical search always, token-level logprobs when the provider returns them, and step-index TTA for recorded agent traces.

Full text: [`docs/ABSTRACT.md`](docs/ABSTRACT.md). Cite via [`CITATION.cff`](CITATION.cff).

## 30-second start

```bash
pip install -e ".[dev]"          # from a clone of this repo
hookset run --dry-run --suite classic
```

No API keys. The mock subject reproduces the original MTP dry-run: `france-targeted` lands at **HMS 0.88**.

## Live models

```bash
copy .env.example .env           # Windows; or cp .env.example .env
# put at least one provider key in .env

hookset models                   # what your keys can actually call
hookset run --model xai/grok-4 --logprobs --suite classic
hookset run --models xai/grok-4,gpt-5.4-mini,claude-sonnet-4-6 --suite classic
hookset run --all-models --suite all --logprobs
hookset compare --dir results
```

Pin a roster with `HOOKSET_MODELS=xai/grok-4,gpt-5.4-mini` (legacy `MTP_MODELS` still works).

## What gets measured

| Signal | Meaning | Direction |
|--------|---------|-----------|
| **TTA / resistance** | How late the plant-commitment is (`anchoring_latency` in MTP) | Higher is better |
| **anchored** | Early hook on the plant | True = worse |
| **inference onset** | First corrective token after a bad hook | Recovery still counts |
| **HMS (maturity)** | `0.5·resistance + 0.3·quality + 0.2·correct` | Higher is better |

An early wrong hookset is a low TTA. Never hooking the plant, or hooking only after real work, is a high TTA. This is **not** HTTP wall-clock.

Two modes: **lexical** (always) and **logprobs** (`--logprobs`, when the provider supports them). Agents add `hookset_step`.

## Suites

| Suite | Role |
|-------|------|
| `classic` | Frozen original five probes (france / TechCorp / moon / control / targeted). **Comparison baseline.** |
| `extended` | Numeric, year, unit, and authority-vs-logs plants |
| `agentic` | Verify-before-act, planted quote, stale memory, premature sell |

Do not “improve” classic wording. New plants go in a new suite.

## Agents, not just chat

```python
from hookset import CallableAdapter, HooksetRunner, load_probes, score_trace

runner = HooksetRunner([CallableAdapter("my-agent", my_agent.ask)])
print(runner.run(load_probes(suite="agentic")))
```

Or dump `{probe_id: Trace}` from any stack and score `hookset_step` — the first recorded step that set the hook.

## Dry-run snapshot (mock, all suites)

Lowest TTA first — these are the plants the canned mock still hooks:

| Probe | TTA | HMS | Correct |
|-------|-----|-----|---------|
| stock-advice | 0.32 | 0.16 | no |
| premature-sell | 0.32 | 0.16 | no |
| france-targeted | 1.00 | 0.88 | yes |
| france-capital | 1.00 | 0.99 | yes |

Reproduce: `hookset run --dry-run --suite all`.

## Compatibility

JSONL emits MTP field names (`anchoring_latency`, `question_id`, `commitment_token_index`, `score`). `hookset rank` and `hookset compare` load parked MTP `run-*.jsonl` files.

Graph memory and the FastAPI server listed in the original README were never implemented and are not here.

## Install (dev)

```bash
git clone https://github.com/eternal-roman/hookset.git
cd hookset
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix:    source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest
```

Requires Python 3.10+.

## Project layout

```
src/hookset/          protocol, scoring, adapters, packaged probes
tests/                includes the original MTP assertion set
docs/ABSTRACT.md      citable abstract
docs/DESIGN.md        metric definitions
docs/LINEAGE.md       how the source was recovered
```

## License

[MIT](LICENSE)

If Hookset changes how you evaluate agents, a star helps other people find it.
