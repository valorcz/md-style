# Dispatch: Explorer M2.2 - Engine Dossier Header Guard & Fingerprint

## Task
Investigate the exact Python engine modifications for Milestone M2:
1. Scoping `_should_build_dossier_header()` and dossier badge/examiner labels in `core/engine.py:365-390` strictly to forensic themes (`is_forensic`).
2. Passing `fingerprint=bundler.fingerprint` to `build_cdp_header_footer_templates()` in `core/engine.py:316`.
3. Adding `examples/school-report-sample.md` to `samples-pdf` target in `Makefile`.

## Scope
- Inspect `core/engine.py`.
- Inspect `Makefile`.
- Formulate exact code changes and regression safety.

## Inputs
- `/home/valor/Devel/personal/md-style/.agents/teamwork/ORIGINAL_REQUEST.md`
- `/home/valor/Devel/personal/md-style/.agents/teamwork/PROJECT.md`
- `/home/valor/Devel/personal/md-style/.agents/teamwork/explorer_survey_2/handoff.md`

## Output
Write report to: `/home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m2_2/handoff.md`


## 2026-10-11T11:01:13Z
You are Explorer M2.2 investigating engine dossier header logic and fingerprint propagation for Milestone M2.

Your working directory is: /home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m2_2/
Authoritative requirements: /home/valor/Devel/personal/md-style/.agents/teamwork/ORIGINAL_REQUEST.md
Project plan: /home/valor/Devel/personal/md-style/.agents/teamwork/PROJECT.md
Survey report: /home/valor/Devel/personal/md-style/.agents/teamwork/explorer_survey_2/handoff.md
Please read /home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m2_2/DISPATCH.md.

Formulate the exact code modifications for:
1. Restricting _should_build_dossier_header() and forensic badge/examiner labels in core/engine.py strictly to forensic themes.
2. Passing fingerprint=bundler.fingerprint to build_cdp_header_footer_templates() in core/engine.py:316.
3. Adding examples/school-report-sample.md to Makefile samples-pdf target.

Write your findings and patch to:
/home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m2_2/handoff.md

Update progress.md while working, and message back when done.
