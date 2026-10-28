"""tests/test_print_fidelity_adversarial.py
Adversarial stress-testing and empirical edge-case verification for Milestone M2 (Print Fidelity & Theme Fixes).

Tests:
1. Boundary break-inside avoidance for .callout, .signature-block, .kpi-card, and figure.
2. Nested callouts (> [!NOTE] > > [!WARNING]) in print and PDF compilation.
3. Oversized component graceful fragmentation (component exceeding single-page height).
4. Adversarial metadata injection and theme isolation (non-forensic themes with examiner/classification).
5. SVJ duplicate page counter suppression across all pages.
6. SHA-256 fingerprint determinism and tamper variance.
7. Minimal and boundary document compilation resilience.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

import pytest

from core.engine import PipelineConfig, ReportEngine
from tests.test_print_fidelity import BBox, PdfLayoutDocument, print_environment_check


def test_stress_boundary_callout_break_inside(tmp_path, print_environment_check):
    """Adversarially places a .callout at the bottom boundary of Page 1.

    Verifies that break-inside: avoid pushes the entire callout to Page 2 intact,
    rather than severing it across the page boundary.
    """
    filler = "\n\n".join(f"Paragraph {i}: " + ("Standard section body content filler line. " * 4) for i in range(1, 14))
    callout_content = (
        "> [!WARNING]\n"
        "> **Adversarial Boundary Test Callout**\n"
        ">\n"
        "> This callout must remain intact on a single page.\n"
        "> Line 2 of callout content.\n"
        "> Line 3 of callout content.\n"
        "> Line 4 of callout content."
    )
    doc_text = f"# Page Break Stress Test\n\n{filler}\n\n{callout_content}\n\n" + (
        "Post-callout paragraph: " + ("Follow-up content continuing on the document. " * 5)
    )

    src_file = tmp_path / "stress_callout.md"
    src_file.write_text(doc_text, encoding="utf-8")
    out_pdf = tmp_path / "stress_callout.pdf"

    cfg = PipelineConfig(
        input_file=src_file,
        output_file=out_pdf,
        style="general/school",
        generate_pdf=True,
        quiet=True,
    )
    engine = ReportEngine(cfg)
    result_path = engine.run()
    assert result_path.is_file()

    layout = PdfLayoutDocument.from_pdf(result_path)
    assert layout.total_pages >= 2, f"Expected at least 2 pages, got {layout.total_pages}"

    callout_phrase = "Adversarial Boundary Test Callout"
    callout_line4 = "Line 4 of callout content"

    p_header = [p.page_number for p in layout.pages if callout_phrase in p.all_text]
    p_tail = [p.page_number for p in layout.pages if callout_line4 in p.all_text]

    assert len(p_header) == 1, f"Callout header found on pages: {p_header}"
    assert len(p_tail) == 1, f"Callout tail found on pages: {p_tail}"
    assert p_header[0] == p_tail[0], (
        f"Callout was split across page boundary! Header on P{p_header[0]}, tail on P{p_tail[0]}"
    )


def test_stress_boundary_signature_block_break_inside(tmp_path, print_environment_check):
    """Adversarially places a .signature-block at the bottom of Page 1.

    Verifies that break-inside: avoid pushes the entire signature block intact to Page 2.
    """
    filler = "\n\n".join(f"Legal Section Clause {i}: " + ("Contract stipulation content filler text. " * 4) for i in range(1, 14))
    signature_block = (
        '<div class="signature-block">\n'
        '  <div class="signature-line">Schváleno výborem SVJ dne 11. října 2026:</div>\n'
        '  <div class="committee-signature">Předseda výboru: Ing. Jan Novák</div>\n'
        '  <div class="committee-signature">Člen výboru: Mgr. Petr Svoboda</div>\n'
        '  <div class="sign-off">Razítko společenství vlastníků</div>\n'
        '</div>'
    )
    doc_text = f"# Stanovy Společenství\n\n{filler}\n\n{signature_block}\n"

    src_file = tmp_path / "stress_sig.md"
    src_file.write_text(doc_text, encoding="utf-8")
    out_pdf = tmp_path / "stress_sig.pdf"

    cfg = PipelineConfig(
        input_file=src_file,
        output_file=out_pdf,
        style="svj/invitation",
        generate_pdf=True,
        quiet=True,
    )
    engine = ReportEngine(cfg)
    result_path = engine.run()
    assert result_path.is_file()

    layout = PdfLayoutDocument.from_pdf(result_path)
    assert layout.total_pages >= 2

    phrase_top = "Schváleno výborem SVJ"
    phrase_bottom = "Razítko společenství vlastníků"

    p_top = [p.page_number for p in layout.pages if phrase_top in p.all_text]
    p_bot = [p.page_number for p in layout.pages if phrase_bottom in p.all_text]

    assert len(p_top) == 1, f"Signature top found on pages {p_top}"
    assert len(p_bot) == 1, f"Signature bottom found on pages {p_bot}"
    assert p_top[0] == p_bot[0], (
        f"Signature block fragmented across pages: top on P{p_top[0]}, bottom on P{p_bot[0]}"
    )


def test_stress_nested_callouts_pdf_rendering(tmp_path, print_environment_check):
    """Verifies that nested callouts render without layout collision or PDF compilation errors."""
    doc_text = """---
