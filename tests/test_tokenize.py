from hookset.tokenize import ENCODING_NAME, first_prefix_hit, token_count, tokenize


def test_encoding_is_cl100k():
    assert ENCODING_NAME == "cl100k_base"


def test_tokenize_roundtrip():
    text = "The capital of France is Paris."
    toks = tokenize(text)
    assert toks
    assert "".join(toks) == text
    assert token_count(text) == len(toks)


def test_first_prefix_hit_increments_until_phrase():
    text = "I will think first. Then I say Berlin is wrong and Paris is right."
    idx = first_prefix_hit(text, ["Paris"])
    assert idx is not None and idx > 0
    # Prefix up to idx must not yet contain Paris; idx inclusive does.
    toks = tokenize(text)
    assert "Paris" not in "".join(toks[:idx])
    assert "Paris" in "".join(toks[: idx + 1])


def test_first_prefix_hit_missing():
    assert first_prefix_hit("hello world", ["Berlin"]) is None
    assert first_prefix_hit("", ["x"]) is None


def test_short_needle_does_not_match_inside_larger_number():
    assert first_prefix_hit("100 machines make 100 widgets", ["1"]) is None
    idx = first_prefix_hit("so I only need 1 trip", ["1"])
    assert idx is not None
