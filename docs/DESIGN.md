# Hookset design

Two complementary measurements, one catalog of questions.

**Planted-claim TTA** (classic / extended / agentic): how late the subject commits to a false plant. Token position, not HTTP wait. A slow model that immediately says “Berlin” still has TTA ≈ 0.

**ALP ladder** (suite `alp`): recall first (baseline), then harder gold items. Extra tokens-to-answer and extra time-to-infer, only when the answer is correct, is evidence of inference. Open-ended items have no gold string and do not enter the window.

Longer resistance to a *bad* hook is better. More work than recall on a *hard correct* item is better. Neither number is intelligence.

```
plant or trap appears
        |
        v
   tokens / ms of work
        |
        v
   hook (commit to plant/template)   or   gold answer (onset)
        |
        v
   optional correction
```

## Detection

1. **Lexical + tiktoken** (always). `find_anchor_point` for the character hook. Then a `cl100k_base` walk: tokens 1, 2, 3, … until a plant/trap phrase or a gold answer (plus aliases such as `one trip` = `1`) is visible. That index is `hookset_token` / `tokens_to_inference`.
2. **Logprobs** (`--logprobs`, when the provider returns them). First strong lean to `wrong_continuation` is the hook; a later lean to `correct_continuation` is onset.
3. **Steps.** `hookset_step` is the first recorded action that would lexical-hook.

A plant mention that is then overridden (`but` / `actually` + the correct term) is not a hook.

## Scores

| Field | Meaning |
|-------|---------|
| `resistance` / TTA / `anchoring_latency` | Hook index / length in `[0, 1]`. No hook → `1.0`. Immediate hook → `0`. |
| `anchored` | Hook in the first 55% of the text (or early logprob commit) |
| `tokens_to_inference` | Tiktoken index of the gold answer. Null if the probe has no gold string |
| `time_to_infer_ms` | `ttft_ms` if `--stream`, else call `elapsed_ms` |
| `inference_quality` | Heuristic: correct present, override words |
| HMS | `0.5·resistance + 0.3·quality + 0.2·correct` — planted-claim rank, MTP-compatible |

ALP report (not HMS):

1. Baseline = median onset and time on **correct recall**.
2. Window = median onset/time on **correct** reasoning / trap / complexity, minus baseline. Not response length.
3. `inference_index` = mean of clipped surplus ratios (tokens and time). Mock clocks are ~0, so the index is tokens-only.
4. `hookset compare` prints hook rate, onset Δ, time Δ, correct, inference index.

Control probes (empty plant) have resistance `1.0`. `*-control` pairs yield `control_impact`.

## Suites

| Suite | Role |
|-------|------|
| `classic` | Frozen five plants. Do not rewrite. |
| `alp` | 15 bases (recall / reasoning / creative / philosophical / trap), 30 paraphrases, 3 complexity tiers. `--mode quick` = 8 prompts. |
| `extended` | Numeric, year, unit, authority plants |
| `agentic` | Verify-before-act, planted quote, stale memory, premature sell |

`hookset.alp` still holds the old ALI helpers (TTFT, ITCV, PSI, CSC, CUR). They are not the default rank.

## Subjects

Mock (dry-run), LiteLLM, `fn(prompt) -> str`, recorded traces. `hookset run --models a,b,c` crosses each with the suite.

## Comparability

Classic ids and wording are unchanged. HMS weights match MTP, so mock `france-targeted` is still about **0.88**. JSONL keeps MTP field names.

## Non-goals

No LLM-as-judge. No graph store or HTTP UI. No claim that TTA is intelligence.
