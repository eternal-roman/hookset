import os

from hookset.catalog import get_available_models, get_default_model, load_roster, supports_logprobs


def test_roster_loads():
    roster = load_roster()
    assert len(roster) >= 5
    ids = {s.id for s in roster}
    assert "grok-4" in ids
    assert "gpt-5.4-mini" in ids


def test_mock_always_available(monkeypatch):
    for key in (
        "OPENROUTER_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "XAI_API_KEY",
        "GOOGLE_API_KEY",
        "HOOKSET_MODELS",
        "MTP_MODELS",
    ):
        monkeypatch.delenv(key, raising=False)
    models = get_available_models()
    assert "mock" in models
    assert get_default_model() == "mock"


def test_hookset_models_restricts(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "xai-real-not-placeholder-value")
    monkeypatch.setenv("HOOKSET_MODELS", "xai/grok-4")
    models = get_available_models()
    assert "xai/grok-4" in models
    assert get_default_model() == "xai/grok-4"


def test_placeholder_keys_ignored(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-...")
    monkeypatch.delenv("HOOKSET_MODELS", raising=False)
    monkeypatch.delenv("MTP_MODELS", raising=False)
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    models = get_available_models()
    assert models == ["mock"]


def test_supports_logprobs():
    assert supports_logprobs("mock") is True
    assert supports_logprobs("claude-sonnet-4-6") is False
    assert supports_logprobs("xai/grok-4") is True
