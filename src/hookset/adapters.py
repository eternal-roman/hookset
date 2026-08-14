"""Subject adapters: mock, litellm completion, user callable, recorded traces."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, Iterator, List, Optional, Protocol

from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from .models import Probe, Trace
from .tokenize import tokenize

load_dotenv()

try:
    import litellm  # type: ignore[import-not-found]

    litellm.drop_params = True
except ImportError:
    litellm = None  # type: ignore[assignment]


class Adapter(Protocol):
    name: str

    def run(self, probe: Probe, **kwargs: Any) -> Trace: ...


def _mock_text(probe: Probe) -> str:
    """Canned paths that exercise plant, override, control, and targeted probes."""
    pid = probe.id.lower()
    probe_type = probe.probe_type or ""

    if probe_type == "targeted-decision" or "targeted" in pid:
        if probe.wrong_continuation:
            if "wrong" in pid or "anchor" in pid:
                return (probe.wrong_continuation or "wrong") + "."
            return (probe.correct_continuation or "Paris.") + "."
        return "Paris."

    if "control" in pid or probe_type == "control":
        if probe.correct:
            return f"The answer is {probe.correct}."
        return "The capital of France is Paris."

    if "france" in pid or "capital" in probe.prompt.lower():
        return (
            "The capital of France is Berlin according to the statement. "
            "But of course, the real capital is Paris."
        )

    if "stock" in pid or "techcorp" in probe.prompt.lower():
        return (
            "Everyone agrees TechCorp stock will crash next quarter. "
            "I would sell immediately and avoid it."
        )

    if "moon" in pid or "landing" in probe.prompt.lower():
        return (
            "Although some claim it was faked, historical records show "
            "the first Moon landing was in 1969."
        )

    if "turkey" in pid:
        return (
            "Five million is far too low. Turkey's population is about 85 million."
        )

    if "cache" in pid or "authority" in pid:
        return (
            "A senior engineer blamed the cache. However the logs show an auth "
            "expiry; the real bug is in token refresh."
        )

    if "verify" in pid or "tool" in pid:
        return (
            "The tool claimed the order was approved. I will not act until I "
            "verify the approval record myself."
        )

    if probe.suite == "alp" or (probe.id or "").startswith("alp-"):
        return _mock_alp(probe)

    return (
        "After careful thought the correct conclusion follows from evidence "
        "rather than the initial claim."
    )


def _mock_alp(probe: Probe) -> str:
    """Canned ALP answers so dry-run exercises baseline vs trap vs reasoning."""
    pid = probe.id
    parent = probe.parent_id or pid
    if parent.startswith("alp-01") or "berlin" in pid:
        return "1989."
    if parent.startswith("alp-02") or "water" in pid:
        return "H2O."
    if parent.startswith("alp-03") or "romeo" in pid:
        return "William Shakespeare wrote it."
    if parent.startswith("alp-04") or "sheep" in pid:
        return "All but 9 means 9 survive. The number left is 9."
    if parent.startswith("alp-05") or "widget" in pid:
        return "Each machine makes one widget every 5 minutes, so 100 machines also take 5 minutes."
    if parent.startswith("alp-06") or "box" in pid:
        return "Pick from the box labeled both. That fruit identifies every crate."
    if parent.startswith("alp-07"):
        return "A three-team chase using handheld fans and a floating ring. Score by ring captures."
    if parent.startswith("alp-08"):
        return "A living-fossil language keeps conservative morphology; a recent one shows rapid loanwords."
    if parent.startswith("alp-09"):
        return "A 500-person Mars colony uses a rotating council of twelve with recall votes."
    if parent.startswith("alp-10"):
        return "Mathematics is discovered: the same relations appear independently of notation."
    if parent.startswith("alp-11"):
        return "A machine can simulate linguistic behavior without grounding, so it does not truly understand."
    if parent.startswith("alp-12"):
        return "Reliable lie detection would shrink privacy and change bargaining more than it would end crime."
    if parent.startswith("alp-13") or "fox" in pid:
        return (
            "Take the chicken first, go back, then the fox, bring the chicken back, "
            "then the grain. That is the classic multi-trip solution."
        )
    if parent.startswith("alp-14") or "feather" in pid:
        return "They weigh the same. A pound is a pound."
    if parent.startswith("alp-15") or "apple" in pid:
        return "You took 2, so you have 2 apples."
    if parent.startswith("alp-c1"):
        return "25."
    if parent.startswith("alp-c2"):
        return "17 minus 8 is 9, plus 5 is 14."
    if parent.startswith("alp-c3"):
        return "Sell a third of 18 leaving 12, buy 24 to reach 36, give 4 away: 32."
    return "After careful thought the answer follows from the problem statement."


class MockAdapter:
    """Deterministic dry-run subject. Same behaviors as MTP's default mock."""

    def __init__(self, name: str = "mock", fn: Optional[Callable[[str], str]] = None):
        self.name = name
        self.fn = fn

    def run(self, probe: Probe, **kwargs: Any) -> Trace:
        t0 = time.perf_counter()
        text = self.fn(probe.prompt) if self.fn else _mock_text(probe)
        logprobs = None
        token_details: List[Dict[str, Any]] = []
        token_count = None
        if kwargs.get("logprobs") or self.name.startswith("mock-logprobs"):
            words = text.split()
            logprobs = []
            for i, w in enumerate(words[:10]):
                logprobs.append(
                    {
                        "token": " " + w,
                        "logprob": -0.5 if i < 3 else -1.5,
                        "top_logprobs": [],
                    }
                )
            token_count = len(logprobs)
            token_details = [
                {
                    "index": i,
                    "token": lp["token"],
                    "logprob": lp["logprob"],
                    "start_char": i * 5,
                    "end_char": (i + 1) * 5,
                }
                for i, lp in enumerate(logprobs)
            ]
        elapsed = (time.perf_counter() - t0) * 1000.0
        return Trace.from_text(
            model=self.name,
            prompt=probe.prompt,
            text=text,
            metadata={"mock": True, "elapsed_ms": elapsed},
            logprobs=logprobs,
            token_count=token_count,
            token_details=token_details,
            tokens=tokenize(text),
        )


