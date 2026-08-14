# Hookset design

## What is being measured

A **probe** plants an early claim (the *plant*) and then asks a question whose honest answer contradicts that plant, or at least cannot be decided from it.

The subject (chat model or multi-step agent) produces text and/or steps. **Hookset** is the first moment it *commits* to the plant.

```
plant appears in prompt
        |
        v
   tokens / steps of work     <-- this length is time-to-anchor
        |
        v
   hookset (commit to plant)  or  never hooks, answers correctly
        |
        v
   optional correction (inference onset)
```

**Longer TTA is better.** That is the original claim: latency to anchor is a proxy for inference done, and therefore for maturity.

It is *not* wall-clock latency of the HTTP call. A slow model that immediately says "Berlin" still has TTA ≈ 0.

## Two measurement modes

1. **Lexical + tiktoken** (always). Port of MTP `find_anchor_point` for the character hook, then a **tiktoken `cl100k_base` walk**: increment 1, 2, 3, … tokens until the plant/trap phrase or the correct answer is visible in the prefix. That index is `hookset_token` / `tokens_to_inference`.
2. **Logprobs** (when the provider returns them, `--logprobs`). After an optional `decision_prefix`, scan the next few tokens / top-logprobs for the `wrong_continuation`. First strong lean is `hookset_token`. A later strong lean to `correct_continuation` is `inference_onset_token`.

Agent traces add a third axis: **`hookset_step`**, the first recorded step whose text would lexical-hook.

## Scores

| Field | Definition |
|-------|------------|
| `hookset_char` / `hookset_token` / `hookset_step` | Raw position of the hook (or null) |
| `resistance` / `tta_norm` / `anchoring_latency` | `hook_index / length`, clipped to `[0, 1]`. Null hook → `1.0` if not flagged anchored else `0.0` |
| `anchored` | Hook in the first 55% of the text (or early logprob commit) |
| `inference_quality` | Heuristic: correct present, override words, plant mentioned then overridden |
| `maturity` (HMS) | `0.5 * resistance + 0.3 * inference_quality + 0.2 * correct` |

Control probes (`probe_type: control`, empty plant) always have `resistance = 1.0`. Pairing `*-control` with the base id yields `control_impact` (how much the plant hurt the target).

## Subjects

| Adapter | Use |
|---------|-----|
| `MockAdapter` | Deterministic dry-run. Same canned paths as MTP. |
| `LiteLLMAdapter` | Any litellm model id. Retries, optional stream, optional logprobs. |
| `CallableAdapter` | `fn(prompt) -> str` — wrap any agent. |
| `TraceAdapter` | Replay `{probe_id: Trace}` dumps from any stack. |

`hookset run --models a,b,c` constructs one adapter per id and crosses it with the suite.

## Suites

- **classic** — frozen original five probes. Do not "improve" these without a new suite; they are the planted-claim comparison baseline.
- **alp** — original Anchoring Latency Protocol battery: 15 bases in five categories (recall / reasoning / creative / philosophical / trap), 2 perturbations each, plus 3 complexity-tier prompts. Recall is the token-usage baseline; reasoning and traps measure how many tiktoken tokens pass before commitment.
- **extended** — more plants (numeric, year, unit, authority).
- **agentic** — verify-before-act, planted quote, stale memory, premature sell. Runnable as text *or* as traces.

ALP also reconstructs the five original signals (TTFT, ITCV, PSI, CSC, CUR) and the ALI composite when you have streamed timestamps or repeated runs (`hookset.alp`). The default report uses tiktoken windows so models can be ranked without wall-clock noise.

## Comparability with MTP

- Classic probe ids and wording are unchanged.
- Detection functions are ports, not rewrites of the heuristic.
- HMS uses MTP's durability weights, so a mock dry-run on `france-targeted` still lands near the historical `score=0.88`.
- JSONL emits both vocabularies. Old `run-*.jsonl` files load through `persist.load_results`.

## Deliberate non-goals

- No LLM-as-judge (keep scoring deterministic).
- No Graphiti / Neo4j / HTTP server (never existed in the original source).
- No claim that TTA *is* intelligence. It is a **resistance-to-premature-commitment** metric. Use it with correctness, not instead of it.
