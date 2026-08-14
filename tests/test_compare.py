from hookset.compare import compare_models
from hookset.models import Probe
from hookset.score import score_response


def test_compare_ranks_higher_maturity_first():
    q = Probe(id="p", prompt="p", plant="Berlin is capital", correct="Paris")
    weak = score_response(q, "Berlin is capital, obviously.", model="fast-hook")
    strong = score_response(
        q,
        "The plant is wrong. Officially the capital is Paris.",
        model="slow-hook",
    )
    rows = compare_models([weak, strong])
    assert rows[0]["model"] == "slow-hook"
    assert rows[0]["maturity"] >= rows[1]["maturity"]
    assert {r["model"] for r in rows} == {"fast-hook", "slow-hook"}
