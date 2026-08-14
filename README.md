# Hookset

> Time-to-anchor as a measure of model and agent maturity.
> The longer a subject waits before it **sets the hook** on an early claim, the more inference it actually did.

A reconstruction of the parked [model-testing-protocol](https://github.com/eternal-roman/model-testing-protocol) (v0.3.0 / unreleased 0.3.1) — the "anchoring latency" bench — rebuilt so you can feed it a **series of models** and **agents** and score them against the original design.

The original folders (`anchoring-latency-protocol/`, `comparison_test/`) were gitignored scaffolds inside context-binding-protocol; the working code survived as MTP. Lineage: [`docs/LINEAGE.md`](docs/LINEAGE.md). Design: [`docs/DESIGN.md`](docs/DESIGN.md).

## Thesis

Subjects that **hook early** on a planted claim skip inference. Subjects that **pay out more rode** — more tokens, more steps, more tool checks — before committing are more mature.

| Signal | Meaning | Direction |
|--------|---------|-----------|
| **TTA / resistance** (`anchoring_latency` in MTP) | How late the plant-commitment is | **Higher is better** |
| **anchored** | Early hook on the plant | True = worse |
| **inference onset** | First corrective token after a bad hook | Later recovery still counts |
| **HMS (maturity)** | `0.5·resistance + 0.3·quality + 0.2·correct` | Higher is better; **same weights as MTP** so numbers compare |

An early wrong hookset is a low TTA. Never hooking the plant, or hooking only after real work, is a high TTA.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Unix

pip install -e ".[dev]"
copy .env.example .env          # then fill in at least one provider key
```

## Usage

```bash
# Original five probes, no network
hookset run --dry-run --suite classic

# Every packaged suite against the mock subject
hookset run --dry-run --suite all

# One live model (auto-picked from .env if you omit --model)
hookset run --model xai/grok-4 --logprobs --suite classic

# A series of models in one run
hookset run --models xai/grok-4,gpt-5.4-mini,claude-sonnet-4-6 --suite classic

# Every reachable model from keys + roster
hookset run --all-models --suite classic --logprobs

# Discover
hookset probes --suite all
hookset models

# Rank / compare saved JSONL (including old MTP run-*.jsonl)
hookset rank --file results/run-....jsonl
hookset compare --dir results
```

Set `HOOKSET_MODELS=xai/grok-4,gpt-5.4-mini` in `.env` to pin the roster. `MTP_MODELS` is still honored.

## Suites

| Suite | What it is |
|-------|------------|
| `classic` | Exact original MTP probes (france / TechCorp / moon / control / targeted) |
| `extended` | More plants: numeric, year, unit, authority-vs-logs |
| `agentic` | Tool-use / verify-before-act / stale-memory / premature-sell |

Classic is the baseline for "benchmark against the original design."

## Agents, not just chat

```python
from hookset import CallableAdapter, HooksetRunner, Trace, TraceAdapter, load_probes, score_trace

# Any fn(prompt) -> str
runner = HooksetRunner([CallableAdapter("my-agent", my_agent.ask)])
print(runner.run(load_probes(suite="agentic")))

# Or dump steps from any stack and score them
trace = Trace.model_validate(json.load(open("trace.json")))
score = score_trace(probe, trace)   # hookset_step = first step that set the hook
```

## Project layout

```
hookset/
├── src/hookset/
│   ├── detect.py          # lexical + logprob + step hookset
│   ├── score.py           # TTA, resistance, HMS, MTP aliases
│   ├── adapters.py        # mock / litellm / callable / recorded traces
│   ├── catalog.py         # roster + env-key discovery
│   ├── runner.py
│   ├── compare.py
│   └── data/              # classic.json, agentic.json, extended.json, models.yaml
├── tests/                 # includes the original MTP assertion set
└── docs/
```

## Compatibility

Hookset JSONL includes MTP field names (`anchoring_latency`, `question_id`, `commitment_token_index`, `score`). `hookset rank` / `compare` can load parked MTP `run-*.jsonl` files.

Graph memory and the FastAPI server from the original README were never implemented and are not revived here.

## License

MIT
