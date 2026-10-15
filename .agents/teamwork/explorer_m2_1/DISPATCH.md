# Dispatch: Explorer M2.1 - Print Styles & Break Avoidance

## Task
Investigate the exact stylesheet modifications for Milestone M2:
1. Removal of duplicate `@bottom-right` margin box in `styles/svj/invitation/invitation.css`.
2. Universal break-inside avoidance rules in `styles/base/paged.css` and `styles/base/print.css` (`.signature-block`, `.signature-line`, `.signature-row`, `.committee-signature`, `.sign-off`, `.callout`, `.admonition`, `.kpi-card`, `.kpi-grid`, `figure`).

## Scope
- Inspect `styles/svj/invitation/invitation.css`.
- Inspect `styles/base/paged.css` and `styles/base/print.css`.
- Formulate exact CSS selectors and property changes.
- Provide verification commands.

## Inputs
- `/home/valor/Devel/personal/md-style/.agents/teamwork/ORIGINAL_REQUEST.md`
- `/home/valor/Devel/personal/md-style/.agents/teamwork/PROJECT.md`
- `/home/valor/Devel/personal/md-style/.agents/teamwork/explorer_survey_2/handoff.md`

## Output
Write report to: `/home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m2_1/handoff.md`

## 2026-10-11T11:01:13Z
You are Explorer M2.1 investigating print stylesheets and break-inside avoidance for Milestone M2.

Your working directory is: /home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m2_1/
Authoritative requirements: /home/valor/Devel/personal/md-style/.agents/teamwork/ORIGINAL_REQUEST.md
Project plan: /home/valor/Devel/personal/md-style/.agents/teamwork/PROJECT.md
Survey report: /home/valor/Devel/personal/md-style/.agents/teamwork/explorer_survey_2/handoff.md
Please read /home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m2_1/DISPATCH.md.

Formulate the exact code modifications for:
1. Removing obsolete @bottom-right in styles/svj/invitation/invitation.css to eliminate duplicate page numbers.
2. Expanding break-inside avoidance rules in styles/base/paged.css and styles/base/print.css (.signature-block, .signature-line, .signature-row, .committee-signature, .sign-off, .callout, .admonition, .kpi-card, .kpi-grid, figure).

Write your findings and patch to:
/home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m2_1/handoff.md

Update progress.md while working, and message back when done.
