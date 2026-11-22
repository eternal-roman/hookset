# Lineage

Hookset is the successor of `model-testing-protocol` (MTP) v0.3.0 and its unreleased 0.3.1, rebuilt on 2026-08-14. MTP is archived on GitHub. New work belongs here.

The thesis is unchanged: a model that anchors on a planted claim before doing inference is less mature. **Longer time-to-anchor = more inference = better.**

## What came from MTP

- The classic probes (france / TechCorp / moon / control / targeted), unchanged.
- Lexical `find_anchor_point` and the logprob commitment and onset helpers (`detect.py`).
- HMS weights `0.5 / 0.3 / 0.2`, the dry-run mock and the JSONL field names.
- 0.3.1 model discovery, finished as `HOOKSET_MODELS`, `hookset models` and `--all-models`.
- A 0.3.1 mock JSONL fixture in `tests/fixtures/mtp-v0.3.1/`.

## The ALP catalog

The first Anchoring Latency Protocol was never committed, and its source is lost. Its implementation plan survived, and it gave us:

- The 15 base prompts in 5 categories (recall, novel reasoning, creative, philosophical, trap), verbatim.
- The ALI metrics and weights (TTFT 0.25, ITCV 0.20, PSI 0.25, CSC 0.15, CUR 0.15), still in `hookset.alp` but not the default rank.
- Quick mode = 8 prompts.

These were reconstructed rather than recovered: the 30 paraphrases (same meaning, new wording), the 3 complexity prompts (1-, 2- and 3-step integer arithmetic), and the tiktoken `cl100k_base` onset walk (the original used stream timestamps). The FastAPI UI and streaming providers were not rebuilt.

## The direction fix

MTP's first port computed `anchoring_latency = 1.0 - anchor_point / 300`, which scored *early* hooks *high*. MTP corrected this to `idx / n`. Hookset keeps the corrected direction (early bad commitment = low score) and names it TTA / resistance, with `anchoring_latency` as an alias.

## Never built

MTP's README listed `anchor-test compare` (now `hookset compare`), a `models.yaml` batch mode (now `--all-models`), and an optional graph store and FastAPI server. The last two are not revived.
