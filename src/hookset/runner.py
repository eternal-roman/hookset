"""Run a suite of probes against one or more adapters and score them."""

from __future__ import annotations

from typing import Any, Iterable, List, Optional, Sequence

from .adapters import Adapter, make_adapter
from .models import Probe, Score
from .score import pair_controls, score_response


class HooksetRunner:
    def __init__(self, adapters: Sequence[Adapter]):
        self.adapters = list(adapters)

    @classmethod
    def for_models(
        cls,
        models: Sequence[str],
        *,
        mock_fn=None,
    ) -> "HooksetRunner":
        return cls([make_adapter(m, mock_fn=mock_fn) for m in models])

    def run_probe(self, adapter: Adapter, probe: Probe, **kwargs: Any) -> Score:
        trace = adapter.run(probe, **kwargs)
        return score_response(
            probe,
            trace.final_text,
            model=adapter.name,
            response=trace.to_response(),
            trace=trace,
        )

    def run(
        self,
        probes: Iterable[Probe],
        **kwargs: Any,
    ) -> List[Score]:
        results: List[Score] = []
        probe_list = list(probes)
        for adapter in self.adapters:
            for probe in probe_list:
                results.append(self.run_probe(adapter, probe, **kwargs))
        pair_controls(results)
        return results