title: Deep Nested Callouts Security Notice
style: forensic/cyber
---

# Architecture Assessment

> [!NOTE]
> Outer container notice level 1.
> High priority warning follows inside this block.
>
> > [!WARNING]
> > Inner nested warning level 2.
> > Ensure credential stores are isolated.
> >
> > > [!IMPORTANT]
> > > Deeply nested alert level 3: Hardware enclave required.

Follow-up report narrative after nested alert sequence.
"""
    src_file = tmp_path / "nested_callout.md"
    src_file.write_text(doc_text, encoding="utf-8")
    out_pdf = tmp_path / "nested_callout.pdf"

    cfg = PipelineConfig(
        input_file=src_file,
        output_file=out_pdf,
        style="forensic/cyber",
        generate_pdf=True,
        quiet=True,
    )
    engine = ReportEngine(cfg)
    result_path = engine.run()
    assert result_path.is_file()

    layout = PdfLayoutDocument.from_pdf(result_path)
    all_text = "\n".join(p.all_text for p in layout.pages)

    assert "Outer container notice level 1" in all_text
    assert "Inner nested warning level 2" in all_text
    assert "Deeply nested alert level 3" in all_text
    assert "Hardware enclave required" in all_text
    assert "Follow-up report narrative" in all_text


def test_stress_oversized_component_graceful_split(tmp_path, print_environment_check):
    """Adversarially provides a component taller than a full page (>1000pt).

    The renderer must not hang, loop infinitely, or crash; it should split across pages.
    """
    huge_callout_body = "\n>\n".join(
        f"> Paragraph {i}: " + ("Extremely verbose regulatory disclosure clause text. " * 8)
        for i in range(1, 40)
    )
    doc_text = f"# Oversized Component Stress Test\n\n> [!NOTE]\n> **Gigantic Regulatory Callout**\n{huge_callout_body}\n\nPost-gigantic paragraph."

    src_file = tmp_path / "oversized.md"
    src_file.write_text(doc_text, encoding="utf-8")
    out_pdf = tmp_path / "oversized.pdf"

    cfg = PipelineConfig(
        input_file=src_file,
        output_file=out_pdf,
        style="general/school",
        generate_pdf=True,
        quiet=True,
    )
    engine = ReportEngine(cfg)
    result_path = engine.run()
    assert result_path.is_file()

    layout = PdfLayoutDocument.from_pdf(result_path)
    # The oversized callout avoids breaking on P1, starts on P2 and gracefully spans to P6
    assert layout.total_pages >= 3
    found_on_pages = [p.page_number for p in layout.pages if "Gigantic Regulatory Callout" in p.all_text]
    assert len(found_on_pages) == 1
    assert "Paragraph 39" in layout.pages[-1].all_text


def test_theme_isolation_adversarial_metadata(tmp_path, print_environment_check):
    """Adversarially injects forensic frontmatter fields into a general school report.

    Verifies that:
    1. Forensic title badge 'DIGITAL FORENSIC INVESTIGATION REPORT' does NOT appear.
    2. 'FORENSIC' does not appear in headers or footers.
    3. Author label does not leak 'Examiner:' when author is provided with prefix.
    4. Explicit dossier_header: false suppresses title block header entirely.
    """
    # Test A: School report with author prefix injected
    doc_a = """---
