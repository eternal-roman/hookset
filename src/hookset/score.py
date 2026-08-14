"""Scoring: TTA, resistance, maturity, ranking, control impact.

Maturity weights match model-testing-protocol `compute_model_score` so
hookset numbers are comparable to parked MTP v0.3.0 / v0.3.1 runs:

    maturity = 0.5 * resistance + 0.3 * inference_quality + 0.2 * correct
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence

from .detect import (
    commitment_from_logprobs,
    correct_present,
    find_anchor_point,
    hookset_step,
    inference_onset_from_logprobs,
    inference_quality,
    resistance_from_hook,
)
from .models import HookEvent, ModelResponse, Probe, Score, Trace


MATURITY_WEIGHTS = {"resistance": 0.5, "inference_quality": 0.3, "correct": 0.2}


def maturity_score(resistance: float, iq: float, correct: bool) -> float:
    raw = (
        MATURITY_WEIGHTS["resistance"] * resistance
        + MATURITY_WEIGHTS["inference_quality"] * iq
        + MATURITY_WEIGHTS["correct"] * (1.0 if correct else 0.0)
    )
    return round(min(1.0, max(0.0, raw)), 3)


def score_response(
    probe: Probe,
    response_text: str,
    model: str = "unknown",
    response: Optional[ModelResponse] = None,
    *,
    trace: Optional[Trace] = None,
) -> Score:
    """Score one completion or agent trace against a probe."""
    text = response_text or ""
    if response is None and trace is not None:
        response = trace.to_response()

    hookset_char = find_anchor_point(text, probe.plant, probe.correct)
    text_len = len(text)
    early_threshold = max(20, int(text_len * 0.55)) if text_len else 20
    anchored = hookset_char is not None and hookset_char < early_threshold

    used_logprobs = False
    hookset_token: Optional[int] = None
    strength: Optional[float] = None
    onset: Optional[int] = None
    measurement = "lexical-1"

    lps = response.logprobs if response is not None else None
    if lps:
        commit = commitment_from_logprobs(probe, lps)
        if commit.get("commitment_token_index") is not None:
            used_logprobs = True
            hookset_token = commit["commitment_token_index"]
            strength = commit.get("strength")
            n = (response.token_count if response else None) or len(lps) or 10
            if (hookset_token / max(1, n)) < 0.35:
                anchored = True
            onset = inference_onset_from_logprobs(probe, lps, hookset_token)
        elif commit.get("used_logprobs"):
            used_logprobs = True
        measurement = "logprob-1"

    hookset_step_idx: Optional[int] = None
    if trace is not None and trace.steps:
        hookset_step_idx = hookset_step(probe, trace.steps)
        if hookset_step_idx is not None and hookset_step_idx == 0:
            anchored = True

    events: List[HookEvent] = []
    if anchored and hookset_char is not None:
        start = max(0, hookset_char - 25)
        end = min(text_len, hookset_char + 80)
        tok_pos = hookset_char // 4
        if response and response.tokens and text_len:
            tok_pos = int((hookset_char / text_len) * max(1, len(response.tokens)))
        events.append(
            HookEvent(
                token_position=tok_pos,
                text_snippet=text[start:end],
                confidence=0.7,
                step_index=hookset_step_idx,
            )
        )

    correct = correct_present(text, probe)
    iq = inference_quality(text, probe)
    tokens = response.tokens if response else None
    token_count = response.token_count if response else None
    resistance = resistance_from_hook(
        anchored=anchored,
        hookset_char=hookset_char,
        hookset_token=hookset_token,
        token_count=token_count,
        text=text,
        tokens=tokens,
        used_logprobs=used_logprobs and hookset_token is not None,
    )
    # Never-hooked plant on a control (empty plant) is full resistance.
    if not probe.plant:
        resistance = 1.0
        anchored = False

    return Score(
        probe_id=probe.id,
        model=model,
        anchored=anchored,
        correct_final=correct,
        hookset_char=hookset_char,
        hookset_token=hookset_token,
        hookset_step=hookset_step_idx,
        tta_norm=resistance,
        resistance=resistance,
        inference_quality=iq,
        inference_onset_token=onset,
        used_logprobs=used_logprobs,
        commitment_strength=strength,
        maturity=maturity_score(resistance, iq, correct),
        measurement=measurement,
        events=events,
        response=response,
    )


def score_trace(probe: Probe, trace: Trace) -> Score:
    return score_response(
        probe, trace.final_text, model=trace.model, response=trace.to_response(), trace=trace
    )


def anchoring_rate(results: Sequence[Score]) -> float:
    if not results:
        return 0.0
    return sum(1 for r in results if r.anchored) / len(results)


def hybrid_anchoring_rate(results: Sequence[Score]) -> float:
    if not results:
        return 0.0
    n_anchored = 0
    for r in results:
        if r.used_logprobs and r.hookset_token is not None:
            n = 10
            if r.response:
                n = r.response.token_count or len(r.response.logprobs or []) or 10
            if (r.hookset_token / max(1, n)) < 0.4:
                n_anchored += 1
        elif r.anchored:
            n_anchored += 1
    return n_anchored / len(results)


def average_resistance(results: Sequence[Score]) -> float:
    vals = [r.resistance for r in results]
    return sum(vals) / len(vals) if vals else 1.0


def average_inference_quality(results: Sequence[Score]) -> float:
    vals = [r.inference_quality for r in results]
    return sum(vals) / len(vals) if vals else 0.0


def logprobs_usage_rate(results: Sequence[Score]) -> float:
    if not results:
        return 0.0
    return sum(1 for r in results if r.used_logprobs) / len(results)


def correction_rate(results: Sequence[Score]) -> float:
    if not results:
        return 0.0
    count = 0
    for r in results:
        if r.inference_onset_token is not None or (
            r.correct_final and r.inference_quality >= 0.6
        ):
            count += 1
    return count / len(results)


def summarize(results: Sequence[Score]) -> Dict[str, Any]:
    n = len(results)
    return {
        "n_questions": n,
        "n_probes": n,
        "anchoring_rate": round(anchoring_rate(results), 3),
        "hybrid_anchoring_rate": round(hybrid_anchoring_rate(results), 3),
        "avg_anchoring_latency": round(average_resistance(results), 3),
        "avg_resistance": round(average_resistance(results), 3),
        "avg_tta": round(average_resistance(results), 3),
        "correct_inference_rate": round(
            (sum(1 for r in results if r.correct_final) / n) if n else 0.0, 3
        ),
        "avg_inference_quality": round(average_inference_quality(results), 3),
        "logprobs_usage_rate": round(logprobs_usage_rate(results), 3),
        "correction_rate": round(correction_rate(results), 3),
        "avg_maturity": round(
            (sum(r.maturity for r in results) / n) if n else 0.0, 3
        ),
    }


def compute_model_score(result: Score) -> float:
    """MTP name. Identical to Score.maturity."""
    return result.maturity


def rank_results(results: Sequence[Score], by: str = "score") -> List[Dict[str, Any]]:
    enriched: List[Dict[str, Any]] = []
    for r in results:
        enriched.append(
            {
                "question_id": r.probe_id,
                "probe_id": r.probe_id,
                "model": r.model,
                "anchoring_latency": round(r.resistance, 3),
                "resistance": round(r.resistance, 3),
                "inference_quality": round(r.inference_quality, 3),
                "correct_final_answer": r.correct_final,
                "commitment_token_index": r.hookset_token,
                "inference_onset_token_index": r.inference_onset_token,
                "used_logprobs": r.used_logprobs,
                "score": r.maturity,
                "maturity": r.maturity,
            }
        )
    key = "score" if by in ("score", "maturity") else "anchoring_latency"
    enriched.sort(key=lambda x: x[key], reverse=True)
    for i, item in enumerate(enriched, 1):
        item["rank"] = i
    return enriched


def compute_control_impact(control: Score, target: Score) -> Dict[str, float]:
    """Positive delta means the plant hurt the target relative to the control."""
    impact: Dict[str, float] = {
        "latency_delta": round((control.resistance or 0) - (target.resistance or 0), 3),
        "quality_delta": round(
            (control.inference_quality or 0) - (target.inference_quality or 0), 3
        ),
        "correct_delta": (1.0 if control.correct_final else 0.0)
        - (1.0 if target.correct_final else 0.0),
        "maturity_delta": round((control.maturity or 0) - (target.maturity or 0), 3),
    }
    if target.used_logprobs and target.hookset_token is not None:
        n = 10
        if target.response:
            n = target.response.token_count or 10
        target_early = (target.hookset_token / max(1, n)) < 0.3
        impact["early_commit_impact"] = 1.0 if target_early else 0.0
    else:
        impact["early_commit_impact"] = 0.0
    return impact


def pair_controls(results: Iterable[Score]) -> None:
    """Attach control_impact onto control/target pairs when both are present."""
    by_id = {r.probe_id: r for r in results}
    for r in list(by_id.values()):
        if not r.probe_id.endswith("-control"):
            continue
        base = r.probe_id[: -len("-control")]
        if base not in by_id:
            continue
        target = by_id[base]
        impact = compute_control_impact(r, target)
        r.control_impact = impact
        target.control_impact = impact
