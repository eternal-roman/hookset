"""JSONL run logs + summary / report sidecars. MTP-compatible field names."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .models import ModelResponse, Score
from .score import maturity_score, summarize


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def save_results(results: Sequence[Score], out_dir: Path = Path("results")) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = utc_stamp()
    out_path = out_dir / f"run-{ts}.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r.model_dump_report(), ensure_ascii=False) + "\n")
    summary = summarize(results)
    with (out_dir / "last_summary.json").open("w", encoding="utf-8") as f:
        json.dump({"timestamp": ts, "summary": summary}, f, indent=2)
    return out_path


def save_report(
    results: Sequence[Score],
    ranked: List[Dict[str, Any]],
    out_dir: Path = Path("results"),
    ts: Optional[str] = None,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = ts or utc_stamp()
    path = out_dir / f"report-{ts}.json"
    payload = {"timestamp": ts, "summary": summarize(results), "ranked": ranked}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _score_from_record(data: Dict[str, Any]) -> Score:
    """Rebuild a Score from hookset JSONL or MTP TestResult JSONL."""
    resp = None
    raw_resp = data.get("response")
    if isinstance(raw_resp, dict) and raw_resp.get("full_response") is not None:
        resp = ModelResponse.model_validate(raw_resp)
    resistance = data.get("resistance")
    if resistance is None:
        resistance = data.get("anchoring_latency")
    if resistance is None:
        resistance = 1.0
    correct = bool(data.get("correct_final", data.get("correct_final_answer", False)))
    iq = float(data.get("inference_quality") or 0.0)
    maturity = data.get("maturity", data.get("score"))
    if maturity is None:
        maturity = maturity_score(float(resistance), iq, correct)
    return Score(
        probe_id=data.get("probe_id") or data.get("question_id") or "unknown",
        model=data.get("model") or "unknown",
        anchored=bool(data.get("anchored", False)),
        correct_final=correct,
        hookset_char=data.get("hookset_char", data.get("anchor_point")),
        hookset_token=data.get("hookset_token", data.get("commitment_token_index")),
        hookset_step=data.get("hookset_step"),
        tta_norm=float(data.get("tta_norm", resistance)),
        resistance=float(resistance),
        inference_quality=iq,
        inference_onset_token=data.get(
            "inference_onset_token", data.get("inference_onset_token_index")
        ),
        used_logprobs=bool(data.get("used_logprobs", False)),
        commitment_strength=data.get("commitment_strength"),
        maturity=float(maturity),
        measurement=data.get("measurement") or data.get("measurement_version") or "lexical-1",
        notes=data.get("notes") or "",
        response=resp,
        control_impact=data.get("control_impact"),
    )


def load_results(path: Optional[Path] = None, directory: Path = Path("results")) -> List[Score]:
    if path is None:
        runs = sorted(directory.glob("run-*.jsonl"))
        if not runs:
            return []
        path = runs[-1]
    results: List[Score] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            results.append(_score_from_record(json.loads(line)))
    return results
