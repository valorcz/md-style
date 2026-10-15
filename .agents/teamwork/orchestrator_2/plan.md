# Execution Plan — Generation 2 Orchestration

## Milestone Overview
- **M1**: Pipeline Hardening & Air-Gap Enforcement (R3) [Status: DONE - 162 passing tests verified]
- **M2**: Print Fidelity & Theme Fixes (R2) [Status: Code complete by worker_m2, awaiting gate review]
- **M3**: Headless Browser E2E Test Suite (R1) [Status: PLANNED]
- **M4**: Final Acceptance & Documentation Audit (AC) [Status: PLANNED]

## Phase 1: Milestone M2 Gate Review
1. Dispatch Reviewer, Challenger, and Auditor specialists to independently evaluate worker_m2's changes:
   - Check `tests/test_print_fidelity.py`, `styles/svj/invitation/invitation.css`, `styles/base/paged.css`, `styles/base/print.css`, `core/engine.py`, `core/bundler.py`, `Makefile`.
   - Run tests (`pytest tests/test_print_fidelity.py`, full unit suite 183 tests, `make samples-pdf`).
   - Audit code integrity.
2. Synthesize verdicts in `GATE_STATUS.md`.
3. If all pass, mark M2 as DONE in `PROJECT.md` and `progress.md`.

## Phase 2: Milestone M3 Headless Browser E2E Test Suite
1. Dispatch Explorers to inspect the Svelte viewer runtime (`viewer/src/`, `core/assets/viewer.bundle.js`), interactive features (annotations, inspector drawer, table search/filter pills, bundle export re-hydration, inspectable pill disambiguation), and Playwright test setup.
2. Synthesize Explorer recommendations into worker specification.
3. Dispatch Worker to implement `tests/e2e/conftest.py` and `tests/e2e/test_svelte_viewer.py` and verify headless execution via `uv run pytest tests/e2e/`.
4. Dispatch Reviewers, Challengers, and Forensic Auditor.
5. Synthesize gate review and mark M3 as DONE.

## Phase 3: Milestone M4 Final Acceptance & Documentation Audit
1. Dispatch Explorer/Worker to produce comprehensive audit report in `docs/pipeline_audit_report.md` and update architecture documentation.
2. Execute full acceptance suite: 87 baseline unit tests + air-gap tests + print fidelity tests + Playwright E2E tests with 0 failures and 0 regressions.
3. Reviewer and Auditor gate verification.
4. Mark M4 as DONE.

## Phase 4: Final Synthesis & Notification
1. Aggregate all findings, test results, and audit verification.
2. Send completion message to parent/Sentinel with executive summary.
