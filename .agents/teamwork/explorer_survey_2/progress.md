# Progress: Survey 2 - W3C Paged Media & Vector PDF Print Fidelity

Last visited: 2026-10-11T10:28:00Z
Status: Investigation complete, writing handoff report

## Completed Investigation Steps
1. Examined all themes in `styles/forensic/`, `styles/svj/`, `styles/general/` (including `school`).
2. Traced Chromium CDP vector PDF compilation (`core/engine.py` -> `viewer/scripts/print-pdf.mjs`) and Paged.js preview (`viewer/src/App.svelte` -> `viewer/src/paged/paged-handlers.ts`).
3. Identified root cause of duplicate page numbers in `svj/invitation` (`@bottom-right` margin box conflict in `invitation.css`).
4. Identified bug in `core/engine.py` causing forensic dossier badges and examiner labels to leak into non-forensic themes (`school-report-sample.md`).
5. Identified missing `fingerprint` parameter in `core/engine.py` CDP compilation call causing empty SHA-256 hash in forensic footers.
6. Analyzed break-inside avoidance for tables, diagrams, callouts, and signature blocks; identified gaps in `paged.css` and `print.css`.
7. Analyzed ordered list continuation mechanism in Paged.js (`UnifiedHeaderFooterHandler`) and Chromium CDP native fragmentation.
8. Evaluated PDF inspection tools: identified `/usr/bin/pdfinfo` and `/usr/bin/pdftotext -bbox-layout` (zero dependencies, sub-millisecond bounding box XML) and `pypdf` as optional dev dependency.
9. Formulated automated test architecture for R2 satisfying all acceptance criteria.
