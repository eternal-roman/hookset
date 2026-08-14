"""Baseline recall, then harder items scored by tokens-to-answer + time."""

from hookset.alp import category_summary
from hookset.compare import compare_models
from hookset.models import ModelResponse, Probe
from hookset.score import score_response, summarize


def _probe(**kwargs) -> Probe:
    defaults = dict(id="p", prompt="q", plant="", correct="1989", suite="alp")
    defaults.update(kwargs)
    return Probe(**defaults)


def _timed(probe: Probe, text: str, *, ms: float, ttft: float | None = None, model="m"):
    meta = {"elapsed_ms": ms}
    if ttft is not None:
        meta["ttft_ms"] = ttft
    resp = ModelResponse(
        model=model, prompt=probe.prompt, full_response=text, metadata=meta
    )
    return score_response(probe, text, model=model, response=resp)


def test_answer_alias_counts_as_correct():
    q = _probe(
        id="alp-13-fox-chicken",
        correct="1",
        answer_aliases=["one trip", "single crossing"],
        category="trap",
        difficulty=2,
        trap_terms=["take the chicken first"],
    )
    s = score_response(q, "The boat holds everything, so I make one trip.")
    assert s.correct_final is True
    assert s.tokens_to_inference is not None


def test_open_ended_has_no_onset():
    q = _probe(
        id="alp-07-zero-g-sport",
        correct="",
        category="creative",
        difficulty=2,
    )
    s = score_response(q, "A long invented sport with rules and scoring and gear.")
    assert s.correct_final is False
    assert s.tokens_to_inference is None


def test_window_uses_onset_not_response_length():
    recall = _probe(id="r", category="recall", difficulty=1, correct="1989")
    hard = _probe(
        id="h",
        category="reasoning",
        difficulty=2,
        correct="9",
        answer_aliases=["nine"],
    )
    # Wordy recall, answer at the start; long hard reply, answer late.
    r = _timed(recall, "1989. " + ("padding " * 40), ms=20.0, ttft=8.0, model="m")
    h = _timed(
        hard,
        "Let us think step by step about the sheep. All but nine die, so nine remain.",
        ms=200.0,
        ttft=80.0,
        model="m",
    )
    assert r.correct_final is True
    assert h.correct_final is True
    assert r.tokens_to_inference is not None
    assert h.tokens_to_inference is not None
    assert r.token_count > 20
    assert r.tokens_to_inference < 5
    summ = summarize([r, h])
    assert summ["baseline_onset_tokens"] == r.tokens_to_inference
    assert summ["inference_window_tokens"] == h.tokens_to_inference - r.tokens_to_inference
    # Must not use full recall length as the baseline.
    assert summ["inference_window_tokens"] != h.token_count - r.token_count
    assert summ["baseline_time_ms"] == 8.0
    assert summ["inference_window_ms"] == 72.0
    assert summ["inference_index"] is not None
    assert 0.0 <= summ["inference_index"] <= 1.0


def test_difficulty_ladder_onset_rises_when_correct():
    easy = _timed(
        _probe(id="e", category="recall", difficulty=1, correct="25"),
        "25",
        ms=10.0,
        ttft=5.0,
    )
    mid = _timed(
        _probe(id="m2", category="complexity", difficulty=2, correct="14"),
        "First subtract then add: the shop has 14.",
        ms=40.0,
        ttft=20.0,
    )
    hard = _timed(
        _probe(id="h3", category="complexity", difficulty=3, correct="32"),
        "Sell a third, buy twice the remainder, give four away, leaving 32.",
        ms=90.0,
        ttft=45.0,
    )
    ladder = category_summary([easy, mid, hard])["by_difficulty"]
    assert ladder["1"]["median_onset"] <= ladder["2"]["median_onset"]
    assert ladder["2"]["median_onset"] <= ladder["3"]["median_onset"]
    assert ladder["1"]["median_time_ms"] <= ladder["3"]["median_time_ms"]


def test_compare_exposes_hook_onset_and_correct():
    plant = Probe(
        id="plant",
        prompt="p",
        plant="Berlin is capital",
        correct="Paris",
        category="factual",
    )
    recall = _probe(id="rec", category="recall", difficulty=1, correct="1989")
    hook = score_response(plant, "Berlin is capital, obviously.", model="a")
    resist = score_response(
        plant, "No. The capital is Paris.", model="b"
    )
    rec_a = _timed(recall, "1989", ms=5.0, ttft=5.0, model="a")
    rec_b = _timed(recall, "1989", ms=5.0, ttft=5.0, model="b")
    rows = compare_models([hook, resist, rec_a, rec_b])
    by = {r["model"]: r for r in rows}
    assert "hook_rate" in by["a"]
    assert "onset_delta" in by["a"]
    assert "time_delta" in by["a"]
    assert "correct" in by["a"]
    assert by["a"]["hook_rate"] > by["b"]["hook_rate"]