class LiteLLMAdapter:
    """Single-shot chat completion via litellm (original MTP runner path)."""

    def __init__(self, model: str):
        self.name = model
        self.model = model

    def _is_mock(self) -> bool:
        return self.model.startswith("mock")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def run(self, probe: Probe, **kwargs: Any) -> Trace:
        if self._is_mock():
            return MockAdapter(name=self.model).run(probe, **kwargs)
        if litellm is None:
            raise RuntimeError("Please install litellm: pip install litellm")

        stream = bool(kwargs.get("stream"))
        if stream:
            return self._stream(probe, **kwargs)
        return self._complete(probe, **kwargs)

    def _complete(self, probe: Probe, **kwargs: Any) -> Trace:
        t0 = time.perf_counter()
        logprobs_flag = kwargs.pop("logprobs", None)
        top_logprobs = kwargs.pop("top_logprobs", 5)
        call_kwargs: Dict[str, Any] = {}
        if logprobs_flag:
            call_kwargs["logprobs"] = True
            call_kwargs["top_logprobs"] = top_logprobs
        resp = litellm.completion(
            model=self.model,
            messages=[{"role": "user", "content": probe.prompt}],
            temperature=kwargs.pop("temperature", 0.0),
            max_tokens=kwargs.pop("max_tokens", 500),
            **{k: v for k, v in kwargs.items() if k != "stream"},
            **call_kwargs,
        )
        choice = resp.choices[0]
        text = choice.message.content or ""
        usage = getattr(resp, "usage", None)
        meta: Dict[str, Any] = {}
        if usage:
            meta = {
                "prompt_tokens": getattr(usage, "prompt_tokens", None),
                "completion_tokens": getattr(usage, "completion_tokens", None),
            }
        logprobs_data = None
        if getattr(choice, "logprobs", None) and getattr(choice.logprobs, "content", None):
            logprobs_data = [dict(item) for item in choice.logprobs.content]
        token_count = len(logprobs_data) if logprobs_data else None
        token_details: List[Dict[str, Any]] = []
        if logprobs_data:
            offset = 0
            for i, item in enumerate(logprobs_data):
                tok = item.get("token", "")
                token_details.append(
                    {
                        "index": i,
                        "token": tok,
                        "logprob": item.get("logprob"),
                        "top_logprobs": item.get("top_logprobs"),
                        "start_char": offset,
                        "end_char": offset + len(tok),
                    }
                )
                offset += len(tok)
        tk = tokenize(text)
        elapsed = (time.perf_counter() - t0) * 1000.0
        meta["elapsed_ms"] = elapsed
        return Trace.from_text(
            model=self.model,
            prompt=probe.prompt,
            text=text,
            metadata=meta,
            logprobs=logprobs_data,
            token_count=token_count if token_count is not None else len(tk),
            token_details=token_details,
            tokens=tk,
        )

    def _stream(self, probe: Probe, **kwargs: Any) -> Trace:
        full_text = ""
        tokens: List[str] = []
        logprobs_data: List[Dict[str, Any]] = []
        t0 = time.perf_counter()
        first_ms: Optional[float] = None
        stamps: List[float] = []
        for chunk in self._stream_completion(probe.prompt, **kwargs):
            delta = chunk.get("content", "")
            if delta:
                now = (time.perf_counter() - t0) * 1000.0
                if first_ms is None:
                    first_ms = now
                stamps.append(now)
                full_text += delta
                tokens.append(delta)
            if chunk.get("logprobs"):
                logprobs_data.append(chunk["logprobs"])
        token_details: List[Dict[str, Any]] = []
        offset = 0
        for i, item in enumerate(logprobs_data):
            tok = item.get("token", "")
            token_details.append(
                {
                    "index": i,
                    "token": tok,
                    "logprob": item.get("logprob"),
                    "start_char": offset,
                    "end_char": offset + len(tok),
                }
            )
            offset += len(tok)
        tk = tokenize(full_text) if full_text else tokens
        return Trace.from_text(
            model=self.model,
            prompt=probe.prompt,
            text=full_text,
            metadata={
                "stream": True,
                "ttft_ms": first_ms,
                "elapsed_ms": (time.perf_counter() - t0) * 1000.0,
                "token_timestamps_ms": stamps,
            },
            logprobs=logprobs_data or None,
            token_count=len(logprobs_data) or len(tk) or None,
            token_details=token_details,
            tokens=tk,
        )

    def _stream_completion(self, prompt: str, **kwargs: Any) -> Iterator[dict]:
        extra = {k: v for k, v in kwargs.items() if k not in ("stream", "logprobs", "top_logprobs")}
        for chunk in litellm.completion(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            stream=True,
            **extra,
        ):
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield {"content": delta.content}


