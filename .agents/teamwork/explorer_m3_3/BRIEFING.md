# BRIEFING — 2026-10-11T16:05:00Z

## Mission
Investigate storage persistence, embedded script re-hydration, clean bundle export (exportUpdatedHtmlBundle), and formulate Playwright E2E test recipes for Milestone M3.

## 🔒 My Identity
- Archetype: explorer
- Roles: teamwork_preview_explorer
- Working directory: /home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m3_3
- Original parent: 2a97336d-5074-4aef-a112-3c18a332ea47
- Milestone: M3 (Headless Browser E2E Test Suite - R1)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Only write files within /home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m3_3/
- Provide exact file paths, line numbers, code snippets, and Playwright verification recipes

## Current Parent
- Conversation ID: 2a97336d-5074-4aef-a112-3c18a332ea47
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `viewer/src/annotations/store.ts` (storage key derivation, schema, persist, edit, delete, tombstones)
  - `viewer/src/annotations/AnnotationCard.svelte` (editing UI, action buttons, Markdown preview)
  - `viewer/src/annotations/export-bundle.ts` (`exportUpdatedHtmlBundle`, transient root stripping, script tag escaping)
  - `viewer/src/InspectorDrawer.svelte` (Review tab, comments list, export button)
  - `core/bundler.py` (`#md-style-annotations` embedding, `doc-fingerprint` generation)
- **Key findings**:
  - Storage key is `md-style:annotations:${docKey}` where `docKey` is SHA256 `doc-fingerprint` from meta tag.
  - Storage schema is `{ annotations: [...], tombstones: [...] }`. Deletions append IDs to `tombstones` array rather than marking items `_deleted: true`.
  - Rehydration in `init()` merges embedded `#md-style-annotations` and `localStorage`, filtering both by `tombstoneSet` so deleted embedded items never resurrect.
  - `exportUpdatedHtmlBundle` cleans DOM (removes `#md-style-viewer-root`, `.table-toolbar-container`, `.annotation-popover`, `.margin-gutter`, unwraps mark tags, resets body classes, sanitizes JSON with `\u003c`, and inserts a clean empty `#md-style-viewer-root`).
  - Playwright test recipes formulated for card editing, storage persistence, tombstone suppression, and 0-error bundle rehydration.
- **Unexplored areas**: None. All DISPATCH tasks completed.

## Key Decisions Made
- Confirmed that tombstones are stored in a dedicated `tombstones: string[]` array in `localStorage` rather than an item property.
- Documented the exact Playwright test recipes with explicit assertions for `tests/e2e/test_svelte_viewer.py`.

## Artifact Index
- DISPATCH.md — Dispatch instructions
- BRIEFING.md — Situational awareness
- progress.md — Liveness heartbeat
- handoff.md — Final investigation report with 5-component structure and full Playwright recipes
