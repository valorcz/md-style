# Project Plan: md-style Architectural Audit, Headless E2E, and Print Fidelity Verification

## Objective
Deliver an enterprise-grade automated verification suite, headless E2E testing framework, print fidelity audit harness, and pipeline architectural hardening with 0 regressions on the existing 87 unit tests, as specified in `ORIGINAL_REQUEST.md`.

## Execution Tracks
1. **Survey Phase (Current)**
   - Explorer 1: Frontend & Svelte Viewer runtime (annotations, InspectorDrawer, TableToolbar, export bundle, inspectable pills).
   - Explorer 2: Paged Media, PDF compilation, styles/themes (forensic, svj, general), header/footer numbering, break rules.
   - Explorer 3: Core modular compilation pipeline (`engine.py`, `bundler.py`, `parser/`, `kb/`), air-gap verification, 87 unit tests status.

2. **Decomposition & Project Mapping**
   - Synthesize survey findings into `PROJECT.md` Feature Inventory & Architecture.
   - Establish Dual Track: Implementation Track and E2E Testing Track.

3. **Milestone Execution**
   - Milestone R1: Headless Browser E2E Test Suite (Playwright/Puppeteer).
   - Milestone R2: W3C Paged Media & Vector PDF Print Fidelity Verification Harness.
   - Milestone R3: Pipeline Architectural Audit, Hardening & Air-Gap Enforcement.
   - Milestone Acceptance: Full regression run (87 tests), offline check, and documentation report in `docs/`.

4. **Final Gate & Reporting**
   - Verification across all acceptance criteria.
   - Synthesis of audit report into `docs/`.
   - Sentinel notification.