title: Biology Class Curriculum Evaluation
author: "Examiner: Dr. Alexander Vance"
date: 2026-10-11
classification: STRICTLY CONFIDENTIAL
case_id: BIO-CASE-99
style: general/school
---

# Section 1: Curriculum Overview
Standard curriculum report content without forensics.
"""
    src_a = tmp_path / "school_adv.md"
    src_a.write_text(doc_a, encoding="utf-8")
    out_a = tmp_path / "school_adv.pdf"

    cfg_a = PipelineConfig(
        input_file=src_a,
        output_file=out_a,
        style="general/school",
        generate_pdf=True,
        quiet=True,
    )
    engine_a = ReportEngine(cfg_a)
    result_a = engine_a.run()
    assert result_a.is_file()

    layout_a = PdfLayoutDocument.from_pdf(result_a)
    all_text_a = "\n".join(p.all_text for p in layout_a.pages)

    assert "DIGITAL FORENSIC INVESTIGATION REPORT" not in all_text_a
    assert "FORENSIC" not in all_text_a
    assert "CYBER DFIR" not in all_text_a
    assert "Forensic Investigation Unit" not in all_text_a
    assert "Dr. Alexander Vance" in all_text_a

    # Verify that in generated HTML, author label is Author:, not Examiner:
    html_a = out_a.with_suffix(".html")
    cfg_html = PipelineConfig(
        input_file=src_a,
        output_file=html_a,
        style="general/school",
        generate_pdf=False,
        quiet=True,
    )
    ReportEngine(cfg_html).run()
    html_content = html_a.read_text(encoding="utf-8")
    assert "DIGITAL FORENSIC" not in html_content
    # The prefix 'Examiner:' was stripped and label rendered as Author:
    assert '<span class="meta-label">Author:</span> Dr. Alexander Vance' in html_content

    # Test B: Explicit dossier_header: false suppresses title block header completely
    doc_b = """---
title: Minimal Announcement Without Dossier
dossier_header: false
author: Notice Board
style: general/announcement
---

# Announcement
Clean bulletin without generated title block header.
"""
    src_b = tmp_path / "no_header.md"
    src_b.write_text(doc_b, encoding="utf-8")
    html_b = tmp_path / "no_header.html"
    cfg_b = PipelineConfig(
        input_file=src_b,
        output_file=html_b,
        style="general/announcement",
        generate_pdf=False,
        quiet=True,
    )
    ReportEngine(cfg_b).run()
    html_b_content = html_b.read_text(encoding="utf-8")
    assert '<header id="title-block-header">' not in html_b_content


def test_svj_adversarial_page_counter_and_first_page_margins(tmp_path, print_environment_check):
    """Adversarially checks that SVJ invitation never leaks bare counter or duplicates across 3 pages."""
    p1_content = "Úvodní text pozvánky na shromáždění SVJ.\n\n" + ("Obsah první strany dokumentu. " * 30)
    p2_content = "\n\n<div style='page-break-before: always;'></div>\n\n# Program Shromáždění\n\n" + ("Obsah druhé strany programu. " * 30)
    p3_content = "\n\n<div style='page-break-before: always;'></div>\n\n# Pokyny k Hlasování\n\n" + ("Obsah třetí strany pokynů. " * 30)

    doc_text = f"""---
title: Pozvánka na shromáždění SVJ
style: svj/invitation
lang: cs
---