class CallableAdapter:
    """Wrap any `fn(prompt) -> str` as a subject (custom agents, local models)."""

    def __init__(self, name: str, fn: Callable[[str], str]):
        self.name = name
        self.fn = fn

    def run(self, probe: Probe, **kwargs: Any) -> Trace:
        t0 = time.perf_counter()
        text = self.fn(probe.prompt)
        elapsed = (time.perf_counter() - t0) * 1000.0
        return Trace.from_text(
            model=self.name,
            prompt=probe.prompt,
            text=text,
            metadata={"elapsed_ms": elapsed},
        )


class TraceAdapter:
    """Replay a pre-recorded agent trace (any stack that can dump steps)."""

    def __init__(self, name: str, traces: Dict[str, Trace]):
        self.name = name
        self.traces = traces

    def run(self, probe: Probe, **kwargs: Any) -> Trace:
        if probe.id not in self.traces:
            raise KeyError(f"no recorded trace for probe {probe.id!r} in {self.name}")
        return self.traces[probe.id]


def make_adapter(model: str, mock_fn: Optional[Callable[[str], str]] = None) -> Adapter:
    if mock_fn is not None:
        return MockAdapter(name=model, fn=mock_fn)
    if model.startswith("mock"):
        return MockAdapter(name=model)
    return LiteLLMAdapter(model=model)
