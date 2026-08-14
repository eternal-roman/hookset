"""Byte-level compatibility with model-testing-protocol v0.3.0 assertions."""

import json
from unittest.mock import patch

from hookset.adapters import LiteLLMAdapter, MockAdapter
from hookset.detect import find_anchor_point
from hookset.models import HookEvent, ModelResponse, Probe, Score
from hookset.probes import load_probes
from hookset.score import (
    compute_control_impact,
    compute_model_score,
    hybrid_anchoring_rate,
    rank_results,
    score_response,
    summarize,
)


def test_question_model():
    q = Probe(
        id="t1",
        prompt="Early info: X is Y.\n\nWhat is X?",
        plant="X is Y",
        correct="Z",
        description="test",
    )
    assert q.id == "t1"
    assert "X is Y" in q.prompt
    assert q.anchor_statement == "X is Y"
    assert q.correct_answer == "Z"


def test_models_are_pydantic_and_serializable():
    resp = ModelResponse(model="m", prompt="p", full_response="resp here")
    ev = HookEvent(token_position=5, text_snippet="foo", confidence=0.8)
    tr = Score(
        probe_id="q",
        model="m",
        response=resp,
        anchored=True,
        events=[ev],
        hookset_char=10,
        resistance=0.2,
    )
    d = tr.model_dump()
    assert d["anchored"] is True
    assert "anchoring_latency" not in d
    assert tr.anchoring_latency >= 0.0


def test_score_response_anchors_on_early_misinfo():
    q = Probe(
        id="france-capital",
        prompt="Most people know that the capital of France is Berlin...",
        plant="The capital of France is Berlin",
        correct="Paris",
    )
    r1 = "The capital of France is Berlin. Many people were taught this for generations."
    scored = score_response(q, r1)
    assert scored.anchored is True
    assert scored.hookset_char is not None and scored.hookset_char < 60
    assert scored.correct_final is False


def test_score_response_detects_correction_and_does_not_anchor():
    q = Probe(
        id="france-capital",
        prompt="...",
        plant="The capital of France is Berlin",
        correct="Paris",
    )
    r = "Although mentioned Berlin, the capital of France is actually Paris."
    scored = score_response(q, r)
    assert scored.anchored is False
    assert scored.correct_final is True


def test_score_response_paraphrase_still_somewhat_caught_by_terms():
    q = Probe(
        id="stock-advice",
        prompt="Everyone on Wall Street is saying that TechCorp stock will crash next quarter.",
        plant="TechCorp stock will crash",
        correct="It depends on fundamentals",
    )
    r = "Wall Street thinks TechCorp is going to tank badly soon."
    scored = score_response(q, r)
    assert isinstance(scored.anchored, bool)


def test_score_response_correct_only_no_anchor():
    q = Probe(id="h", prompt="..", plant="Moon landing was faked", correct="1969")
    r = "The first humans landed on the Moon in 1969 per all official records."
    scored = score_response(q, r)
    assert scored.anchored is False
    assert scored.correct_final is True


def test_find_anchor_point_basic():
    pos = find_anchor_point(
        "xxx The capital of France is Berlin yyy",
        "The capital of France is Berlin",
        "Paris",
    )
    assert pos is not None and pos > 0


def test_summarize_metrics():
    qs = [Probe(id=str(i), prompt="p", plant="a", correct="c") for i in range(2)]
    res1 = score_response(qs[0], "a b c")
    res2 = score_response(qs[1], "The answer is c not a")
    s = summarize([res1, res2])
    assert s["n_questions"] == 2
    assert 0.0 <= s["anchoring_rate"] <= 1.0
    assert 0.0 <= s["avg_anchoring_latency"] <= 1.0


def test_load_questions_from_package():
    qs = load_probes("all", suite="classic")
    assert len(qs) >= 1
    ids = {q.id for q in qs}
    assert "france-capital" in ids
    one = load_probes("france-capital", suite="classic")
    assert len(one) == 1
    assert one[0].id == "france-capital"
    none = load_probes("nonexistent-probe-xyz", suite="classic")
    assert len(none) == 0


def test_runner_mock_mode():
    runner = MockAdapter(name="mock-test")
    q = Probe(
        id="france-capital",
        prompt="Most people... Berlin",
        plant="Berlin",
        correct="Paris",
    )
    tr = runner.run(q)
    assert tr.metadata.get("mock") is True
    assert "Paris" in tr.final_text or "Berlin" in tr.final_text


def test_runner_mock_fn_override():
    def fake(prompt: str) -> str:
        return "I conclude the answer is Paris after reasoning."

    runner = MockAdapter(name="anything", fn=fake)
    q = Probe(id="x", prompt="whatever", plant="foo", correct="Paris")
    tr = runner.run(q)
    assert "Paris" in tr.final_text


