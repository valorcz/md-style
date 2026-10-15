# Dispatch: Survey 3 - Core Pipeline Architecture & Existing Tests

## Task
Investigate the core compilation pipeline, air-gap strictness, and existing test suite for Requirement 3 (R3).

## Scope
1. Examine `core/engine.py`, `core/bundler.py`, `core/parser/`, and `core/kb/`.
2. Check existing test suite (locate the 87 unit tests, check runner: `pytest`, `uv run pytest`, etc., and current test health).
3. Investigate air-gap strictness: identify any external network requests, remote asset fetches (fonts, CDN scripts, images), or asset inlining mechanisms.
4. Investigate parser resilience against malformed inputs (invalid frontmatter, deeply nested Pandoc callouts, unmatched fenced code blocks).
5. Inspect CLI diagnostics, exit codes, build timing metrics, and existing documentation in `docs/`.

## Inputs
- `/home/valor/Devel/personal/md-style/.agents/teamwork/ORIGINAL_REQUEST.md`

## Output
Write your findings and actionable recommendations to:
`/home/valor/Devel/personal/md-style/.agents/teamwork/explorer_survey_3/handoff.md`


## 2026-10-11T10:17:34Z
You are Explorer 3 investigating the core compilation pipeline, air-gap strictness, resilience against malformed inputs, and the existing test suite for md-style.

Your working directory is: /home/valor/Devel/personal/md-style/.agents/teamwork/explorer_survey_3/
The authoritative requirements are recorded at: /home/valor/Devel/personal/md-style/.agents/teamwork/ORIGINAL_REQUEST.md
Please read /home/valor/Devel/personal/md-style/.agents/teamwork/explorer_survey_3/DISPATCH.md for your assigned scope.

Investigate:
1. Modular compilation pipeline: core/engine.py, core/bundler.py, core/parser/, core/kb/.
2. Existing unit test suite: locate the 87 tests, run them or inspect how they run (e.g. pytest or uv run pytest), and check their current status.
3. Air-gap strictness: identify if any external network requests exist in themes, bundler, or viewer, and how zero external network requests are guaranteed.
4. Parser resilience on malformed inputs (invalid frontmatter, deeply nested Pandoc callouts, unmatched fenced blocks).
5. CLI diagnostics, exit codes, build timing metrics, and existing documentation in docs/.
6. What is needed to implement hardening, offline tests, and produce the audit report in docs/ satisfying R3 acceptance criteria.

Write your comprehensive findings and recommendations to:
/home/valor/Devel/personal/md-style/.agents/teamwork/explorer_survey_3/handoff.md

Update your progress.md while working. When done, send a message to the orchestrator summarizing your findings.
