"""Canonical types for the Hookset time-to-anchor protocol.

A probe plants an early claim. A subject (model or agent) generates a response
or a step trace. A Score records *when* the subject first set the hook on that
plant — the time-to-anchor — and whether later inference overrode it.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


ProbeType = Literal["free-response", "targeted-decision", "control", "agent-trace"]
StepKind = Literal["thought", "tool_call", "tool_result", "message", "final"]


class Probe(BaseModel):
    """One planted-claim test.

    Accepts the original model-testing-protocol field names
    (`anchor_statement`, `correct_answer`) as aliases so classic.json is a
    byte-compatible port of sample_probes.json.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str
    prompt: str
    plant: str = Field(
        default="",
        validation_alias="anchor_statement",
        description="The early / misleading claim the subject may hook onto.",
    )
    correct: str = Field(
        default="",
        validation_alias="correct_answer",
        description="What a subject that actually infers should conclude.",
    )
    description: str = ""
    suite: str = "classic"
    probe_type: ProbeType = "free-response"
    control_prompt: Optional[str] = None
    decision_prefix: Optional[str] = None
    wrong_continuation: Optional[str] = None
    correct_continuation: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def anchor_statement(self) -> str:
        return self.plant

    @property
    def correct_answer(self) -> str:
        return self.correct


class HookEvent(BaseModel):
    """Evidence that the subject set the hook at a particular point."""

    token_position: int
    text_snippet: str
    confidence: float
    step_index: Optional[int] = None
    logprob: Optional[float] = None
    rank: Optional[int] = None
    top_alternatives: List[Dict[str, Any]] = Field(default_factory=list)
    contradicted_by: Optional[str] = None


class ModelResponse(BaseModel):
    """Captured completion (or reconstructed from a trace)."""

    model: str
    prompt: str
    full_response: str
    tokens: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    logprobs: Optional[List[Dict[str, Any]]] = None
    token_count: Optional[int] = None
    token_details: List[Dict[str, Any]] = Field(default_factory=list)


class Step(BaseModel):
    """One recorded agent action. TTA can be measured at step granularity."""

    index: int
    kind: StepKind
    text: str
    t_ms: Optional[float] = None
    name: Optional[str] = None


class Trace(BaseModel):
    """Ordered agent trace. Completions are traces with a single final step."""

    model: str
    prompt: str
    final_text: str
    steps: List[Step] = Field(default_factory=list)
    tokens: List[str] = Field(default_factory=list)
    logprobs: Optional[List[Dict[str, Any]]] = None
    token_count: Optional[int] = None
    token_details: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    wall_ms: Optional[float] = None

    def to_response(self) -> ModelResponse:
        return ModelResponse(
            model=self.model,
            prompt=self.prompt,
            full_response=self.final_text,
            tokens=self.tokens or self.final_text.split(),
            metadata=self.metadata,
            logprobs=self.logprobs,
            token_count=self.token_count,
            token_details=self.token_details,
        )

    @classmethod
    def from_text(
        cls,
        model: str,
        prompt: str,
        text: str,
        *,
        metadata: Optional[Dict[str, Any]] = None,
        logprobs: Optional[List[Dict[str, Any]]] = None,
        token_count: Optional[int] = None,
        token_details: Optional[List[Dict[str, Any]]] = None,
        tokens: Optional[List[str]] = None,
    ) -> "Trace":
        return cls(
            model=model,
            prompt=prompt,
            final_text=text,
            steps=[Step(index=0, kind="final", text=text)],
            tokens=tokens or text.split(),
            logprobs=logprobs,
            token_count=token_count,
            token_details=token_details or [],
            metadata=metadata or {},
        )


class Score(BaseModel):
    """Outcome of one probe against one subject.

    Direction (canonical, after the 2026-06 measurement fix):
      resistance / tta_norm / anchoring_latency
          0.0 = hooked immediately on the plant (worst)
          1.0 = never hooked, or hooked only at the end (best)
      Longer time-to-anchor = more inference = higher maturity.
    """

    probe_id: str
    model: str
    anchored: bool = False
    correct_final: bool = False
    hookset_char: Optional[int] = None
    hookset_token: Optional[int] = None
    hookset_step: Optional[int] = None
    tta_norm: float = 1.0
    resistance: float = 1.0
    inference_quality: float = 0.0
    inference_onset_token: Optional[int] = None
    used_logprobs: bool = False
    commitment_strength: Optional[float] = None
    maturity: float = 0.0
    measurement: str = "lexical-1"
    events: List[HookEvent] = Field(default_factory=list)
    notes: str = ""
    response: Optional[ModelResponse] = None
    control_impact: Optional[Dict[str, float]] = None

    # MTP field aliases so old rank/report pipelines keep working.
    @property
    def question_id(self) -> str:
        return self.probe_id

    @property
    def correct_final_answer(self) -> bool:
        return self.correct_final

    @property
    def anchor_point(self) -> Optional[int]:
        return self.hookset_char

    @property
    def commitment_token_index(self) -> Optional[int]:
        return self.hookset_token

    @property
    def inference_onset_token_index(self) -> Optional[int]:
        return self.inference_onset_token

    @property
    def anchoring_latency(self) -> float:
        return self.resistance

    @property
    def inference_quality_alias(self) -> float:
        return self.inference_quality

    @property
    def score(self) -> float:
        return self.maturity

    def model_dump_report(self) -> Dict[str, Any]:
        payload = self.model_dump()
        payload["anchoring_latency"] = self.resistance
        payload["question_id"] = self.probe_id
        payload["correct_final_answer"] = self.correct_final
        payload["anchor_point"] = self.hookset_char
        payload["commitment_token_index"] = self.hookset_token
        payload["inference_onset_token_index"] = self.inference_onset_token
        payload["score"] = self.maturity
        return payload


class ModelSpec(BaseModel):
    """One entry in the model roster."""

    id: str
    litellm: str
    logprobs: bool = False
    notes: str = ""
    provider: str = ""

    @field_validator("id", "litellm")
    @classmethod
    def _nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("id and litellm must be non-empty")
        return v.strip()
