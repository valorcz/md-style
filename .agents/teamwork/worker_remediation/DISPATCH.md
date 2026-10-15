## 2026-10-11T18:05:00Z
You are worker_remediation (Role: teamwork_preview_worker).
Your working directory is: /home/valor/Devel/personal/md-style/.agents/teamwork/worker_remediation/
The authoritative requirements are at: /home/valor/Devel/personal/md-style/.agents/teamwork/ORIGINAL_REQUEST.md
The project breakdown is at: /home/valor/Devel/personal/md-style/.agents/teamwork/PROJECT.md
The remediation recipes and M4 blueprint are at: /home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m3_remediation/handoff.md

### MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### Tasks to Implement

#### 1. Air-Gap Sanitization in `core/bundler.py` (Recipe 1)
- Add `sanitize_inline_styles(self, html_content: str) -> str` to `AssetBundler`.
- In `assemble()`, call `processed_html = self.sanitize_inline_styles(processed_html)`.
- Strip remote `@import url(...)`, remote font URLs, and remote `<link>` tags when `allow_online=False`, including inside inline SVGs.

#### 2. Chromium Strict Air-Gap in `tests/e2e/conftest.py` (Recipe 2)
- Add `"--host-resolver-rules=MAP * ^NOTFOUND"` to `browser_type_launch_args` in `tests/e2e/conftest.py`.

#### 3. LocalStorage Corruption Resilience in `viewer/src/annotations/store.ts` (Recipe 3)
- In `persist()`, wrap `JSON.parse(existing)` in a local `try/catch` block so `currentTombstones = []` on parse error without preventing `localStorage.setItem` from executing.

#### 4. MarginGutter Card Edit Overlap in `MarginGutter.svelte` & `AnnotationCard.svelte` (Recipe 4)
- In `MarginGutter.svelte`, add `editingCardId` tracking and expand estimated height to 220px when in edit mode.
- In `MarginGutter.svelte` styles, add `z-index: 20` on `.gutter-item:has(.card-edit-box)` or `:hover`/`:focus-within`.
- In `AnnotationCard.svelte`, dispatch `editToggle` events on edit toggle, cancel, and save.
- Recompile viewer bundle: run `make build-viewer` (or `cd viewer && npm run build`) to update `core/assets/viewer.bundle.js` and `core/assets/viewer.bundle.css`.

#### 5. Un-xfail Adversarial E2E Tests in `tests/e2e/test_adversarial_e2e.py` (Recipe 5)
- Remove `@pytest.mark.xfail` on `test_adversarial_corrupted_local_storage`.
- Remove `@pytest.mark.xfail` on `test_adversarial_margin_gutter_edit_overlap`.

#### 6. Milestone M4: Comprehensive Pipeline Audit Report in `docs/pipeline_audit_report.md`
- Author comprehensive, publication-grade audit report `docs/pipeline_audit_report.md` following the Section 4 blueprint from `explorer_m3_remediation/handoff.md`:
  - Section 1: Executive Summary & Audit Scope (findings table, metrics summary)
  - Section 2: Pipeline Architecture & Decoupling Overview (engine, bundler, kb, svelte viewer, print CDP)
  - Section 3: Air-Gap Guarantees & Network Security Analysis (FontBundler, IconService, Beautiful-Mermaid SVG leak remediation, `--host-resolver-rules`)
  - Section 4: Interactive Viewer Hardening & Headless E2E Verification (all 8 baseline scenarios + 6 adversarial scenarios documented)
  - Section 5: W3C Paged Media & Vector PDF Print Fidelity (bounding boxes, monotonic counters, break avoidance, signature blocks, SVJ fix)
  - Section 6: Input Resilience & Robustness (nested callouts, code fences, frontmatter, timing diagnostics, exit codes)
  - Section 7: Verification Matrix & Reproduction Instructions (exact commands, counts, pass rates)

#### 7. Verification Execution
- Run `uv run pytest tests/e2e/ -v` (assert 14/14 pass cleanly with 0 xfails and 0 errors).
- Run `uv run pytest` (assert all 205+ tests pass cleanly with 0 regressions).
- Run `make samples-pdf` (assert all 4 PDFs compile cleanly).

#### 8. Handoff
- Document all changes, file paths, test commands, and exact outputs in `/home/valor/Devel/personal/md-style/.agents/teamwork/worker_remediation/handoff.md`.
- Send completion message to parent orchestrator.
