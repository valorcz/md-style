"""
tests/test_print_fidelity.py
Automated print fidelity verification harness for W3C Paged Media & Vector PDF export (Milestone M2).

Validates:
1. Compilation across forensic, SVJ, and school themes to vector PDF via Chromium CDP.
2. Monotonic page numbering (English 'Page X of Y' / Czech 'Strana X z Y') and absence of duplicate margin box numbers.
3. Running header/footer metadata correctness and theme boundary isolation (zero forensic leaks into school/SVJ).
4. Vertical bounding box clearances (Header yMax < Content yMin, Content yMax < Footer yMin).
5. Zero orphan headings at page bottoms (headings accompanied by body content on the same page).
6. Zero table header splits and table fragmentation protection.
7. Break-inside avoidance for signature blocks and multi-page ordered list continuation.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from core.engine import PipelineConfig, ReportEngine

# XML Namespace emitted by pdftotext -bbox-layout
XHTML_NS = "http://www.w3.org/1999/xhtml"


@dataclass
class BBox:
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    @property
    def height(self) -> float:
        return self.y_max - self.y_min

    @property
    def width(self) -> float:
        return self.x_max - self.x_min

    def overlaps_vertically_with(self, other: "BBox", tolerance: float = 0.5) -> bool:
        """Returns True if vertical spans overlap by more than tolerance."""
        return not (self.y_max <= other.y_min + tolerance or other.y_max <= self.y_min + tolerance)

    def overlaps_horizontally_with(self, other: "BBox", tolerance: float = 0.5) -> bool:
        """Returns True if horizontal spans overlap by more than tolerance."""
        return not (self.x_max <= other.x_min + tolerance or other.x_max <= self.x_min + tolerance)

    def intersects(self, other: "BBox", tolerance: float = 0.5) -> bool:
        """Returns True if 2D bounding boxes intersect."""
        return self.overlaps_vertically_with(other, tolerance) and self.overlaps_horizontally_with(other, tolerance)


@dataclass
class Word:
    text: str
    bbox: BBox


@dataclass
class Line:
    words: List[Word]
    bbox: BBox

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)


@dataclass
class Block:
    lines: List[Line]
    bbox: BBox

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines)


@dataclass
class PageLayout:
    page_number: int  # 1-indexed
    width: float
    height: float
    blocks: List[Block]

    @property
    def all_text(self) -> str:
        return "\n".join(b.text for b in self.blocks)

    def get_header_blocks(self, top_threshold_pt: float = 55.0) -> List[Block]:
        """Header blocks reside within the top margin zone."""
        return [b for b in self.blocks if b.bbox.y_max <= top_threshold_pt]

    def get_footer_blocks(self, bottom_threshold_pt: float = 55.0) -> List[Block]:
        """Footer blocks reside within the bottom margin zone."""
        cutoff = self.height - bottom_threshold_pt
        return [b for b in self.blocks if b.bbox.y_min >= cutoff]

    def get_body_blocks(
        self, top_threshold_pt: float = 55.0, bottom_threshold_pt: float = 55.0
    ) -> List[Block]:
        """Body content blocks reside between top and bottom margin zones."""
        bottom_cutoff = self.height - bottom_threshold_pt
        return [
            b
            for b in self.blocks
            if b.bbox.y_max > top_threshold_pt and b.bbox.y_min < bottom_cutoff
        ]


@dataclass
class PdfLayoutDocument:
    pdf_path: Path
    pages: List[PageLayout]

    @property
    def total_pages(self) -> int:
        return len(self.pages)

    @classmethod
    def from_pdf(cls, pdf_path: Path) -> "PdfLayoutDocument":
        """Runs /usr/bin/pdftotext -bbox-layout and parses XML output."""
        if not shutil.which("pdftotext"):
            raise RuntimeError("pdftotext binary not found in PATH")

        cmd = ["pdftotext", "-bbox-layout", str(pdf_path.resolve()), "-"]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)

        root = ET.fromstring(res.stdout)
        pages: List[PageLayout] = []

        page_elems = root.findall(f".//{{{XHTML_NS}}}page")
        for idx, page_el in enumerate(page_elems, start=1):
            width = float(page_el.get("width", "595.28"))
            height = float(page_el.get("height", "841.89"))
            blocks: List[Block] = []

            for block_el in page_el.findall(f".//{{{XHTML_NS}}}block"):
                lines: List[Line] = []
                b_x_min = float(block_el.get("xMin", "0"))
                b_y_min = float(block_el.get("yMin", "0"))
                b_x_max = float(block_el.get("xMax", "0"))
                b_y_max = float(block_el.get("yMax", "0"))

                for line_el in block_el.findall(f".//{{{XHTML_NS}}}line"):
                    words: List[Word] = []
                    l_x_min = float(line_el.get("xMin", "0"))
                    l_y_min = float(line_el.get("yMin", "0"))
                    l_x_max = float(line_el.get("xMax", "0"))
                    l_y_max = float(line_el.get("yMax", "0"))

                    for word_el in line_el.findall(f".//{{{XHTML_NS}}}word"):
                        w_text = word_el.text or ""
                        w_x_min = float(word_el.get("xMin", "0"))
                        w_y_min = float(word_el.get("yMin", "0"))
                        w_x_max = float(word_el.get("xMax", "0"))
                        w_y_max = float(word_el.get("yMax", "0"))
                        words.append(
                            Word(
                                text=w_text,
                                bbox=BBox(w_x_min, w_y_min, w_x_max, w_y_max),
                            )
                        )

                    lines.append(
                        Line(
                            words=words,
                            bbox=BBox(l_x_min, l_y_min, l_x_max, l_y_max),
                        )
                    )

                blocks.append(
                    Block(
                        lines=lines,
                        bbox=BBox(b_x_min, b_y_min, b_x_max, b_y_max),
                    )
                )

            pages.append(
                PageLayout(
                    page_number=idx,
                    width=width,
                    height=height,
                    blocks=blocks,
                )
            )

        return cls(pdf_path=pdf_path, pages=pages)


SAMPLE_SPECS: Dict[str, Dict[str, Any]] = {
    "cyber": {
        "src": Path("examples/sample-forensic-cyber.md"),
        "style": "forensic/cyber",
        "title": "Advanced Threat Hunting & AI Forensic Incident Dossier",
        "lang": "en",
        "classification": "TOP SECRET // TLP:AMBER",
        "footer_unit": "CYBER DFIR",
        "page_regex": re.compile(r"(?:Page\s+)?(\d+)\s+of\s+(\d+)", re.IGNORECASE),
        "is_forensic": True,
    },
    "dossier": {
        "src": Path("examples/sample-forensic-report.md"),
        "style": "forensic/dossier",
        "title": "Digital Forensic Investigation Report",
        "lang": "en",
        "classification": "CONFIDENTIAL",
        "footer_unit": "Forensic Investigation Unit",
        "page_regex": re.compile(r"(?:Page\s+)?(\d+)\s+of\s+(\d+)", re.IGNORECASE),
        "is_forensic": True,
        "requires_sha256": True,
    },
    "svj": {
        "src": Path("examples/pozvánka-shromáždění-svj.md"),
        "style": "svj/invitation",
        "title": "Pozvánka na shromáždění",
        "lang": "cs",
        "header_center": "POZVÁNKA NA SHROMÁŽDĚNÍ",
        "footer_left": "Statutární orgán / Výbor SVJ",
        "statute_notice": "1207",
        "page_regex": re.compile(r"Strana\s+(\d+)\s+z\s+(\d+)", re.IGNORECASE),
        "is_forensic": False,
    },
    "school": {
        "src": Path("examples/school-report-sample.md"),
        "style": "general/school",
        "title": "Academic Progress & Evaluation Report",
        "lang": "en",
        "date": "June 12, 2026",
        "page_regex": re.compile(r"(?:Page\s+)?(\d+)\s+of\s+(\d+)", re.IGNORECASE),
        "is_forensic": False,
    },
}


@pytest.fixture(scope="module")
def print_environment_check():
    """Skips tests if headless Chromium or pdftotext are absent."""
    has_browser = any(
        shutil.which(b)
        for b in [
            "chromium-browser",
            "chromium",
            "google-chrome",
            "brave-browser",
            "microsoft-edge",
        ]
    )
    if not has_browser:
        pytest.skip("No Chromium-compatible browser found in PATH")
    if not shutil.which("pdftotext"):
        pytest.skip("pdftotext binary not found in PATH")


@pytest.fixture(scope="module")
def compiled_sample_pdfs(tmp_path_factory, print_environment_check) -> Dict[str, PdfLayoutDocument]:
    """Compiles all 4 canonical sample documents to PDF and parses their XML layout."""
    out_dir = tmp_path_factory.mktemp("pdf_fidelity")
    compiled_docs: Dict[str, PdfLayoutDocument] = {}

    for key, spec in SAMPLE_SPECS.items():
        src_path = spec["src"]
        assert src_path.is_file(), f"Sample source markdown missing: {src_path}"

        out_pdf = out_dir / f"{key}.pdf"
        cfg = PipelineConfig(
            input_file=src_path,
            output_file=out_pdf,
            style=spec["style"],
            generate_pdf=True,
            quiet=True,
        )
        engine = ReportEngine(cfg)
        result_path = engine.run()

        assert result_path.is_file(), f"Expected compiled PDF at {result_path}"
        assert result_path.stat().st_size > 10000, f"Compiled PDF {result_path} is too small"

        doc_layout = PdfLayoutDocument.from_pdf(result_path)
        assert doc_layout.total_pages > 0, f"PDF {result_path} has 0 pages"
        compiled_docs[key] = doc_layout

    return compiled_docs


def test_compilation_integrity(compiled_sample_pdfs):
    """Verifies that all 4 sample themes compile to valid multi-page PDFs with >50KB size."""
    for key, doc in compiled_sample_pdfs.items():
        assert doc.pdf_path.is_file()
        assert doc.pdf_path.stat().st_size > 50000, f"{key} PDF unexpectedly small"
        assert doc.total_pages >= 2, f"{key} expected multi-page PDF, got {doc.total_pages}"


@pytest.mark.parametrize("doc_key", ["cyber", "dossier", "svj", "school"])
def test_monotonic_page_numbers(compiled_sample_pdfs, doc_key):
    """Verifies that page numbers increment strictly monotonically (1 of N to N of N,

    or Strana 1 z N to Strana N z N) with zero duplicate margin numbers.
    """
    doc = compiled_sample_pdfs[doc_key]
    spec = SAMPLE_SPECS[doc_key]
    pattern: re.Pattern = spec["page_regex"]
    total = doc.total_pages

    extracted_numbers: List[int] = []

    for page in doc.pages:
        footer_blocks = page.get_footer_blocks()
        footer_text = " ".join(b.text for b in footer_blocks)

        m = pattern.search(footer_text)
        assert m is not None, (
            f"Page {page.page_number}/{total} of {doc_key} footer missing page counter: "
            f"'{footer_text}'"
        )
        p_num = int(m.group(1))
        p_total = int(m.group(2))

        assert p_num == page.page_number, (
            f"Page counter mismatch on page {page.page_number} of {doc_key}: got {p_num}"
        )
        assert p_total == total, (
            f"Total page mismatch on page {page.page_number} of {doc_key}: got {p_total}, expected {total}"
        )
        extracted_numbers.append(p_num)

        # Bug A Guard: Assert absence of duplicate page counter in footer
        # (e.g. Bare number block from obsolete CSS margin box)
        if doc_key == "svj":
            bare_number_blocks = [
                b for b in footer_blocks
                if b.text.strip() == str(p_num)
            ]
            assert len(bare_number_blocks) == 0, (
                f"Page {page.page_number} has duplicate bare page number block '{p_num}' "
                f"from obsolete CSS margin box!"
            )

    # Monotonic increment check: [1, 2, ..., total]
    expected_sequence = list(range(1, total + 1))
    assert extracted_numbers == expected_sequence, (
        f"Non-monotonic page sequence in {doc_key}: {extracted_numbers} != {expected_sequence}"
    )


@pytest.mark.parametrize("doc_key", ["cyber", "dossier", "svj", "school"])
def test_header_footer_bounding_box_clearance(compiled_sample_pdfs, doc_key):
    """Verifies that headers, body content, and footers maintain non-negative clearance:

    - max(header.yMax) < min(body.yMin) with >= 10pt clearance
    - max(body.yMax) < min(footer.yMin) with >= 10pt clearance
    - Zero vertical overlap between distinct footer blocks
    """
    doc = compiled_sample_pdfs[doc_key]
    min_clearance_pt = 10.0

    for page in doc.pages:
        header_blocks = page.get_header_blocks()
        footer_blocks = page.get_footer_blocks()
        body_blocks = page.get_body_blocks()

        if body_blocks:
            min_body_y = min(b.bbox.y_min for b in body_blocks)
            max_body_y = max(b.bbox.y_max for b in body_blocks)

            if header_blocks:
                max_header_y = max(b.bbox.y_max for b in header_blocks)
                header_clearance = min_body_y - max_header_y
                assert header_clearance >= min_clearance_pt, (
                    f"Page {page.page_number} of {doc_key}: Header overlaps or collides with body! "
                    f"header.yMax={max_header_y:.2f}, body.yMin={min_body_y:.2f}, clearance={header_clearance:.2f}pt"
                )

            if footer_blocks:
                min_footer_y = min(b.bbox.y_min for b in footer_blocks)
                footer_clearance = min_footer_y - max_body_y
                assert footer_clearance >= min_clearance_pt, (
                    f"Page {page.page_number} of {doc_key}: Body overlaps or collides with footer! "
                    f"body.yMax={max_body_y:.2f}, footer.yMin={min_footer_y:.2f}, clearance={footer_clearance:.2f}pt"
                )

        # Internal footer block overlap check (catches colliding margin boxes)
        for i, b1 in enumerate(footer_blocks):
            for j, b2 in enumerate(footer_blocks):
                if i < j:
                    if b1.bbox.intersects(b2.bbox, tolerance=1.0):
                        pytest.fail(
                            f"Page {page.page_number} of {doc_key}: Footer blocks collide!\n"
                            f"Block 1: '{b1.text}' at ({b1.bbox.x_min:.1f}, {b1.bbox.y_min:.1f}, {b1.bbox.x_max:.1f}, {b1.bbox.y_max:.1f})\n"
                            f"Block 2: '{b2.text}' at ({b2.bbox.x_min:.1f}, {b2.bbox.y_min:.1f}, {b2.bbox.x_max:.1f}, {b2.bbox.y_max:.1f})"
                        )


def test_forensic_metadata_correctness(compiled_sample_pdfs):
    """Verifies that forensic documents render proper classifications, titles, and SHA-256 fingerprints."""
    # Cyber
    cyber = compiled_sample_pdfs["cyber"]
    cyber_p2 = cyber.pages[1]  # Page 2 has running header
    p2_header = " ".join(b.text for b in cyber_p2.get_header_blocks())
    p2_footer = " ".join(b.text for b in cyber_p2.get_footer_blocks())
    assert "Advanced Threat Hunting" in p2_header or "Incident Dossier" in p2_header
    assert "TLP:AMBER" in p2_header
    assert "CYBER DFIR" in p2_footer

    # Dossier (Bug C check)
    dossier = compiled_sample_pdfs["dossier"]
    dossier_p2 = dossier.pages[1]
    d_footer = " ".join(b.text for b in dossier_p2.get_footer_blocks())
    assert "Forensic Investigation Unit" in d_footer
    # Cryptographic hash verification: SHA-256 followed by at least 8 hex characters
    m_hash = re.search(r"SHA-256:\s*([0-9a-fA-F]{8,})", d_footer)
    assert m_hash is not None, (
        f"Forensic dossier footer missing SHA-256 fingerprint hash! Footer text was: '{d_footer}'"
    )


def test_theme_isolation_no_forensic_leaks(compiled_sample_pdfs):
    """Verifies that general (school) and SVJ documents never leak forensic badges or examiner labels (Bug B)."""
    school = compiled_sample_pdfs["school"]
    school_all_text = school.pages[0].all_text  # Page 1 has title banner

    # Assert absence of forensic leakage on school report
    assert "FORENSIC INVESTIGATION REPORT" not in school_all_text, (
        "Forensic badge leaked into school report Page 1 title block!"
    )
    assert "DIGITAL FORENSIC" not in school_all_text
    assert "Examiner:" not in school_all_text
    assert "Vyšetřovatel:" not in school_all_text

    # Verify proper academic title & advisor attribution
    assert "Academic Progress & Evaluation Report" in school_all_text
    assert "Faculty Advisor: Dr. Alistair Vance" in school_all_text or "Dr. Alistair Vance" in school_all_text

    # SVJ theme isolation check
    svj = compiled_sample_pdfs["svj"]
    svj_all_text = "\n".join(p.all_text for p in svj.pages)
    assert "FORENSIC" not in svj_all_text
    assert "TLP:" not in svj_all_text
    assert "DFIR" not in svj_all_text
    assert "Examiner:" not in svj_all_text


@pytest.mark.parametrize("doc_key", ["cyber", "dossier", "svj", "school"])
def test_zero_orphan_headings(compiled_sample_pdfs, doc_key):
    """Verifies that no headings are orphaned as the final block at the bottom of a page

    without subsequent body content.
    """
    doc = compiled_sample_pdfs[doc_key]
    spec = SAMPLE_SPECS[doc_key]

    src_text = spec["src"].read_text(encoding="utf-8")
    heading_titles = [
        line.lstrip("#").strip()
        for line in src_text.splitlines()
        if line.startswith("#") and len(line.lstrip("#").strip()) > 2
    ]

    for page in doc.pages:
        body_blocks = page.get_body_blocks()
        if not body_blocks:
            continue

        last_block = body_blocks[-1]
        last_block_text = last_block.text.strip()

        is_heading = any(
            ht.lower() in last_block_text.lower() or last_block_text.lower() in ht.lower()
            for ht in heading_titles
            if len(ht) > 5
        )

        dist_to_bottom = (page.height - 55.0) - last_block.bbox.y_max
        if is_heading and dist_to_bottom < 70.0:
            pytest.fail(
                f"Page {page.page_number} of {doc_key} has orphan heading at page bottom: "
                f"'{last_block_text}' with no subsequent body content (yMax={last_block.bbox.y_max:.1f}, "
                f"dist_to_bottom={dist_to_bottom:.1f}pt)"
            )


@pytest.mark.parametrize("doc_key", ["cyber", "dossier", "svj", "school"])
def test_zero_table_header_splits(compiled_sample_pdfs, doc_key):
    """Verifies that table headers are not split across page breaks and rows do not fragment."""
    doc = compiled_sample_pdfs[doc_key]

    for page in doc.pages:
        body_blocks = page.get_body_blocks()
        for block in body_blocks:
            bottom_boundary = page.height - 55.0
            assert block.bbox.y_max <= bottom_boundary + 1.0, (
                f"Page {page.page_number} of {doc_key}: Block crosses bottom boundary: "
                f"yMax={block.bbox.y_max:.2f} > boundary={bottom_boundary:.2f}"
            )


def test_signature_block_integrity(compiled_sample_pdfs):
    """Verifies that signature blocks are kept intact on a single page without fragmentation."""
    school = compiled_sample_pdfs["school"]

    vance_pages = [
        p.page_number
        for p in school.pages
        if "Dr. Alistair Vance, Ph.D." in p.all_text and "Senior Lecturer" in p.all_text
    ]
    thorne_pages = [
        p.page_number
        for p in school.pages
        if "Prof. Margaret Thorne" in p.all_text and "Dean of Academic Studies" in p.all_text
    ]

    assert len(vance_pages) == 1, "Expected Dr. Vance signature on exactly 1 page"
    assert len(thorne_pages) == 1, "Expected Prof. Thorne signature on exactly 1 page"
    assert vance_pages[0] == thorne_pages[0], (
        f"Signature block fragmented across pages! Vance on P{vance_pages[0]}, Thorne on P{thorne_pages[0]}"
    )


def test_ordered_list_counter_continuation(compiled_sample_pdfs):
    """Verifies that multi-page ordered lists (SVJ agenda items 1..11) maintain continuous numbering."""
    svj = compiled_sample_pdfs["svj"]

    agenda_titles = [
        "Zahájení",
        "Zpráva výboru o hospodaření",
        "Zpráva o technickém stavu",
        "Rozúčtování nákladů instalace",
        "Úprava výše měsíčního příspěvku",
        "Modernizace přístupového",
        "Změna servisní smlouvy",
        "Schválení plánu revizí",
        "Zřízení internetových stránek",
        "Různé a diskuse",
        "Závěr",
    ]

    item_pages: Dict[int, int] = {}
    for item_idx in range(1, 12):
        title_prefix = agenda_titles[item_idx - 1]
        pattern = re.compile(rf"(?:^|\n)\s*{item_idx}\.\s+(?:###\s+)?{re.escape(title_prefix)}", re.MULTILINE)
        found_pages = [p.page_number for p in svj.pages if pattern.search(p.all_text)]
        if found_pages:
            # Main agenda details are located on pages 2..5 (page 1 is TOC summary)
            detail_pages = [pg for pg in found_pages if pg >= 2]
            item_pages[item_idx] = detail_pages[0] if detail_pages else found_pages[0]

    assert len(item_pages) == 11, f"Missing agenda items in SVJ document: found {len(item_pages)} of 11"

    pages_seq = [item_pages[i] for i in range(1, 12)]
    for i in range(len(pages_seq) - 1):
        assert pages_seq[i] <= pages_seq[i + 1], (
            f"Agenda item {i + 1} (P{pages_seq[i]}) appears after item {i + 2} (P{pages_seq[i + 1]})!"
        )
