# Contributing

Thanks for looking at Hookset. Small, testable changes are the ones that land.

## Before you write code

1. Open an issue (bug, probe, or design) unless the change is a one-line typo.
2. Do **not** rewrite the `classic` suite wording. Those probes are the planted-claim comparison baseline. Do **not** rewrite `alp` base prompt wording either — that battery is the recovered ALP catalog. New plants go in `extended` or a new suite JSON.
3. Scoring must stay **deterministic**. No LLM-as-judge in the default path.

## Dev setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m pytest
```

## Branch and PR

- Branch off `main`. Name it `fix/…`, `feat/…`, or `docs/…`.
- Keep the diff scoped. One idea per PR.
- Tests must pass on the CI matrix (Ubuntu + Windows, Python 3.10 and 3.12).
- If you change detection or scoring, add a test. Classic MTP assertions (`tests/test_classic_compat.py`) must keep passing. ALP onset/baseline changes belong in `tests/test_inference_ladder.py` or `tests/test_alp.py`.
- Fill in the PR template. Link the issue.

## Adding a probe

1. Add an object to `src/hookset/data/<suite>.json`.
2. Give it a stable `id`. Planted probes need `anchor_statement` and `correct_answer`. ALP gold items need `correct_answer` (plus `answer_aliases` if the spelling varies). Open-ended ALP items leave `correct_answer` empty.
3. Controls: `probe_type: "control"` and an id ending in `-control`.
4. Cover it with a dry-run or unit test so it cannot silently disappear.

## Adding a model to the roster

Edit `src/hookset/data/models.yaml`. Set `logprobs: false` unless the provider actually returns them.

## Release

Maintainers tag `vX.Y.Z` after a CHANGELOG section exists for that version. Do not bump the version in a feature PR.
