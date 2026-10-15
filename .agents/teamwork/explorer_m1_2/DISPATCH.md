# Dispatch: Explorer M1.2 - Callout Parser Nesting & Title Deduplication

## Task
Investigate the exact changes needed for recursive callout parsing and title deduplication in `core/parser/plugins/callouts.py`.

## Scope
1. Review `/home/valor/Devel/personal/md-style/.agents/teamwork/PROJECT.md` (Features 5, 6).
2. Review findings from `/home/valor/Devel/personal/md-style/.agents/teamwork/explorer_survey_3/handoff.md`.
3. Inspect `core/parser/plugins/callouts.py` and `tests/test_callout_plugin.py`.
4. Formulate the precise token transformation logic in `transform_blockquote_callouts`:
   - Recursive transformation of inner blockquotes so `> [!NOTE] > > [!WARNING]` generates nested `<div class="callout ...">`.
   - Single-line alert title deduplication: strip `custom_title` from inline tokens so the title is not duplicated in the body paragraph.
5. Provide test cases to verify these behaviors and ensure 0 regressions.

## Inputs
- `/home/valor/Devel/personal/md-style/.agents/teamwork/ORIGINAL_REQUEST.md`
- `/home/valor/Devel/personal/md-style/.agents/teamwork/PROJECT.md`
- `/home/valor/Devel/personal/md-style/.agents/teamwork/explorer_survey_3/handoff.md`

## Output
Write report to: `/home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m1_2/handoff.md`
