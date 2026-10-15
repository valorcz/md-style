# Dispatch: Explorer M1.1 - Air-Gap Enforcement & Offline Testing

## Task
Investigate the exact changes needed for strict air-gap enforcement across the compilation pipeline and formulate the automated offline test suite.

## Scope
1. Review `/home/valor/Devel/personal/md-style/.agents/teamwork/PROJECT.md` (Features 1, 2, 3, 4).
2. Review findings from `/home/valor/Devel/personal/md-style/.agents/teamwork/explorer_survey_3/handoff.md`.
3. Provide exact code modification proposals for:
   - `core/kb/resolvers/ip_resolver.py`: guard `_resolve_ptr` behind `allow_online`.
   - `core/fonts.py`: propagate `allow_online`, return `None` without HTTP requests when `allow_online=False`, clean font embedding.
   - `core/icons.py`: propagate `allow_online`, skip GitHub CDN fetch, use fallback SVG.
   - `core/bundler.py`: pass `allow_online` to `FontBundler`.
4. Provide the exact test specifications for `tests/test_airgap_offline.py` (socket interception, cold cache test, 0 remote scripts/links).
5. Ensure 0 regressions on existing unit tests.

## Inputs
- `/home/valor/Devel/personal/md-style/.agents/teamwork/ORIGINAL_REQUEST.md`
- `/home/valor/Devel/personal/md-style/.agents/teamwork/PROJECT.md`
- `/home/valor/Devel/personal/md-style/.agents/teamwork/explorer_survey_3/handoff.md`

## Output
Write report to: `/home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m1_1/handoff.md`


## 2026-10-11T10:31:35Z
You are Explorer M1.1 investigating Air-Gap Enforcement and Offline Testing for Milestone M1 of md-style.

Your working directory is: /home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m1_1/
Authoritative requirements: /home/valor/Devel/personal/md-style/.agents/teamwork/ORIGINAL_REQUEST.md
Project plan: /home/valor/Devel/personal/md-style/.agents/teamwork/PROJECT.md
Survey findings: /home/valor/Devel/personal/md-style/.agents/teamwork/explorer_survey_3/handoff.md
Please read /home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m1_1/DISPATCH.md.

Formulate the exact implementation plan and code specifications for:
1. Air-gap strictness in core/kb/resolvers/ip_resolver.py, core/fonts.py, core/icons.py, core/bundler.py.
2. The complete test suite tests/test_airgap_offline.py asserting zero external WAN requests.
3. Verification that all 87 baseline tests continue to pass.

Write your findings and implementation blueprint to:
/home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m1_1/handoff.md

Update progress.md while working, and send a message when complete.


## 2026-10-11T10:40:49Z
**Context**: Milestone M1 Air-Gap Investigation
**Content**: Checking in on the status of your investigation and patch verification for air-gap enforcement.
**Action**: Please let me know your current progress, complete your handoff.md, and send your completion report.
