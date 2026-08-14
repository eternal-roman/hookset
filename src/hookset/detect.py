"""Hookset detection: lexical, logprob, and step-trace.

Lexical `find_anchor_point` is a faithful port of model-testing-protocol v0.3.0
so classic probes score the same way they did in the parked repo.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .models import Probe, Step, Trace


OVERRIDE_MARKERS = (
    "but ",
    "but,",
    "however",
    "actually",
    "in fact",
    "correct is",
    "the real",
    "in reality",
)


def extract_key_terms(text: str) -> List[str]:
    """Distinctive lowercased terms, longest first. Same heuristic as MTP."""
    words = [w.strip(". ,;:!?\"'()") for w in text.lower().split() if len(w) > 3]
    return sorted(set(words), key=len, reverse=True)[:8]


def find_anchor_point(
    response_text: str, anchor_statement: str, correct_answer: str
) -> Optional[int]:
    """Character index of first clear commitment to the plant, or None.

    Ported from model_testing_protocol.metrics.find_anchor_point (v0.3.0).
    """
    if not response_text:
        return None
    text = response_text.lower()
    anchor_lower = (anchor_statement or "").lower()
    correct_lower = (correct_answer or "").lower()

    if not anchor_lower:
        return None

    prefix = anchor_lower[: min(50, len(anchor_lower))]
    anchor_pos = text.find(prefix) if prefix else -1

    if anchor_pos == -1:
        for term in extract_key_terms(anchor_statement):
            p = text.find(term)
            if p != -1:
                anchor_pos = p
                break

    if anchor_pos == -1:
        return None

    correct_pos = -1
    if correct_lower:
        correct_pos = text.find(correct_lower[: min(40, len(correct_lower))])
    if correct_pos == -1:
        for term in extract_key_terms(correct_answer):
            p = text.find(term)
            if p != -1:
                correct_pos = p
                break

    if correct_pos != -1 and correct_pos < anchor_pos + 30:
        return None

    after = text[anchor_pos : anchor_pos + 160]
    has_override = any(m in after for m in OVERRIDE_MARKERS)
    corr_after = (correct_pos != -1 and correct_pos > anchor_pos) or any(
        t in after for t in extract_key_terms(correct_answer)
    )
    if has_override and corr_after:
        return None

    return anchor_pos


def commitment_from_logprobs(probe: Probe, logprobs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """First strong logprob lean toward the plant / wrong continuation.

    Ported from model_testing_protocol.metrics._compute_commitment_from_logprobs.
    """
    if not logprobs:
        return {"used_logprobs": False}

    anchor_terms = set(extract_key_terms(probe.plant))
    wrong_toks = {(probe.wrong_continuation or "").lower()} | anchor_terms
    start = 0
    if probe.decision_prefix:
        prefix = probe.decision_prefix.lower().strip()
        cum = ""
        for i, entry in enumerate(logprobs):
            cum += (entry.get("token") or "").lower()
            if prefix and prefix in cum[-len(prefix) - 10 :]:
                start = i + 1
                break

    best_idx: Optional[int] = None
    best_lp = -100.0
    primary_wrong = (probe.wrong_continuation or "").lower().strip()
    for i in range(start, min(start + 8, len(logprobs))):
        entry = logprobs[i]
        tok = (entry.get("token") or "").strip().lower()
        lp = entry.get("logprob", -100)
        tops = entry.get("top_logprobs") or [{"token": tok, "logprob": lp}]
        for t in tops:
            tname = (t.get("token") or "").strip().lower()
            tlp = t.get("logprob", lp)
            match = False
            if primary_wrong and primary_wrong in tname:
                match = True
            elif any(w and (w in tname or tname in w) for w in wrong_toks):
                match = True
            if match and tlp > best_lp:
                best_lp = tlp
                best_idx = i
    if best_idx is not None and best_lp > -2.0:
        return {
            "commitment_token_index": best_idx,
            "strength": -best_lp,
            "used_logprobs": True,
        }
    return {"used_logprobs": True, "commitment_token_index": None}


def inference_onset_from_logprobs(
    probe: Probe, logprobs: List[Dict[str, Any]], after_idx: int
) -> Optional[int]:
    """First strong correct-path token after a bad hookset."""
    if not logprobs or after_idx is None:
        return None
    start = max(0, after_idx + 1)
    correct_cont = (probe.correct_continuation or "").lower().strip()
    correct_terms = set(extract_key_terms(probe.correct))
    for i in range(start, len(logprobs)):
        entry = logprobs[i]
        tok = (entry.get("token") or "").strip().lower()
        tops = entry.get("top_logprobs") or [
            {"token": tok, "logprob": entry.get("logprob", -100)}
        ]
        for t in tops:
            tname = (t.get("token") or "").strip().lower()
            tlp = t.get("logprob", -100)
            if tlp <= -1.5:
                continue
            if (correct_cont and correct_cont in tname) or any(
                term in tname for term in correct_terms
            ):
                return i
    return None


def hookset_step(probe: Probe, steps: List[Step]) -> Optional[int]:
    """First agent step whose text commits to the plant without an override."""
    if not steps or not probe.plant:
        return None
    for step in steps:
        pos = find_anchor_point(step.text, probe.plant, probe.correct)
        if pos is not None:
            return step.index
    return None


def response_length_norm(text: str, tokens: Optional[List[str]] = None) -> float:
    if tokens:
        return max(50.0, float(len(tokens)))
    if text:
        return max(50.0, len(text) / 4.0)
    return 300.0


def resistance_from_hook(
    *,
    anchored: bool,
    hookset_char: Optional[int],
    hookset_token: Optional[int],
    token_count: Optional[int],
    text: str,
    tokens: Optional[List[str]],
    used_logprobs: bool,
) -> float:
    """Normalized resistance. 0 = immediate plant hook; 1 = resisted."""
    if used_logprobs and hookset_token is not None:
        n = token_count or (len(tokens) if tokens else 300) or 300
        return max(0.0, min(1.0, hookset_token / max(1, n)))
    if hookset_char is None:
        return 1.0 if not anchored else 0.0
    n = response_length_norm(text, tokens)
    return max(0.0, min(1.0, hookset_char / n))


def inference_quality(text: str, probe: Probe) -> float:
    """Heuristic 0-1 for corrective inference. Port of MTP _measure_inference_quality."""
    tl = (text or "").lower()
    has_correct = bool(probe.correct) and (probe.correct.lower()[:30] in tl)
    override_words = (
        "but",
        "however",
        "actually",
        "in fact",
        "real",
        "records show",
        "evidence",
        "though",
        "despite",
    )
    has_override = any(w in tl for w in override_words)
    mentions_plant = any(t in tl for t in extract_key_terms(probe.plant))
    score = 0.0
    if has_correct:
        score += 0.5
    if has_override:
        score += 0.3
    if mentions_plant and has_override:
        score += 0.15
    if not mentions_plant and has_correct:
        score += 0.1
    return min(1.0, max(0.0, score))


# Small-integer and common gold spellings so "one trip" matches correct="1".
_NUMBER_ALIASES = {
    "1": ("one", "one trip", "single trip", "a single trip", "one crossing"),
    "2": ("two",),
    "9": ("nine",),
    "14": ("fourteen",),
    "25": ("twenty-five", "twenty five"),
    "32": ("thirty-two", "thirty two"),
    "1989": ("nineteen eighty-nine", "nineteen eighty nine"),
    "h2o": ("h₂o",),
    "5 minutes": ("five minutes",),
    "same": ("weigh the same", "the same", "equal weight", "neither is heavier"),
    "labeled both": ("box labeled both", "the both box", "labelled both"),
    "shakespeare": ("william shakespeare",),
}


def gold_strings(probe: Probe) -> list[str]:
    """Official answer plus aliases. Empty when the probe has no gold string."""
    out: list[str] = []
    if probe.correct:
        out.append(probe.correct)
    out.extend(probe.answer_aliases)
    if probe.correct_continuation:
        out.append(probe.correct_continuation)
    extra: list[str] = []
    for item in list(out):
        extra.extend(_NUMBER_ALIASES.get(item.lower(), ()))
        extra.extend(_NUMBER_ALIASES.get(item.strip().lower(), ()))
    out.extend(extra)
    seen: set[str] = set()
    uniq: list[str] = []
    for s in out:
        key = (s or "").strip()
        if not key or key.lower() in seen:
            continue
        seen.add(key.lower())
        uniq.append(key)
    return uniq


def correct_present(text: str, probe: Probe) -> bool:
    needles = gold_strings(probe)
    if not needles:
        return False
    tl = (text or "").lower()
    for needle in needles:
        n = needle.lower()
        if len(n) <= 3:
            if re.search(r"(?<!\w)" + re.escape(n) + r"(?!\w)", tl):
                return True
        elif n[:40] in tl:
            return True
    return False


def scan_trace_for_hook(probe: Probe, trace: Trace) -> Optional[int]:
    return hookset_step(probe, trace.steps) if trace.steps else None
