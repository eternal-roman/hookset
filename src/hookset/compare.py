"""Cross-model / cross-run comparison."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Sequence

from .models import Score
from .score import summarize


def by_model(results: Sequence[Score]) -> Dict[str, List[Score]]:
    grouped: Dict[str, List[Score]] = defaultdict(list)
    for r in results:
        grouped[r.model].append(r)
    return dict(grouped)


def compare_models(results: Sequence[Score]) -> List[Dict[str, Any]]:
    """One row per model, ranked by mean maturity (then mean resistance)."""
    rows: List[Dict[str, Any]] = []
    for model, group in by_model(results).items():
        summary = summarize(group)
        rows.append(
            {
                "model": model,
                "n": summary["n_probes"],
                "maturity": summary["avg_maturity"],
                "resistance": summary["avg_resistance"],
                "tta": summary["avg_tta"],
                "anchoring_rate": summary["anchoring_rate"],
                "correct": summary["correct_inference_rate"],
                "inference_quality": summary["avg_inference_quality"],
                "correction_rate": summary["correction_rate"],
                "logprobs": summary["logprobs_usage_rate"],
            }
        )
    rows.sort(key=lambda r: (r["maturity"], r["resistance"]), reverse=True)
    for i, row in enumerate(rows, 1):
        row["rank"] = i
    return rows
