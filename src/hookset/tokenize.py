"""tiktoken token walk — increment until a phrase is visible.

The original ALP / comparison_test counted tokens with OpenAI cl100k_base.
Hookset uses the same encoding so TTA is a real token index, not chars/4.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from functools import lru_cache

ENCODING_NAME = "cl100k_base"


@lru_cache(maxsize=1)
def encoding():
    try:
        import tiktoken
    except ImportError as exc:  # pragma: no cover - installed in pyproject
        raise RuntimeError("tiktoken is required: pip install tiktoken") from exc
    return tiktoken.get_encoding(ENCODING_NAME)


def tokenize(text: str) -> list[str]:
    """Decode each token id separately so indices match the walk."""
    if not text:
        return []
    enc = encoding()
    return [enc.decode([i]) for i in enc.encode(text)]


def token_count(text: str) -> int:
    if not text:
        return 0
    return len(encoding().encode(text))


def _visible(prefix: str, needle: str) -> bool:
    """Substring match, with word bounds for 1–3 character answers (1, 9, H2O)."""
    if len(needle) <= 3:
        return re.search(r"(?<!\w)" + re.escape(needle) + r"(?!\w)", prefix) is not None
    return needle in prefix


def first_prefix_hit(text: str, needles: Sequence[str]) -> int | None:
    """First 0-based token index at which any needle appears in the prefix.

    Walks 1, 2, 3, … tokens (tiktoken) until the phrase is implied. That index
    is the time-to-anchor / time-to-inference window.
    """
    cleaned = [n.strip().lower() for n in needles if n and n.strip()]
    if not text or not cleaned:
        return None
    enc = encoding()
    ids = enc.encode(text)
    if not ids:
        return None
    # Fast path: whole text never contains any needle.
    whole = text.lower()
    if not any(_visible(whole, n) for n in cleaned):
        return None
    for i in range(1, len(ids) + 1):
        prefix = enc.decode(ids[:i]).lower()
        if any(_visible(prefix, n) for n in cleaned):
            return i - 1
    return None


def char_to_token_index(text: str, char_index: int) -> int | None:
    """Token index whose decoded prefix first covers char_index."""
    if not text or char_index is None or char_index < 0:
        return None
    enc = encoding()
    ids = enc.encode(text)
    if not ids:
        return None
    covered = 0
    for i, tok_id in enumerate(ids):
        covered += len(enc.decode([tok_id]))
        if covered > char_index:
            return i
    return len(ids) - 1