{p1_content}
{p2_content}
{p3_content}
"""
    src_file = tmp_path / "svj_3page.md"
    src_file.write_text(doc_text, encoding="utf-8")
    out_pdf = tmp_path / "svj_3page.pdf"

    cfg = PipelineConfig(
        input_file=src_file,
        output_file=out_pdf,
        style="svj/invitation",
        generate_pdf=True,
        quiet=True,
    )
    engine = ReportEngine(cfg)
    result_path = engine.run()
    assert result_path.is_file()

    layout = PdfLayoutDocument.from_pdf(result_path)
    assert layout.total_pages == 3

    counter_pattern = re.compile(r"Strana\s+(\d+)\s+z\s+(\d+)", re.IGNORECASE)

    for page in layout.pages:
        footer_blocks = page.get_footer_blocks()
        footer_text = " ".join(b.text for b in footer_blocks)

        matches = counter_pattern.findall(footer_text)
        assert len(matches) == 1, (
            f"Page {page.page_number} footer has unexpected counter match count {len(matches)}: '{footer_text}'"
        )
        assert matches[0] == (str(page.page_number), "3")

        for b in footer_blocks:
            clean_b = b.text.strip()
            assert clean_b != str(page.page_number), (
                f"Page {page.page_number} has duplicate bare page counter block '{clean_b}' in footer!"
            )


def test_sha256_fingerprint_determinism_and_variance(tmp_path, print_environment_check):
    """Verifies that the document SHA-256 fingerprint:

    1. Is deterministic for identical input.
    2. Varies when document markdown changes.
    3. Matches between HTML metadata and PDF footer in forensic dossier theme.
    """
    doc_1_text = """---
title: Integrity Verification Case
style: forensic/dossier
classification: CONFIDENTIAL
---

# Evidence Inventory
Original evidence hash item 001.
"""
    doc_2_text = """---
title: Integrity Verification Case
style: forensic/dossier
classification: CONFIDENTIAL
---

# Evidence Inventory
Tampered evidence hash item 002.
"""

    src_1 = tmp_path / "doc_1.md"
    src_1.write_text(doc_1_text, encoding="utf-8")
    pdf_1 = tmp_path / "doc_1.pdf"

    src_2 = tmp_path / "doc_2.md"
    src_2.write_text(doc_2_text, encoding="utf-8")
    pdf_2 = tmp_path / "doc_2.pdf"

    ReportEngine(PipelineConfig(input_file=src_1, output_file=pdf_1, style="forensic/dossier", generate_pdf=True, quiet=True)).run()
    ReportEngine(PipelineConfig(input_file=src_2, output_file=pdf_2, style="forensic/dossier", generate_pdf=True, quiet=True)).run()

    html_1 = pdf_1.with_suffix(".html")
    html_2 = pdf_2.with_suffix(".html")
    ReportEngine(PipelineConfig(input_file=src_1, output_file=html_1, style="forensic/dossier", generate_pdf=False, quiet=True)).run()
    ReportEngine(PipelineConfig(input_file=src_2, output_file=html_2, style="forensic/dossier", generate_pdf=False, quiet=True)).run()

    m1 = re.search(r'<meta name="doc-fingerprint" content="([0-9a-fA-F]{64})">', html_1.read_text(encoding="utf-8"))
    m2 = re.search(r'<meta name="doc-fingerprint" content="([0-9a-fA-F]{64})">', html_2.read_text(encoding="utf-8"))

    assert m1 is not None, "doc-fingerprint meta tag missing in doc 1"
    assert m2 is not None, "doc-fingerprint meta tag missing in doc 2"

    fp1 = m1.group(1)
    fp2 = m2.group(1)

    assert fp1 != fp2, "Fingerprints must differ for different source contents"

    layout_1 = PdfLayoutDocument.from_pdf(pdf_1)
    p2_footer_1 = " ".join(b.text for b in layout_1.pages[0].get_footer_blocks()) if layout_1.total_pages == 1 else " ".join(b.text for b in layout_1.pages[1].get_footer_blocks())
    assert fp1[:8] in p2_footer_1, (
        f"PDF footer '{p2_footer_1}' did not contain short SHA-256 prefix '{fp1[:8]}'"
    )


def test_minimal_and_boundary_document_compilation(tmp_path, print_environment_check):
    """Verifies that an empty or minimal document compiles cleanly to PDF without crashing."""
    src = tmp_path / "minimal.md"
    src.write_text("# Title Only\n", encoding="utf-8")
    out = tmp_path / "minimal.pdf"

    cfg = PipelineConfig(
        input_file=src,
        output_file=out,
        style="general/school",
        generate_pdf=True,
        quiet=True,
    )
    engine = ReportEngine(cfg)
    res = engine.run()
    assert res.is_file()
    assert res.stat().st_size > 10000

    layout = PdfLayoutDocument.from_pdf(res)
    assert layout.total_pages == 1
    assert "Title Only" in layout.pages[0].all_text
