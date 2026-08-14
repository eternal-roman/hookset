from hookset.alp import (
    QUICK_IDS,
    compute_ali,
    compute_csc,
    compute_cur,
    compute_itcv,
    compute_psi,
    compute_ttft,
    rouge_l,
)
from hookset.probes import load_probes
from hookset.runner import HooksetRunner
from hookset.score import score_response, summarize


def test_alp_catalog_has_five_categories_and_perturbations():
    probes = load_probes(suite="alp")
    ids = {p.id for p in probes}
    assert "alp-01-berlin-wall" in ids
    assert "alp-13-fox-chicken" in ids
    assert "alp-c3-shop-multistep" in ids
    cats = {p.category for p in probes}
    assert cats == {
        "recall",
        "reasoning",
        "creative",
        "philosophical",
        "trap",
        "complexity",
    }
    bases = [p for p in probes if p.role == "base"]
    assert len(bases) == 15
    perturbations = [p for p in probes if p.role == "perturbation"]
    assert len(perturbations) == 30
    assert all(p.parent_id for p in perturbations)


def test_alp_quick_mode_is_eight_prompts():
    probes = load_probes(suite="alp", mode="quick")
    ids = {p.id for p in probes}
    assert ids == QUICK_IDS
    assert len(probes) == 8


def test_alp_recall_is_baseline_fast_correct():
    probe = load_probes("alp-01-berlin-wall", suite="alp")[0]
    scored = score_response(probe, "1989.")
    assert scored.category == "recall"
    assert scored.correct_final is True
    assert scored.anchored is False
    assert scored.token_count is not None and scored.token_count >= 1
    assert scored.tokens_to_inference is not None


def test_alp_trap_hooks_classic_fox_chicken():
    probe = load_probes("alp-13-fox-chicken", suite="alp")[0]
    hooked = score_response(
        probe,
        "Take the chicken first, then the fox, bring the chicken back, then the grain.",
    )
    inferred = score_response(
        probe,
        "The boat already holds me and 3 items, so I only need 1 trip.",
    )
    assert hooked.anchored is True
    assert hooked.correct_final is False
    assert inferred.correct_final is True
    assert inferred.resistance >= hooked.resistance
    assert hooked.hookset_token is not None


def test_alp_dry_run_full_catalog():
    probes = load_probes(suite="alp")
    results = HooksetRunner.for_models(["mock"]).run(probes)
    assert len(results) == len(probes)
    summ = summarize(results)
    assert summ["n_questions"] == len(probes)
    assert "by_category" in summ
    assert "recall" in summ["by_category"]
    assert summ["baseline_avg_tokens"] is not None
    # Trap mock recites the classic puzzle — that is an early hook.
    fox = next(r for r in results if r.probe_id == "alp-13-fox-chicken")
    assert fox.anchored is True


def test_rouge_and_alp_metrics():
    assert rouge_l("the cat sat", "the cat sat") == 1.0
    assert rouge_l("aaa bbb", "ccc ddd") == 0.0
    assert compute_ttft([12.0, 20.0]) == 12.0
    assert compute_itcv([0, 10, 12, 14, 16, 40, 80, 120]) is not None
    psi = compute_psi("hello world", ["hello world", "hello there"])
    assert psi is not None and 0.0 <= psi <= 1.0
    slope = compute_csc([(1, 10.0), (2, 20.0), (3, 30.0)])
    assert slope is not None and slope > 0
    assert compute_cur(["same text", "same text"]) == 1.0
    ali = compute_ali(
        {
            "slow": {"ttft": 200.0, "itcv": 2.0, "psi": 0.8, "csc": 5.0, "cur": 0.2},
            "fast": {"ttft": 10.0, "itcv": 0.1, "psi": 0.1, "csc": 0.0, "cur": 0.9},
        }
    )
    assert ali["slow"] > ali["fast"]
