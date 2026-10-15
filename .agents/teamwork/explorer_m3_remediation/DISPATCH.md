## 2026-10-11T17:36:00Z
You are explorer_m3_remediation (Role: teamwork_preview_explorer).
Your working directory is: /home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m3_remediation/
The authoritative requirements are at: /home/valor/Devel/personal/md-style/.agents/teamwork/ORIGINAL_REQUEST.md
The project breakdown is at: /home/valor/Devel/personal/md-style/.agents/teamwork/PROJECT.md

### MANDATORY: Full Forensic Audit & Challenger Failure Reports to Read
1. `/home/valor/Devel/personal/md-style/.agents/teamwork/auditor_m3_1/handoff.md` (FULL FORENSIC AUDIT REPORT: INTEGRITY VIOLATION)
2. `/home/valor/Devel/personal/md-style/.agents/teamwork/challenger_m3_1/handoff.md` (CHALLENGER REPORT: REQUEST_CHANGES)

### Mission
Investigate and design exact remediation recipes for the integrity violations and defects:
1. **Air-Gap Strictness (Zero WAN requests from browser)**:
   - Identify how inline SVG `<style>` blocks (e.g. from `beautiful-mermaid`) containing `@import url("https://fonts.googleapis.com...")` leak through `core/bundler.py`.
   - Provide exact code changes for `core/bundler.py` to strip/sanitize all external `@import url(...)` and font URLs when `allow_online=False` across the entire document (including inside SVGs).
   - Provide exact changes in `tests/e2e/conftest.py` to add `--host-resolver-rules=MAP * ^NOTFOUND` in browser launch args.
2. **Corrupted LocalStorage Recovery (`store.ts:persist`)**:
   - Provide exact fix in `viewer/src/annotations/store.ts` (and bundled js) so `JSON.parse(existing)` is locally try-caught and corrupted data does not prevent `localStorage.setItem` or saving new annotations.
3. **MarginGutter Card Edit Overlap**:
   - Provide exact fix in `viewer/src/annotations/MarginGutter.svelte` (and bundled js) to ensure an editing card cannot be covered by adjacent cards (e.g. `z-index: 20` on `.gutter-item` containing active `.card-edit-box` or dynamic positioning).
4. **Adversarial Test Suite Cleanup**:
   - Ensure all 14 tests in `tests/e2e/` (`test_svelte_viewer.py` + `test_adversarial_e2e.py`) pass with 0 xfails.
5. **Milestone M4 Preparation**:
   - Outline the full structure and required sections for `docs/pipeline_audit_report.md` covering architecture, air-gap guarantees, findings, fixes, and test metrics.

Write your report in /home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m3_remediation/handoff.md.
Send completion message to parent orchestrator.
