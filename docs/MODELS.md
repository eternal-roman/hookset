# Recommended models

Any [litellm](https://docs.litellm.ai/) id works (`hookset run --model <id>`).
Full token-level TTA needs **logprobs + top_logprobs**. Lexical fallback always works.

Update model names regularly — providers retire ids. This page matches the packaged roster as of **2026-08-14**.

## August 2026 roster

| Provider | litellm ids | Logprobs | Notes |
|----------|-------------|----------|-------|
| **OpenAI** | `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-5.6-sol` | Yes | Terra is the balanced default. `gpt-5.6` aliases Sol. |
| OpenAI (legacy) | `gpt-5.5`, `gpt-5.4-mini`, `gpt-4o-mini` | Yes | Retired / retiring. Do not use for new benches. |
| **Anthropic** | `claude-sonnet-5`, `claude-opus-5`, `claude-fable-5` | No | Lexical TTA + HMS only. Haiku: `claude-haiku-4-5`. |
| Anthropic (legacy) | `claude-sonnet-4-6`, `claude-opus-4-8` | No | Still live; migrate new work to the 5-series. |
| **Google** | `gemini/gemini-3.7-flash`, `gemini/gemini-3.5-flash` | Best-effort | 3.7 is current Flash. Gemini 2.5 retires ~Oct 2026. |
| **xAI** | `xai/grok-4.6`, `xai/grok-4.5`, `xai/grok-4.3` | 4.3 only | Prefix `xai/` required. **logprobs unsupported on grok-4.20 and newer** (silently ignored). |
| **DeepSeek** | `deepseek/deepseek-v4-flash`, `deepseek/deepseek-v4-pro` | Varies | `deepseek-chat` / `deepseek-reasoner` retired 2026-07-24. |
| **OpenRouter** | `openrouter/x-ai/grok-4.6`, `openrouter/openai/gpt-5.6-terra`, `openrouter/anthropic/claude-sonnet-5`, `openrouter/google/gemini-3.7-flash` | Varies | One key, many families. OpenRouter's xAI slug is `x-ai`, not `xai`. |

## Commands

```bash
hookset models
hookset run --model gpt-5.6-terra --logprobs --suite classic
hookset run --model claude-sonnet-5 --suite classic
hookset run --model gemini/gemini-3.7-flash --logprobs
hookset run --model xai/grok-4.6 --suite classic
hookset run --model openrouter/x-ai/grok-4.6 --suite classic
```

Pin a set in `.env`:

```
HOOKSET_MODELS=xai/grok-4.6,gpt-5.6-terra,claude-sonnet-5
```

`MTP_MODELS` is still read as a fallback alias.

## Comparability

- Always pass `--logprobs` when the provider supports it.
- Claude, and Grok 4.20+, stay on lexical TTA. HMS remains comparable.
- Re-run rather than mixing retired ids (`gpt-4o-mini`, `gpt-5.4-mini`, `gemini-2.0-flash*`, `gemini-2.5-flash*`, `xai/grok-4`, `deepseek/deepseek-chat`) with new ones.

The packaged roster lives in `src/hookset/data/models.yaml`.
