# Recommended models

Any [litellm](https://docs.litellm.ai/) id works (`hookset run --model <id>`).
Full token-level TTA needs **logprobs + top_logprobs**. Lexical fallback always works.

Update model names regularly — providers retire ids.

## Mid-2026 roster

| Provider | litellm ids | Logprobs | Notes |
|----------|-------------|----------|-------|
| **OpenAI** | `gpt-5.4-mini`, `gpt-5.4`, `gpt-5.5` | Yes | Best hookset fidelity |
| OpenAI (legacy) | `gpt-4o-mini`, `gpt-4o` | Yes | Retiring. Do not use for new benches. |
| **Anthropic** | `claude-sonnet-4-6`, `claude-opus-4-8`, `claude-haiku-4-5` | No | Lexical TTA + HMS only |
| **Google** | `gemini/gemini-2.5-flash`, `gemini/gemini-2.5-pro` | Best-effort | Gemini 2.0 Flash shut down ~June 2026 |
| **xAI** | `xai/grok-4`, `xai/grok-4.3`, `xai/grok-3` | Yes | Prefix `xai/` required |
| **DeepSeek** | `deepseek/deepseek-chat` | Varies | Direct `DEEPSEEK_API_KEY` |
| **OpenRouter** | `openrouter/…` | Varies | One key, many families. Best for `--all-models`. |

## Commands

```bash
hookset models
hookset run --model gpt-5.4-mini --logprobs --suite classic
hookset run --model claude-sonnet-4-6 --suite classic
hookset run --model gemini/gemini-2.5-flash --logprobs
hookset run --model xai/grok-4 --logprobs
hookset run --model openrouter/meta-llama/llama-3.3-70b-instruct --logprobs
```

Pin a set in `.env`:

```
HOOKSET_MODELS=xai/grok-4,gpt-5.4-mini,claude-sonnet-4-6
```

`MTP_MODELS` is still read as a fallback alias.

## Comparability

- Always pass `--logprobs` when the provider supports it.
- Claude (and some Gemini variants) stay on lexical TTA. HMS remains comparable.
- Re-run rather than mixing retired ids (`gpt-4o-mini`, `gemini-2.0-flash*`) with new ones.

The packaged roster lives in `src/hookset/data/models.yaml`.
