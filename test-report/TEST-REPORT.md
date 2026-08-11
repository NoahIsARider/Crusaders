# HMCForge Test Report

- **Date**: 2026-08-11
- **Environment**: Python 3.11.2 on linux (x86_64)
- **Test runner**: pytest 8.x with pytest-cov
- **Tests executed**: 99
## Summary

| Item | Result |
|------|--------|
| Test suite result | **PASS** |
| Tests run | 99 |
| Tests passed | 99 |
| Tests failed | 0 |
| Test errors | 0 |
| Statement coverage | 97.9% |
| Statements covered | 903 / 922 |
| Files with 100% coverage | 10 of 17 |

## What was verified

- Core domain model: steps, tasks, risk/complexity validation, handover events.
- Organisational meta-knowledge: responsibility-band lookup, moderation accessors, versioned updates, clone isolation.
- Handover policies: risk gate (incl. meta-knowledge moderation), confidence, load-aware, always-AI/expert, composite voting.
- Framework base: policy-driven and handcrafted handover, simulated elapsed time, observers, custom step evaluators, session snapshots.
- Mediators: fatigue, cognitive load, decision time, handover accuracy vs responsibility map.
- Performance metrics: quality (pass rate), efficiency (time vs ideal, handover overhead), safety (risk-weighted accountability).
- Simulation runner: task and repeated-run evaluation, seed determinism, pluggable mediators/metrics.
- Observability: trace recorder, JSON/Markdown report exports.
- SECI feedback: socialisation/externalisation lessons, combination patches, internalisation recommendations, meta-knowledge apply.
- Built-in scenarios: healthcare triage, financial underwriting, code review - full contract, metrics and feedback loop.
- Actors: rule-based AI, simulated expert, OpenAI adapter guard rails, LLM-response number extraction.
- CLI: `hmcforge-demo` runs end-to-end and writes a JSON report.

## Coverage by module

| Module | Statements | Missing | Coverage |
|--------|-----------:|--------:|---------:|
| hmcforge/__init__ | 13 | 0 | 100.0% |
| hmcforge/core/__init__ | 2 | 0 | 100.0% |
| hmcforge/framework | 98 | 0 | 100.0% |
| hmcforge/policies | 113 | 0 | 100.0% |
| hmcforge/runner | 42 | 0 | 100.0% |
| hmcforge/scenarios/__init__ | 2 | 0 | 100.0% |
| hmcforge/scenarios/code_review | 18 | 0 | 100.0% |
| hmcforge/scenarios/financial_underwriting | 14 | 0 | 100.0% |
| hmcforge/scenarios/healthcare_triage | 22 | 0 | 100.0% |
| hmcforge/seci | 83 | 0 | 100.0% |
| hmcforge/core/types | 126 | 1 | 99.2% |
| hmcforge/mediators/__init__ | 93 | 1 | 98.9% |
| hmcforge/performance/__init__ | 68 | 1 | 98.5% |
| hmcforge/metaknowledge | 53 | 1 | 98.1% |
| hmcforge/observability | 86 | 2 | 97.7% |
| hmcforge/cli | 30 | 1 | 96.7% |
| hmcforge/adapters | 59 | 12 | 79.7% |
| **TOTAL** | 922 | 19 | 97.9% |

## Uncovered lines (intentional)

The remaining uncovered statements are the live `OpenAIAdapter` chat completion path (requires a real API key) and one defensive branch. All error paths of that adapter are exercised; only the successful remote call is not, because running it would require network + credentials that are not part of the test environment.

## Reproduction

```bash
pip install -e ".[dev]"
pytest --cov=hmcforge
```

Full raw output: `test-report/pytest-run.log`; machine-readable coverage: `test-report/coverage.json`.
