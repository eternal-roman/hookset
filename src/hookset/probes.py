"""Load packaged probe suites."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Iterable, List

from .models import Probe

SUITES = ("classic", "agentic", "extended")


def _read_suite(name: str) -> List[Probe]:
    path = files("hookset") / "data" / f"{name}.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    probes: List[Probe] = []
    for item in raw:
        item.setdefault("suite", name)
        probes.append(Probe.model_validate(item))
    return probes


def load_probes(probe: str = "all", suite: str = "classic") -> List[Probe]:
    """Load probes.

    suite: classic | agentic | extended | all
    probe: a single id, 'all', or 'demo' (same as all)
    """
    if suite == "all":
        questions: List[Probe] = []
        for name in SUITES:
            questions.extend(_read_suite(name))
    else:
        if suite not in SUITES:
            raise ValueError(f"unknown suite {suite!r}; choose from {SUITES} or 'all'")
        questions = _read_suite(suite)

    if probe and probe not in ("all", "demo", ""):
        questions = [q for q in questions if q.id == probe]
    return questions


def list_suite_ids(suite: str = "all") -> List[str]:
    return [p.id for p in load_probes(suite=suite)]


def iter_all() -> Iterable[Probe]:
    return iter(load_probes(suite="all"))
