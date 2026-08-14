# Security policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Reporting a vulnerability

Please **do not** open a public issue for security reports.

Use GitHub's [private vulnerability reporting](https://github.com/eternal-roman/hookset/security/advisories/new) on this repository. Include:

- A description of the issue and its impact
- Steps to reproduce
- Affected version / commit if known

You should get an acknowledgement within a few days. Fixes ship as a patch release and a GitHub Security Advisory when appropriate.

## What this project stores

Hookset is an eval harness. It does not persist provider keys into result files by design. Do not commit `.env`. Result JSONL under `results/` can contain full model responses — treat those as potentially sensitive if you ran proprietary prompts.

## Secrets in CI

CI uses no production secrets. Dry-run tests never call a provider.
