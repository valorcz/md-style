# Dispatch: Worker M2 - Print Fidelity & Theme Fixes

## Objective
Implement all code modifications, stylesheet updates, and the automated print verification test suite for Milestone M2:
1. Stylesheet fixes:
   - Remove obsolete `@bottom-right` margin box in `styles/svj/invitation/invitation.css` (lines 316–333).
   - Add universal break-inside avoidance rules in `styles/base/paged.css` and `styles/base/print.css` (.signature-block, .signature-line, .signature-row, .committee-signature, .sign-off, .callout, .admonition, .kpi-card, .kpi-grid, figure).
2. Engine fixes:
   - Scope `_should_build_dossier_header()` and dossier badge/examiner labels in `core/engine.py` strictly to forensic themes (`is_forensic`).
   - Store `self.fingerprint` in `core/bundler.py` and pass `fingerprint=getattr(bundler, "fingerprint", "")` to `build_cdp_header_footer_templates()` in `core/engine.py:_compile_pdf()`.
   - Add `examples/school-report-sample.md` to `samples-pdf` target in `Makefile`.
3. Automated Print Verification Harness:
   - Deploy `tests/test_print_fidelity.py` (from `explorer_m2_3/proposed_test_print_fidelity.py`).
4. Run verification:
   - `uv run pytest tests/test_print_fidelity.py -v`
   - `uv run pytest` (all tests pass with 0 regressions).

## Owned Files
- `styles/svj/invitation/invitation.css`
- `styles/base/paged.css`
- `styles/base/print.css`
- `core/engine.py`
- `core/bundler.py`
- `Makefile`
- `tests/test_print_fidelity.py`

## Inputs
- `/home/valor/Devel/personal/md-style/.agents/teamwork/ORIGINAL_REQUEST.md`
- `/home/valor/Devel/personal/md-style/.agents/teamwork/PROJECT.md`
- `/home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m2_1/handoff.md`
- `/home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m2_2/handoff.md`
- `/home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m2_3/handoff.md`
- `/home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m2_3/proposed_test_print_fidelity.py`

## Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Output
Write your handoff report to:
`/home/valor/Devel/personal/md-style/.agents/teamwork/worker_m2/handoff.md`
Include build/test commands executed, verbatim test outputs, and verification results.


## 2026-10-11T11:13:14Z
You are the Implementation Worker for Milestone M2 (Print Fidelity & Theme Fixes).

Your working directory is: /home/valor/Devel/personal/md-style/.agents/teamwork/worker_m2/
Authoritative requirements: /home/valor/Devel/personal/md-style/.agents/teamwork/ORIGINAL_REQUEST.md
Project plan: /home/valor/Devel/personal/md-style/.agents/teamwork/PROJECT.md
Dispatch details: /home/valor/Devel/personal/md-style/.agents/teamwork/worker_m2/DISPATCH.md

You own exclusively:
- styles/svj/invitation/invitation.css
- styles/base/paged.css
- styles/base/print.css
- core/engine.py
- core/bundler.py
- Makefile
- tests/test_print_fidelity.py

Input specifications and patches from Explorers:
- /home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m2_1/handoff.md
- /home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m2_2/handoff.md
- /home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m2_3/handoff.md
- /home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m2_3/proposed_test_print_fidelity.py

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Tasks:
1. Apply stylesheet fixes:
   - Remove obsolete @bottom-right margin box in styles/svj/invitation/invitation.css (lines 316-333) to prevent duplicate page numbers.
   - Expand universal break-inside avoidance rules in styles/base/paged.css and styles/base/print.css.
2. Apply engine & bundler fixes:
   - Scope _should_build_dossier_header() and dossier badge/examiner labels in core/engine.py strictly to forensic themes.
   - Store self.fingerprint in core/bundler.py and pass fingerprint=getattr(bundler, "fingerprint", "") in core/engine.py:_compile_pdf().
   - Add examples/school-report-sample.md to Makefile samples-pdf target.
3. Deploy tests/test_print_fidelity.py from explorer_m2_3/proposed_test_print_fidelity.py.
4. Run tests:
   - uv run pytest tests/test_print_fidelity.py -v
   - uv run pytest
   Verify 0 regressions and that all existing tests and new print tests pass cleanly.

Report your changes, commands run, and verbatim test outputs in:
/home/valor/Devel/personal/md-style/.agents/teamwork/worker_m2/handoff.md

Update progress.md while working, and message back when done.
