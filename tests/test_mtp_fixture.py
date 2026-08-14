"""Historical MTP 0.3.1 dry-run JSONL still loads and ranks."""

from pathlib import Path

from hookset.persist import load_results
from hookset.score import rank_results


FIXTURE = Path(__file__).parent / "fixtures" / "mtp-v0.3.1" / "run-france-targeted.jsonl"


def test_historical_mtp_jsonl_loads():
    loaded = load_results(FIXTURE)
    assert len(loaded) == 1
    row = loaded[0]
    assert row.probe_id == "france-targeted"
    assert row.model == "mock"
    assert row.resistance == 1.0
    assert row.correct_final is True
    assert row.inference_quality == 0.6
    ranked = rank_results(loaded)
    assert ranked[0]["score"] == 0.88
