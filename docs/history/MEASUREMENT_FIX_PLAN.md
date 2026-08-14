# Measurement Fix Plan (historical)

Ported from model-testing-protocol. Records the intent behind the logprobs +
targeted-probe work. Hookset implements the **corrected** direction.

Core goals:
- Move from pure lexical char search to token-level commitment using logprobs.
- Add `decision_prefix` / `wrong_continuation` for measurement at the critical generation step.
- Separate commitment timing from final correctness and inference quality.
- Add basic `inference_onset` detection.
- Preserve backward compatibility with lexical mode.

In Hookset: `detect.py` (`commitment_from_logprobs`, `inference_onset_from_logprobs`)
and `Score.resistance` (alias `anchoring_latency`).

Note: Earlier versions confused latency direction. That was corrected:
**early bad commitment = low resistance score.** Longer TTA is better.
