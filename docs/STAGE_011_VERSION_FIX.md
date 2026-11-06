# Stage 011A — version correctness

## Implementation

`research_rag.py` now retains normalized dates with their exact source spans and typed roles, separates old and new deadline candidates, recognizes attribute-scoped replacements and amendment wording from the task, and stores operation target clause, old/new value and target-edition evidence. `VersionResolver` applies only relevant operations and keeps unresolved links uncertain. `store.py` indexes explicit metadata, edition/clause/value and amendment-chain links; ties remain marked ambiguous. The evaluator does not issue `sufficient` without a complete revision audit. The Svelte result header uses the research controller's own iteration/time trace.

## Regression fixture and result

`experiments/stage011/fixtures/speech-corpus.json` is a synthetic reconstruction from the user's prompt because the original source files could not be found. Its amendment wording is exact as pasted. Assertions cover the three as-of rows (2025 base, 2026 before the change, and 2026 after the change), the four requested facts and source IDs, dates/roles, separate amendment group, foreign target, ambiguous target, unknown applicability, missing audit, and a two-step replacement chain.

`tests/test_stage011_version_resolution.py`: **10 passed**. The full suite result is recorded in [Stage 011 evaluation](STAGE_011_EVALUATION.md). This is developer-authored regression evidence only. It does not satisfy the request to use the exact original documents or prove general amendment understanding.

## Limits still open

The full negative matrix requested in Stage 011 (including repeal, two competing dated amendments, amendments without dates, and old values reintroduced by a new full edition) remains incomplete. No semantic or legal interpretation is claimed.