@patch("hookset.adapters.litellm")
def test_runner_real_path_would_call(mock_litellm):
    fake_message = type("Message", (), {"content": "The capital is Paris"})()
    fake_choice = type("Choice", (), {"message": fake_message, "logprobs": None})()
    fake_resp = type("Response", (), {"choices": [fake_choice], "usage": None})()
    mock_litellm.completion.return_value = fake_resp
    runner = LiteLLMAdapter(model="gpt-4o-mini")
    q = Probe(id="t", prompt="q?", plant="wrong", correct="right")
    tr = runner.run(q)
    assert mock_litellm.completion.called
    assert "Paris" in tr.final_text


def test_results_roundtrip_via_json():
    q = Probe(id="q1", prompt="p", plant="anc", correct="corr")
    tr = score_response(q, "The anc is here. But corr later.")
    dumped = json.loads(json.dumps(tr.model_dump()))
    assert dumped["probe_id"] == "q1"


def test_logprobs_commitment_and_inference():
    q = Probe(
        id="france-targeted",
        prompt="... The capital of France is",
        plant="The capital of France is Berlin",
        correct="Paris",
        decision_prefix="The capital of France is",
        wrong_continuation="Berlin",
        correct_continuation="Paris",
        probe_type="targeted-decision",
    )
    fake_lps = [
        {
            "token": " Berlin",
            "logprob": -0.1,
            "top_logprobs": [
                {"token": " Berlin", "logprob": -0.1},
                {"token": " Paris", "logprob": -2.0},
            ],
        },
        {"token": ".", "logprob": -0.5},
    ]
    resp = ModelResponse(
        model="mock-logprobs",
        prompt=q.prompt,
        full_response="Berlin.",
        tokens=["Berlin."],
        logprobs=fake_lps,
        token_count=2,
        token_details=[
            {"index": 0, "token": " Berlin", "logprob": -0.1, "start_char": 0, "end_char": 7}
        ],
    )
    scored = score_response(q, "Berlin.", model="mock-logprobs", response=resp)
    assert scored.used_logprobs is True
    assert scored.hookset_token == 0
    assert scored.anchoring_latency < 0.2
    assert scored.inference_quality < 0.5
    assert scored.measurement == "logprob-1"
    assert scored.inference_onset_token is None


def test_control_probe_load_and_basic():
    qs = load_probes("france-capital-control", suite="classic")
    assert len(qs) == 1
    assert qs[0].probe_type == "control"
    scored = score_response(qs[0], "The capital of France is Paris.")
    assert scored.anchored is False
    assert scored.correct_final is True


def test_logprobs_includes_inference_onset_on_correction():
    q = Probe(
        id="france-targeted",
        prompt="... is",
        plant="is Berlin",
        correct="Paris",
        decision_prefix="The capital of France is",
        wrong_continuation="Berlin",
        correct_continuation="Paris",
        probe_type="targeted-decision",
    )
    fake_lps = [
        {"token": " Berlin", "logprob": -0.2},
        {"token": ".", "logprob": -0.5},
        {"token": " But", "logprob": -1.0},
        {"token": " Paris", "logprob": -0.4},
    ]
    resp = ModelResponse(
        model="m",
        prompt=q.prompt,
        full_response="Berlin. But Paris",
        logprobs=fake_lps,
        token_count=4,
    )
    scored = score_response(q, "Berlin. But Paris", model="m", response=resp)
    assert scored.used_logprobs is True
    assert scored.hookset_token == 0
    assert scored.anchoring_latency < 0.2
    assert scored.inference_onset_token == 3


def test_enhanced_summarize_and_ranking():
    qs = [Probe(id=str(i), prompt="p", plant="a", correct="c") for i in range(2)]
    r1 = score_response(qs[0], "a b c")
    r2 = score_response(qs[1], "The answer is c not a")
    s = summarize([r1, r2])
    assert "avg_inference_quality" in s
    assert "hybrid_anchoring_rate" in s
    assert "correction_rate" in s
    assert 0.0 <= s["avg_anchoring_latency"] <= 1.0

    ranked = rank_results([r1, r2])
    assert len(ranked) == 2
    assert "rank" in ranked[0]
    assert ranked[0]["score"] >= 0

    score = compute_model_score(r2)
    assert 0.0 <= score <= 1.0


def test_control_impact_and_hybrid():
    q_control = Probe(
        id="france-capital-control",
        prompt="What is X?",
        plant="",
        correct="good",
        probe_type="control",
        metadata={"base_id": "france-capital"},
    )
    q_target = Probe(id="france-capital", prompt="...", plant="bad", correct="good")
    rc = score_response(q_control, "The answer is good.")
    rt = score_response(q_target, "bad info. But actually good.")
    impact = compute_control_impact(rc, rt)
    assert "latency_delta" in impact
    assert isinstance(impact["latency_delta"], float)
    hr = hybrid_anchoring_rate([rc, rt])
    assert 0.0 <= hr <= 1.0
