import json
from pathlib import Path

from hookset.cli import main
from hookset.persist import load_results, save_results
from hookset.probes import load_probes
from hookset.score import score_response


def test_cli_probes(capsys):
    main(["probes", "--suite", "classic"])
    out = capsys.readouterr().out
    assert "france-capital" in out
    assert "france-targeted" in out


def test_cli_models_json(capsys):
    main(["models", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert "available" in payload
    assert "mock" in payload["available"]


def test_cli_dry_run(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["run", "--dry-run", "--suite", "classic", "--probe", "france-capital-control"])
    out = capsys.readouterr().out
    assert "france-capital-control" in out
    runs = list((tmp_path / "results").glob("run-*.jsonl"))
    assert len(runs) == 1


def test_cli_rank_roundtrip(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    probe = load_probes("france-capital-control", suite="classic")[0]
    scored = score_response(probe, "The capital of France is Paris.", model="mock")
    path = save_results([scored], tmp_path / "results")
    main(["rank", "--file", str(path)])
    out = capsys.readouterr().out
    assert "france-capital-control" in out


def test_load_mtp_shaped_jsonl(tmp_path):
    p = tmp_path / "run-old.jsonl"
    p.write_text(
        json.dumps(
            {
                "question_id": "france-capital",
                "model": "gpt-4o-mini",
                "anchored": True,
                "correct_final_answer": False,
                "anchor_point": 0,
                "anchoring_latency": 0.05,
                "inference_quality": 0.1,
                "score": 0.145,
                "used_logprobs": False,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    loaded = load_results(p)
    assert len(loaded) == 1
    assert loaded[0].probe_id == "france-capital"
    assert loaded[0].resistance == 0.05
    assert loaded[0].correct_final is False
