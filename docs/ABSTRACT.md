# Abstract

**Hookset: time-to-anchor as a maturity metric for language models and agents**

Language-model evaluations typically score *what* a system concludes. They rarely score *when* it committed. We observe that premature commitment to an early, planted claim — a *hookset* — is a distinct failure from final incorrectness: a subject can recover, or it can never hook at all. Hookset measures **time-to-anchor (TTA)**, the normalized position of first commitment to that plant, as a proxy for inference actually performed.

A probe plants a claim (fact, consensus, authority, stale memory, or tool result) and then asks a question whose honest answer contradicts the plant or cannot be decided from it. Detection is deterministic. Lexical search (distinctive plant prefix or key terms, suppressed by early correction or an override marker plus the correct term) is always available. When a provider returns log-probabilities, commitment is read from the first strong lean toward the declared wrong continuation after an optional decision prefix; a later strong lean toward the correct continuation is *inference onset*. Multi-step agents are scored at step granularity: `hookset_step` is the first recorded action whose text would lexical-hook.

Scores are oriented so that **longer TTA is better**. Resistance (alias `anchoring_latency` from the predecessor protocol) is `hook_index / length`, clipped to `[0, 1]`, or `1.0` if the plant is never hooked. The Hookset Maturity Score is

```
HMS = 0.5 · resistance + 0.3 · inference_quality + 0.2 · correct
```

The weights are inherited from model-testing-protocol v0.3.0 so new runs remain comparable to historical JSONL. Control probes (empty plant) isolate the cost of the plant via paired `control_impact`.

The classic suite freezes the original five probes. Extended and agentic suites add numeric, authority, and tool-use plants. Subjects are interchangeable adapters: mock, LiteLLM completions, callables, and recorded traces. The metric does not claim to be intelligence. It is resistance to premature commitment, and it is meant to be read *with* correctness, not instead of it.

**Keywords:** time-to-anchor, anchoring bias, LLM evaluation, agent traces, premature commitment, log-probabilities
