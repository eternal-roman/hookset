# ALP recovery (2026-08-14)

The first working Anchoring Latency Protocol was built in Antigravity (brain
`e314825a-65b9-422e-b88c-f36c9bd703ce`) as a gitignored folder:

`C:\Users\elamj\Dev\context-binding-protocol\anchoring-latency-protocol\`

It was never committed. By June 2026 the folder was only a `.venv` + `.env` and
was deleted as local cleanup. The conversation protobuf is encrypted. What
survived is the implementation plan, walkthrough, and first-run rankings.

## Recovered intact

- Thesis: slow commitment = inference; fast commitment = recall / template hook.
- 15 base prompts in 5 categories (recall, novel reasoning, creative,
  philosophical, adversarial/trap), verbatim from `implementation_plan.md`.
- 2 perturbation slots per base (30). Exact historical paraphrases were not
  saved; current paraphrases keep the same semantics.
- 3 complexity-tier prompts for CSC (exact originals not saved; reconstructed
  as 1-/2-/3-step integer arithmetic).
- Five metrics and ALI weights: TTFT 0.25, ITCV 0.20, PSI 0.25, CSC 0.15, CUR 0.15.
- Quick mode = 8 prompts (one per category + 3 complexity).
- First live ranking (wall-clock TTFT era): Grok 3 Mini ALI 0.818, Claude Sonnet 4
  0.342, Grok 3 0.004.

## Not recovered

- `server.py`, `static/index.html` (FastAPI glassmorphism UI).
- `providers.py` streaming implementation.
- Exact perturbation strings and complexity wording.
- tiktoken was **not** in the ALP plan (that used stream timestamps). The user
  requirement to count with tiktoken is restored here as `cl100k_base`, the
  same encoding CBP's comparison_test used.

## Correction applied

Hookset keeps planted-claim HMS for `classic` / `extended` / `agentic`.
Suite `alp` is the original question catalog. Token position is a tiktoken
walk, not `chars/4`.
