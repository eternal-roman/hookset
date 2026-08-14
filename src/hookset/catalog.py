"""Model roster + env-key discovery.

Successor to the unreleased MTP 0.3.1 `get_available_models` / `MTP_MODELS`
work. A packaged `data/models.yaml` is the static roster; env keys decide
what you can actually call; HOOKSET_MODELS (or MTP_MODELS) restricts order.
"""

from __future__ import annotations

import os
from functools import lru_cache
from importlib.resources import files
from typing import List, Optional

import yaml
from dotenv import load_dotenv

from .models import ModelSpec

load_dotenv()

_PLACEHOLDERS = ("sk-or-...", "sk-...", "sk-ant-...", "xai-...")


def _key_present(name: str) -> bool:
    val = os.getenv(name, "") or ""
    if not val.strip():
        return False
    return not any(val.startswith(p) for p in _PLACEHOLDERS)


def _provider_for(litellm_id: str) -> str:
    lid = litellm_id.lower()
    if lid.startswith("openrouter/"):
        return "openrouter"
    if lid.startswith("xai/") or "grok" in lid:
        return "xai"
    if lid.startswith("claude") or lid.startswith("anthropic/"):
        return "anthropic"
    if lid.startswith("gemini") or lid.startswith("google/"):
        return "google"
    if lid.startswith("gpt") or lid.startswith("openai/"):
        return "openai"
    return "other"


@lru_cache(maxsize=1)
def load_roster() -> List[ModelSpec]:
    raw = files("hookset") / "data" / "models.yaml"
    data = yaml.safe_load(raw.read_text(encoding="utf-8")) or {}
    specs: List[ModelSpec] = []
    for item in data.get("models", []):
        spec = ModelSpec.model_validate(item)
        if not spec.provider:
            spec.provider = _provider_for(spec.litellm)
        specs.append(spec)
    return specs


def _reachable(spec: ModelSpec) -> bool:
    p = spec.provider or _provider_for(spec.litellm)
    if p == "openrouter":
        return _key_present("OPENROUTER_API_KEY")
    if p == "openai":
        return _key_present("OPENAI_API_KEY") or _key_present("OPENROUTER_API_KEY")
    if p == "anthropic":
        return _key_present("ANTHROPIC_API_KEY") or _key_present("OPENROUTER_API_KEY")
    if p == "xai":
        return _key_present("XAI_API_KEY") or _key_present("OPENROUTER_API_KEY")
    if p == "google":
        return _key_present("GOOGLE_API_KEY") or _key_present("OPENROUTER_API_KEY")
    return False


def explicit_model_list() -> List[str]:
    raw = os.getenv("HOOKSET_MODELS") or os.getenv("MTP_MODELS") or ""
    return [m.strip() for m in raw.split(",") if m.strip()]


def get_available_models() -> List[str]:
    """Models you can actually call, plus always-present `mock`."""
    available: List[str] = []
    if _key_present("OPENROUTER_API_KEY"):
        available.extend(
            [
                "openrouter/gpt-5.4-mini",
                "openrouter/anthropic/claude-sonnet-4-6",
                "openrouter/google/gemini-2.5-flash",
                "openrouter/xai/grok-4.3",
            ]
        )
    for spec in load_roster():
        if _reachable(spec) and spec.litellm not in available:
            available.append(spec.litellm)

    available.append("mock")

    explicit = explicit_model_list()
    if explicit:
        filtered = [m for m in explicit if m in available or m.startswith("mock")]
        if filtered:
            if "mock" not in filtered:
                filtered.append("mock")
            available = filtered

    seen = set()
    out: List[str] = []
    for m in available:
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out


def get_default_model() -> str:
    avail = get_available_models()
    explicit = explicit_model_list()
    if explicit and explicit[0] in avail and explicit[0] != "mock":
        return explicit[0]
    for pref in (
        "gpt-5.4-mini",
        "openrouter/gpt-5.4-mini",
        "xai/grok-4",
        "xai/grok-4.3",
        "gemini/gemini-2.5-flash",
    ):
        if pref in avail:
            return pref
    for m in avail:
        if m != "mock":
            return m
    return "mock"


def spec_for(model: str) -> Optional[ModelSpec]:
    for spec in load_roster():
        if spec.id == model or spec.litellm == model:
            return spec
    return None


def supports_logprobs(model: str) -> bool:
    spec = spec_for(model)
    if spec is not None:
        return spec.logprobs
    lid = model.lower()
    if lid.startswith("claude") or "anthropic" in lid:
        return False
    if lid.startswith("mock"):
        return True
    return True
