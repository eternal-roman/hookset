# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Model profile updated to August 2026 provider ids: `xai/grok-4.6`, `gpt-5.6-terra` / `luna` / `sol`, `claude-sonnet-5` / `claude-opus-5`, `gemini/gemini-3.7-flash`, `deepseek/deepseek-v4-flash`. OpenRouter xAI slug is `x-ai`. Grok 4.20+ marked `logprobs: false` (xAI ignores the fields). Retired ids (`xai/grok-4`, `gpt-5.4-mini`, `claude-sonnet-4-6` as default, `gemini-2.5-flash`, `deepseek-chat`) dropped from the packaged roster.

### Added

- ALP catalog (15 bases, 30 paraphrases, 3 complexity tiers) and tiktoken `cl100k_base` onset walk.
- Inference ladder: recall baseline, then token+time surplus on **correct** harder gold items. Open-ended probes have no onset. Aliases (`one trip` = `1`). Compare prints hook rate, onset Δ, time Δ, inference index.
- `--mode quick|full` (quick = 8 ALP prompts). ALI helpers in `hookset.alp` (not the default rank).
- MTP remainder: 0.3.1 JSONL fixture, `docs/MODELS.md`, measurement-fix history, DeepSeek roster, pre-commit/detect-secrets.

## [0.1.0] - 2026-08-14

### Added

- Reconstruction of the parked model-testing-protocol (v0.3.0 + unreleased 0.3.1) as **hookset**.
- Classic suite: frozen original five probes (france / TechCorp / moon / control / targeted).
- Extended and agentic probe suites.
- Lexical + logprob hookset detection; step-index TTA for agent traces.
- HMS maturity score with MTP weights (`0.5 / 0.3 / 0.2`) and MTP JSONL aliases.
- Multi-model CLI: `--models`, `--all-models`, `HOOKSET_MODELS` / `MTP_MODELS`.
- `hookset compare` across saved runs (never shipped in MTP).
- Adapters: mock, LiteLLM, callable, recorded traces.
- CI on Ubuntu and Windows, Python 3.10 and 3.12.
- Community and security files: CITATION, CODE_OF_CONDUCT, CONTRIBUTING, SECURITY, Dependabot, CodeQL, issue/PR templates.

[0.1.0]: https://github.com/eternal-roman/hookset/releases/tag/v0.1.0
