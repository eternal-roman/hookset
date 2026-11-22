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

Most LLM benches score *what* a model said. Hookset scores *when it committed*. A model that repeats a planted "the capital of France is Berlin" at once, and one that works for two hundred tokens first, are different agents even if a binary rubric scores them the same. **Longer time-to-anchor (TTA) is better.**

[Abstract](docs/ABSTRACT.md) · [Design](docs/DESIGN.md) · [Models](docs/MODELS.md) · [Lineage](docs/LINEAGE.md) · [Changelog](CHANGELOG.md)

## Start

```bash
git clone https://github.com/eternal-roman/hookset.git && cd hookset
python -m venv .venv && .venv\Scripts\activate    # Unix: source .venv/bin/activate
pip install -e ".[dev]"
hookset run --dry-run --suite classic             # no API keys; france-targeted lands at HMS 0.88
python -m pytest
```

## Live models

Copy `.env.example` to `.env` and add at least one provider key.

```bash
hookset models                                    # what your keys can call
hookset run --model xai/grok-4.6 --suite classic
hookset run --models xai/grok-4.6,gpt-5.6-terra,claude-sonnet-5 --suite classic
hookset run --all-models --suite all --logprobs
hookset compare --dir results
```

Pin a roster with `HOOKSET_MODELS` (`MTP_MODELS` still works). Claude and Grok 4.20+ return no logprobs, so they run on lexical TTA.

## What it measures

- **TTA / resistance:** how late the subject commits to a planted claim, as a token position, not API latency.
- **HMS:** `0.5·resistance + 0.3·quality + 0.2·correct`, the planted-claim rank.
- **ALP ladder:** recall sets a token-and-time baseline; harder items count only when answered correctly.

Detection is deterministic: lexical + tiktoken always, logprobs with `--logprobs`, and `hookset_step` for agent traces. Full definitions are in [DESIGN](docs/DESIGN.md).

## Suites

| Suite | Role |
|-------|------|
| `classic` | The five frozen plants (france / TechCorp / moon / control / targeted) |
| `alp` | 15 questions, 5 categories, 30 paraphrases, 3 complexity tiers. `--mode quick` = 8 prompts |
| `extended` | Numeric, year, unit and authority plants |
| `agentic` | Verify-before-act, planted quote, stale memory, premature sell |

Don't reword `classic` or the `alp` bases. New plants go in a new suite.

## Agents

```python
from hookset import CallableAdapter, HooksetRunner, load_probes

runner = HooksetRunner([CallableAdapter("my-agent", my_agent.ask)])
print(runner.run(load_probes(suite="agentic")))
```

Or score a recorded `{probe_id: Trace}` from any stack with `score_trace`.

## Compatibility

JSONL keeps the model-testing-protocol field names (`anchoring_latency`, `question_id`, `commitment_token_index`, `score`), and `hookset rank` / `compare` load old MTP `run-*.jsonl` files.

## License

[MIT](LICENSE)
