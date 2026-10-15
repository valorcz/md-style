# Dispatch: Explorer M2.3 - Automated Print Verification Harness

## Task
Investigate and design the automated print verification test harness `tests/test_print_fidelity.py` for Milestone M2:
1. Compilation of sample documents across forensic, SVJ, and school themes to PDF.
2. Parsing and inspection of compiled PDFs using `/usr/bin/pdftotext -bbox-layout` and `xml.etree.ElementTree`.
3. Verifying:
   - Monotonic page numbers (`1 of N` to `N of N`, `Strana 1 z N` to `Strana N z N`).
   - Headers match metadata without forensic leaks in school reports.
   - Zero orphan headers at page bottoms.
   - Zero table header splits and `thead` repetition.
   - Zero content/footer and header/content bounding box overlaps (`yMax < yMin`).

## Inputs
- `/home/valor/Devel/personal/md-style/.agents/teamwork/ORIGINAL_REQUEST.md`
- `/home/valor/Devel/personal/md-style/.agents/teamwork/PROJECT.md`
- `/home/valor/Devel/personal/md-style/.agents/teamwork/explorer_survey_2/handoff.md`

## Output
Write report to: `/home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m2_3/handoff.md`


## 2026-10-11T11:01:13Z
You are Explorer M2.3 investigating the automated print verification test harness for Milestone M2.

Your working directory is: /home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m2_3/
Authoritative requirements: /home/valor/Devel/personal/md-style/.agents/teamwork/ORIGINAL_REQUEST.md
Project plan: /home/valor/Devel/personal/md-style/.agents/teamwork/PROJECT.md
Survey report: /home/valor/Devel/personal/md-style/.agents/teamwork/explorer_survey_2/handoff.md
Please read /home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m2_3/DISPATCH.md.

Formulate the complete test harness implementation for tests/test_print_fidelity.py:
1. Compiles sample documents across forensic/cyber, forensic/dossier, svj/invitation, and general/school to PDF.
2. Inspects compiled PDFs with /usr/bin/pdftotext -bbox-layout and xml.etree.ElementTree.
3. Tests monotonic page numbers, header metadata correctness, zero orphan headers, zero table header splits, and zero header/footer overlaps.

Write your findings and test blueprint to:
/home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m2_3/handoff.md

Update progress.md while working, and message back when done.
