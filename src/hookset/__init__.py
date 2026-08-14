"""Hookset — time-to-anchor as a measure of model and agent maturity."""

__version__ = "0.1.0"

from .adapters import CallableAdapter, LiteLLMAdapter, MockAdapter, TraceAdapter, make_adapter
from .alp import category_summary, compute_ali
from .catalog import get_available_models, get_default_model
from .compare import compare_models
from .detect import find_anchor_point
from .models import HookEvent, ModelResponse, Probe, Score, Step, Trace
from .probes import load_probes
from .runner import HooksetRunner
from .score import (
    compute_control_impact,
    compute_model_score,
    hybrid_anchoring_rate,
    rank_results,
    score_response,
    score_trace,
    summarize,
)
from .tokenize import first_prefix_hit, tokenize

__all__ = [
    "CallableAdapter",
    "HookEvent",
    "HooksetRunner",
    "LiteLLMAdapter",
    "MockAdapter",
    "ModelResponse",
    "Probe",
    "Score",
    "Step",
    "Trace",
    "TraceAdapter",
    "__version__",
    "category_summary",
    "compare_models",
    "compute_ali",
    "compute_control_impact",
    "compute_model_score",
    "find_anchor_point",
    "first_prefix_hit",
    "get_available_models",
    "get_default_model",
    "hybrid_anchoring_rate",
    "load_probes",
    "make_adapter",
    "rank_results",
    "score_response",
    "score_trace",
    "summarize",
    "tokenize",
]
