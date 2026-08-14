"""Anchoring Latency Protocol metrics recovered from Antigravity session e314825a.

Original runtime (gitignored under context-binding-protocol/anchoring-latency-protocol/)
measured five signals and a composite ALI. Source files were never committed;
this is a faithful reconstruction of the plan + walkthrough that did survive.

Token counts use tiktoken (cl100k_base), not wall-clock, as the primary axis:
walk tokens until a commitment or the correct answer is implied.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable, Sequence
from typing import Any

from .models import Score

# Walkthrough "quick" set: one prompt per category + three complexity tiers.
QUICK_IDS = frozenset(
    {
        "alp-01-berlin-wall",
        "alp-04-sheep",
        "alp-07-zero-g-sport",
        "alp-10-math-discovered",
        "alp-13-fox-chicken",
        "alp-c1-add",
        "alp-c2-shop",
        "alp-c3-shop-multistep",
    }
)

# Original ALI weights (implementation_plan.md).
ALI_WEIGHTS = {
    "ttft": 0.25,
    "itcv": 0.20,
    "psi": 0.25,
    "csc": 0.15,
    "cur": 0.15,
}

REASONING_CATEGORIES = frozenset(
    {"reasoning", "creative", "philosophical", "trap", "complexity"}
)
# Open-ended items have no gold string; they do not enter the onset window.
WINDOW_CATEGORIES = frozenset({"reasoning", "trap", "complexity"})


def rouge_l(a: str, b: str) -> float:
    """Word-level ROUGE-L F1. No extra dependency."""
    wa = (a or "").lower().split()
    wb = (b or "").lower().split()
    if not wa or not wb:
        return 0.0
    n, m = len(wa), len(wb)
    prev = [0] * (m + 1)
    for i in range(1, n + 1):
        cur = [0] * (m + 1)
        for j in range(1, m + 1):
            if wa[i - 1] == wb[j - 1]:
                cur[j] = prev[j - 1] + 1
            else:
                cur[j] = max(prev[j], cur[j - 1])
        prev = cur
    lcs = prev[m]
    prec = lcs / m
    rec = lcs / n
    if prec + rec == 0:
        return 0.0
    return (2 * prec * rec) / (prec + rec)


def compute_ttft(timestamps_ms: Sequence[float]) -> float | None:
    """Time-to-first-token in ms. First timestamp is the first visible token."""
    if not timestamps_ms:
        return None
    return float(timestamps_ms[0])


def compute_itcv(timestamps_ms: Sequence[float]) -> float | None:
    """Early vs late inter-token cadence variance (coefficient of variation).

    Plan: CV of first 15 deltas vs last 15 of a 50-token window.
    Returns early_cv / max(late_cv, eps). Higher = still searching early.
    """
    if len(timestamps_ms) < 4:
        return None
    deltas = [
        max(0.0, timestamps_ms[i] - timestamps_ms[i - 1])
        for i in range(1, len(timestamps_ms))
    ]
    window = deltas[:50]
    if len(window) < 4:
        return None
    mid = max(1, len(window) // 2)
    early = window[: min(15, mid)]
    late = window[-min(15, len(window) - mid) :] or window[-1:]

    def _cv(xs: Sequence[float]) -> float:
        if not xs:
            return 0.0
        mean = sum(xs) / len(xs)
        if mean <= 1e-9:
            return 0.0
        var = sum((x - mean) ** 2 for x in xs) / len(xs)
        return math.sqrt(var) / mean

    late_cv = _cv(late)
    early_cv = _cv(early)
    return early_cv / max(late_cv, 1e-6)


def compute_psi(base: str, perturbations: Sequence[str]) -> float | None:
    """1 - mean ROUGE-L vs perturbations. Higher = more framing-sensitive."""
    if not perturbations:
        return None
    sims = [rouge_l(base, p) for p in perturbations]
    return 1.0 - (sum(sims) / len(sims))


def compute_csc(pairs: Sequence[tuple[int, float]]) -> float | None:
    """Slope of (complexity, token-or-ttft). Positive = harder → more work."""
    if len(pairs) < 2:
        return None
    xs = [float(c) for c, _ in pairs]
    ys = [float(v) for _, v in pairs]
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    if den <= 1e-12:
        return 0.0
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den


def compute_cur(responses: Sequence[str]) -> float | None:
    """Mean pairwise ROUGE-L. Lower = less default-anchored."""
    if len(responses) < 2:
        return None
    sims: list[float] = []
    for i in range(len(responses)):
        for j in range(i + 1, len(responses)):
            sims.append(rouge_l(responses[i], responses[j]))
    return sum(sims) / len(sims) if sims else None


def _minmax(values: dict[str, float | None], invert: bool = False) -> dict[str, float]:
    present = {k: v for k, v in values.items() if v is not None}
    if not present:
        return {k: 0.0 for k in values}
    lo = min(present.values())
    hi = max(present.values())
    out: dict[str, float] = {}
    for k, v in values.items():
        if v is None:
            out[k] = 0.0
            continue
        if hi - lo < 1e-12:
            norm = 0.5
        else:
            norm = (v - lo) / (hi - lo)
        out[k] = 1.0 - norm if invert else norm
    return out


def compute_ali(per_model: dict[str, dict[str, float | None]]) -> dict[str, float]:
    """Min-max ALI across models. Higher = more deliberation.

    Expected keys per model: ttft, itcv, psi, csc, cur.
    PSI/CUR are inverted (high similarity = more anchored).
    """
    if not per_model:
        return {}
    keys = ("ttft", "itcv", "psi", "csc", "cur")
    invert = {"psi": False, "cur": True, "ttft": False, "itcv": False, "csc": False}
    # PSI in this module is already 1-similarity (higher=better). CUR is similarity (invert).
    columns: dict[str, dict[str, float | None]] = {k: {} for k in keys}
    for model, metrics in per_model.items():
        for k in keys:
            columns[k][model] = metrics.get(k)
    norms = {k: _minmax(columns[k], invert=invert[k]) for k in keys}
    ali: dict[str, float] = {}
    for model in per_model:
        score = 0.0
        for k in keys:
            score += ALI_WEIGHTS[k] * norms[k][model]
        ali[model] = round(min(1.0, max(0.0, score)), 3)
    return ali


def _median(vals: list[float]) -> float | None:
    if not vals:
        return None
    s = sorted(vals)
    mid = len(s) // 2
    if len(s) % 2:
        return float(s[mid])
    return (s[mid - 1] + s[mid]) / 2.0


def _surplus_ratio(value: float | None, baseline: float | None) -> float | None:
    if value is None or baseline is None:
        return None
    return max(0.0, float(value) - float(baseline)) / max(float(baseline), 1.0)


def _combo(token_ratio: float | None, time_ratio: float | None) -> float | None:
    """0–1 evidence that harder items took more tokens and/or more time than recall."""
    parts = []
    if token_ratio is not None:
        parts.append(min(token_ratio, 4.0) / 4.0)
    if time_ratio is not None:
        parts.append(min(time_ratio, 4.0) / 4.0)
    if not parts:
        return None
    return round(sum(parts) / len(parts), 3)


def category_summary(results: Sequence[Score]) -> dict[str, Any]:
    """Recall baseline, then harder gold items as token+time surplus."""
    buckets: dict[str, list[Score]] = defaultdict(list)
    for r in results:
        cat = r.category or "uncategorized"
        buckets[cat].append(r)

    def _avg(xs: Iterable[float]) -> float | None:
        vals = list(xs)
        if not vals:
            return None
        return round(sum(vals) / len(vals), 3)

    by_cat: dict[str, Any] = {}
    for cat, group in sorted(buckets.items()):
        tokens = [r.token_count for r in group if r.token_count]
        to_inf = [
            r.tokens_to_inference
            for r in group
            if r.correct_final and r.tokens_to_inference is not None
        ]
        by_cat[cat] = {
            "n": len(group),
            "avg_tokens": _avg(float(t) for t in tokens) if tokens else None,
            "avg_tokens_to_inference": _avg(float(t) for t in to_inf) if to_inf else None,
            "avg_tta": _avg(r.resistance for r in group),
            "correct_rate": round(
                sum(1 for r in group if r.correct_final) / len(group), 3
            ),
            "anchoring_rate": round(sum(1 for r in group if r.anchored) / len(group), 3),
        }

    def _onsets(rows: list[Score]) -> list[float]:
        return [
            float(r.tokens_to_inference)
            for r in rows
            if r.correct_final and r.tokens_to_inference is not None
        ]

    def _times(rows: list[Score]) -> list[float]:
        return [
            float(r.time_to_infer_ms)
            for r in rows
            if r.correct_final and r.time_to_infer_ms is not None
        ]

    recall = [r for r in results if r.category == "recall"]
    harder = [r for r in results if r.category in WINDOW_CATEGORIES]
    base_onset = _median(_onsets(recall))
    hard_onset = _median(_onsets(harder))
    base_ms = _median(_times(recall))
    hard_ms = _median(_times(harder))
    window_tok = (
        round(hard_onset - base_onset, 3)
        if base_onset is not None and hard_onset is not None
        else None
    )
    window_ms = (
        round(hard_ms - base_ms, 3) if base_ms is not None and hard_ms is not None else None
    )
    if base_ms is not None:
        base_ms = round(base_ms, 3)
    if hard_ms is not None:
        hard_ms = round(hard_ms, 3)
    index = _combo(_surplus_ratio(hard_onset, base_onset), _surplus_ratio(hard_ms, base_ms))

    by_diff: dict[str, Any] = {}
    diff_buckets: dict[int, list[Score]] = defaultdict(list)
    for r in results:
        if r.correct_final and r.tokens_to_inference is not None:
            diff_buckets[int(r.difficulty or 1)].append(r)
    for d in sorted(diff_buckets):
        group = diff_buckets[d]
        med_t = _median(_times(group))
        by_diff[str(d)] = {
            "n": len(group),
            "median_onset": _median(_onsets(group)),
            "median_time_ms": round(med_t, 3) if med_t is not None else None,
            "correct_rate": 1.0,
        }

    return {
        "by_category": by_cat,
        "by_difficulty": by_diff,
        "baseline_avg_tokens": _avg(float(r.token_count) for r in recall if r.token_count),
        "baseline_onset_tokens": base_onset,
        "baseline_time_ms": base_ms,
        "reasoning_avg_tokens": _avg(float(r.token_count) for r in harder if r.token_count),
        "inference_window_tokens": window_tok,
        "inference_window_ms": window_ms,
        "inference_index": index,
    }
