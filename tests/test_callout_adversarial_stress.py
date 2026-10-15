"""
tests/test_callout_adversarial_stress.py
Adversarial stress-testing suite for the Callout Parser plugin (Milestone M1).
Empirically tests pathological, extreme, and edge-case markdown scenarios:
- Deeply nested alerts (5 to 10+ levels)
- Mixed alert and standard blockquote nesting
- Complex formatted titles and absolute title deduplication
- Malformed, corrupted, and boundary alert syntax
- Integration with fenced code, tables, lists, and raw HTML inside callouts
- Interoperability between container callouts (:::) and blockquote alerts (>)
- Tag balancing, HTML tree well-formedness, and zero-crash guarantees.
"""

import re
from html.parser import HTMLParser
from typing import List, Tuple, Dict, Any
import pytest
from core.parser import MarkdownParser


class CalloutHTMLValidator(HTMLParser):
    """
    Strict HTML well-formedness and callout tag balance oracle.
    Verifies that all tags balance properly (LIFO), void elements are respected,
    and callout opening/closing tags strictly match.
    """
    VOID_TAGS = {
        'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
        'link', 'meta', 'param', 'source', 'track', 'wbr'
    }

    def __init__(self):
        super().__init__()
        self.stack: List[Tuple[str, Dict[str, str]]] = []
        self.errors: List[str] = []
        self.callout_depth: int = 0
        self.max_callout_depth: int = 0
        self.callout_open_count: int = 0
        self.callout_close_count: int = 0

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str]]) -> None:
        attrs_dict = dict(attrs)
        classes = attrs_dict.get('class', '').split()
        if tag == 'div' and 'callout' in classes:
            self.callout_depth += 1
            self.callout_open_count += 1
            if self.callout_depth > self.max_callout_depth:
                self.max_callout_depth = self.callout_depth

        if tag not in self.VOID_TAGS:
            self.stack.append((tag, attrs_dict))

    def handle_endtag(self, tag: str) -> None:
        if tag in self.VOID_TAGS:
            return
        if not self.stack:
            self.errors.append(f"Unexpected closing tag </{tag}> with empty stack")
            return
        top_tag, top_attrs = self.stack.pop()
        if top_tag != tag:
            self.errors.append(f"Mismatched closing tag: expected </{top_tag}>, got </{tag}>")

        classes = top_attrs.get('class', '').split()
        if top_tag == 'div' and 'callout' in classes:
            self.callout_depth -= 1
            self.callout_close_count += 1

    def validate(self, html_str: str) -> Tuple[bool, List[str]]:
        self.reset()
        self.stack = []
        self.errors = []
        self.callout_depth = 0
        self.max_callout_depth = 0
        self.callout_open_count = 0
        self.callout_close_count = 0
        self.feed(html_str)
        if self.stack:
            self.errors.append(f"Unclosed tags at EOF: {[t[0] for t in self.stack]}")
        return len(self.errors) == 0, self.errors


def extract_callout_content(html_str: str) -> str:
    """Helper extracting the inner body within <div class="callout-content">."""
    m = re.search(r'<div class="callout-content">\s*(.*?)\s*</div>', html_str, re.DOTALL)
    return m.group(1) if m else ""


# ============================================================================
# 1. DEEPLY NESTED ALERTS (5+ LEVELS)
# ============================================================================

def test_stress_deeply_nested_5_levels():
    """Verify 5 levels of nested alerts maintain strict tag balance and proper hierarchy."""
    p = MarkdownParser()
    v = CalloutHTMLValidator()

    src = """
> [!NOTE] Level 1 Note
> Level 1 body
> > [!WARNING] Level 2 Warning
> > Level 2 body
> > > [!CAUTION] Level 3 Caution
> > > Level 3 body
> > > > [!TIP] Level 4 Tip
> > > > Level 4 body
> > > > > [!IMPORTANT] Level 5 Important
> > > > > Level 5 body text
"""
    html_out, _, _ = p.render(src)
    ok, errs = v.validate(html_out)
    assert ok, f"Tag balancing validation failed: {errs}"
    assert v.max_callout_depth == 5
    assert v.callout_open_count == 5
    assert v.callout_close_count == 5

    # Check hierarchy order
    pos1 = html_out.find("callout-note")
    pos2 = html_out.find("callout-warning")
    pos3 = html_out.find("callout-caution")
    pos4 = html_out.find("callout-tip")
    pos5 = html_out.find("callout-important")
    assert 0 <= pos1 < pos2 < pos3 < pos4 < pos5
    assert "Level 5 body text" in html_out


def test_stress_deeply_nested_7_levels_including_proposal():
    """Verify 7 levels of mixed alerts including a proposal with ballot generation."""
    p = MarkdownParser()
    v = CalloutHTMLValidator()

    src = """
> [!NOTE] Level 1
> > [!WARNING] Level 2
> > > [!CAUTION] Level 3
> > > > [!TIP] Level 4
> > > > > [!IMPORTANT] Level 5
> > > > > > [!CRITICAL] Level 6
> > > > > > > [!PROPOSAL] Level 7 Proposal
> > > > > > > Proposal body
"""
    html_out, _, _ = p.render(src)
    ok, errs = v.validate(html_out)
    assert ok, f"Tag balancing validation failed: {errs}"
    assert v.max_callout_depth == 7
    assert v.callout_open_count == 7
    assert v.callout_close_count == 7

    assert 'class="proposal-ballot"' in html_out
    assert "Proposal body" in html_out


def test_stress_scaling_10_level_nesting():
    """Stress-test recursive callout parsing scaling up to 10 nesting levels."""
    p = MarkdownParser()
    v = CalloutHTMLValidator()

    types = ["NOTE", "WARNING", "CAUTION", "TIP", "IMPORTANT", "CRITICAL", "INFO", "SUCCESS", "DANGER", "FINDING"]
    src = ""
    for i, t in enumerate(types):
        indent = "> " * (i + 1)
        src += f"{indent}[!{t}] Level {i+1} Title\n"
        src += f"{indent}Level {i+1} Body\n"

    html_out, _, _ = p.render(src)
    ok, errs = v.validate(html_out)
    assert ok, f"Tag balancing validation failed: {errs}"
    assert v.max_callout_depth == 10
    assert v.callout_open_count == 10
    assert v.callout_close_count == 10
    assert "Level 10 Body" in html_out


# ============================================================================
# 2. MIXED BLOCKQUOTE AND ALERT FORMATS
# ============================================================================

def test_stress_alternating_blockquotes_and_alerts():
    """Verify alternating standard blockquotes and alerts across 5 levels."""
    p = MarkdownParser()
    v = CalloutHTMLValidator()

    src = """
> Standard Quote L1
>
> > [!NOTE] Alert L2
> > Note content
> >
> > > Standard Quote L3
> > >
> > > > [!WARNING] Alert L4
> > > > Warning content
> > > >
> > > > > Standard Quote L5
> > > > > Deep quote content
"""
    html_out, _, _ = p.render(src)
    ok, errs = v.validate(html_out)
    assert ok, f"Tag balancing validation failed: {errs}"

    assert v.callout_open_count == 2
    assert v.callout_close_count == 2
    assert html_out.count("<blockquote>") == 3
    assert html_out.count("</blockquote>") == 3
    assert "Deep quote content" in html_out


def test_stress_sibling_alerts_inside_parent_alert():
    """Verify multiple sibling alerts inside a single parent alert container."""
    p = MarkdownParser()
    v = CalloutHTMLValidator()

    src = """
> [!NOTE] Parent Note
> Parent introductory text.
>
> > [!TIP] Sibling Child 1
> > First tip content.
>
> > [!WARNING] Sibling Child 2
> > Second warning content.
>
> > [!CAUTION] Sibling Child 3
> > Third caution content.
>
> Parent concluding text.
"""
    html_out, _, _ = p.render(src)
    ok, errs = v.validate(html_out)
    assert ok, f"Tag balancing validation failed: {errs}"

    assert v.callout_open_count == 4
    assert v.callout_close_count == 4
    assert v.max_callout_depth == 2

    # Check parent content encloses all siblings and trailing text
    assert "Parent introductory text." in html_out
    assert "Sibling Child 1" in html_out
    assert "Sibling Child 2" in html_out
    assert "Sibling Child 3" in html_out
    assert "Parent concluding text." in html_out


def test_stress_alert_inside_standard_quote_with_surrounding_text():
    """Verify standard blockquote with text before and after an embedded alert."""
    p = MarkdownParser()
    v = CalloutHTMLValidator()

    src = """
> Preceding standard quote paragraph.
>
> > [!WARNING] Embedded Callout
> > Callout body.
>
> Trailing standard quote paragraph.
"""
    html_out, _, _ = p.render(src)
    ok, errs = v.validate(html_out)
    assert ok, f"Tag balancing validation failed: {errs}"

    assert v.callout_open_count == 1
    assert v.callout_close_count == 1
    assert html_out.count("<blockquote>") == 1
    assert html_out.count("</blockquote>") == 1

    # Outer blockquote must start before callout and end after callout
    bq_start = html_out.find("<blockquote>")
    callout_start = html_out.find('class="callout')
    bq_end = html_out.rfind("</blockquote>")
    assert bq_start < callout_start < bq_end


# ============================================================================
# 3. COMPLEX TITLES AND DEDUPLICATION
# ============================================================================

def test_stress_complex_titles_single_line_deduplication():
    """Verify single-line alerts with rich formatting in titles do not duplicate in body."""
    p = MarkdownParser()
    v = CalloutHTMLValidator()

    test_titles = [
        "**Bold Title**",
        "*Italicized Title*",
        "`code_token()` Title",
        "[Hyperlink Title](https://example.com)",
        "Emoji Title 🚀 ⚠️ 🛡️",
        "HTML Characters <script> & 'quotes' \"double\"",
        "Regex Tokens (parens) [brackets] *stars* +plus+ ?question?",
    ]

    for title in test_titles:
        src = f"> [!NOTE] {title}"
        html_out, _, _ = p.render(src)
        ok, errs = v.validate(html_out)
        assert ok, f"Tag balancing failed for title '{title}': {errs}"

        # Title must appear in callout-title span (escaped)
        assert '<span class="callout-title">' in html_out
        # Title must NOT appear as a paragraph inside callout-content
        content = extract_callout_content(html_out)
        assert "<p>" not in content, f"Body contained unexpected paragraph for single-line alert with title '{title}'"
        assert title not in content, f"Title was duplicated in body for title '{title}'"


def test_stress_title_with_blank_line_and_body_deduplication():
    """Verify title separated from body by an empty quote line does not duplicate."""
    p = MarkdownParser()
    src = """
> [!NOTE] Distinct Header
>
> Actual body paragraph.
"""
    html_out, _, _ = p.render(src)
    assert '<span class="callout-title">Distinct Header</span>' in html_out
    assert '<p>Distinct Header</p>' not in html_out
    assert '<p>Actual body paragraph.</p>' in html_out


def test_stress_empty_title_alert():
    """Verify alert with no title renders localized default title without empty tags."""
    p = MarkdownParser()
    src = "> [!NOTE]"
    html_out, _, _ = p.render(src)
    assert '<span class="callout-title">NOTE</span>' in html_out
    content = extract_callout_content(html_out)
    assert content.strip() == ""


def test_stress_legacy_bold_format_with_code():
    """Verify legacy bold alert format retains inline code and doesn't duplicate tag."""
    p = MarkdownParser()
    src = "> **CRITICAL**: Detected process injection into `lsass.exe`."
    html_out, _, _ = p.render(src)
    assert 'class="callout callout-critical critical"' in html_out
    assert '<span class="callout-title">CRITICAL</span>' in html_out
    assert '<code>lsass.exe</code>' in html_out
    assert 'CRITICAL:' not in html_out


# ============================================================================
# 4. MALFORMED, CORRUPTED, AND BOUNDARY SYNTAX (ZERO CRASHES)
# ============================================================================

@pytest.mark.parametrize("scenario,markdown_src", [
    ("unclosed_bracket", "> [!NOTE unclosed bracket\n> body content"),
    ("missing_type", "> [!] Missing type\n> body content"),
    ("unknown_type", "> [!UNKNOWN_TYPE] Unknown\n> body content"),
    ("multiple_tags_line", "> [!NOTE] [!WARNING] Double tags\n> body content"),
    ("lowercase_tag", "> [!note] Lowercase\n> body content"),
    ("leading_spaces", ">    [!NOTE] Indented tag\n> body content"),
    ("tab_indented", ">\t[!NOTE]\tTab title\n>\tbody content"),
    ("empty_blockquote", ">"),
    ("multi_empty_blockquote", ">\n>\n>"),
    ("empty_nested_quotes", "> > > >"),
    ("alert_with_empty_inner_quote", "> [!NOTE] Title\n> >"),
    ("unclosed_code_fence", "> [!WARNING] Unclosed Fence\n> ```python\n> x = 1"),
    ("malformed_table", "> [!IMPORTANT] Broken Table\n> | a | b\n> | c"),
    ("consecutive_tag_lines", "> [!NOTE] First\n> [!WARNING] Second"),
])
def test_stress_malformed_syntax_zero_crashes(scenario: str, markdown_src: str):
    """Verify parser never crashes on malformed, incomplete, or corrupted callout syntax."""
    p = MarkdownParser()
    v = CalloutHTMLValidator()

    try:
        html_out, _, _ = p.render(markdown_src)
    except Exception as exc:
        pytest.fail(f"Parser crashed on scenario '{scenario}': {type(exc).__name__}: {exc}")

    ok, errs = v.validate(html_out)
    assert ok, f"Tag balancing failed on scenario '{scenario}': {errs}"


# ============================================================================
# 5. MARKDOWN BLOCK CONSTRUCTS INSIDE CALLOUTS
# ============================================================================

def test_stress_code_lists_and_tables_inside_callout():
    """Verify rich block-level markdown structures render with proper wrappers inside callout."""
    p = MarkdownParser()
    v = CalloutHTMLValidator()

    src = """
> [!NOTE] Operational Analysis
> Preceding text.
>
> ```bash
> curl -sSf https://internal.corp/status
> ```
>
> 1. Step Alpha
>    - Sub-step Alpha.1
>    - Sub-step Alpha.2
> 2. Step Beta
>
> | Endpoint | Method | Status |
> | :--- | :---: | ---: |
> | `/api/v1/health` | `GET` | 200 |
> | `/api/v1/auth` | `POST` | 401 |
>
> Concluding text.
"""
    html_out, _, _ = p.render(src)
    ok, errs = v.validate(html_out)
    assert ok, f"Tag balancing validation failed: {errs}"

    # Verify elements are rendered inside callout-content
    assert '<pre class="highlight-code"' in html_out
    assert '<ol>' in html_out and '<ul>' in html_out
    assert '<div class="table-wrapper">' in html_out
    assert '<table>' in html_out
    assert 'Operational Analysis' in html_out


def test_stress_raw_html_and_images_inside_callout():
    """Verify raw HTML elements and images render cleanly inside callouts."""
    p = MarkdownParser()
    v = CalloutHTMLValidator()

    src = """
> [!CAUTION] Media and HTML Embed
> <div class="custom-card">Custom HTML Content</div>
>
> ![Architecture Diagram](assets/diagram.png)
"""
    html_out, _, _ = p.render(src)
    ok, errs = v.validate(html_out)
    assert ok, f"Tag balancing validation failed: {errs}"

    assert '<div class="custom-card">Custom HTML Content</div>' in html_out
    assert '<img src="assets/diagram.png" alt="Architecture Diagram"' in html_out


# ============================================================================
# 6. CONTAINER (:::) AND BLOCKQUOTE (>) INTEROPERABILITY
# ============================================================================

def test_stress_container_callout_inside_blockquote_alert():
    """Verify container callout nested inside blockquote alert."""
    p = MarkdownParser()
    v = CalloutHTMLValidator()

    src = """
> [!NOTE] Outer Blockquote Alert
> Outer note body.
>
> ::: warning Inner Container Callout
> Inner container body.
> :::
>
> Outer trailing body.
"""
    html_out, _, _ = p.render(src)
    ok, errs = v.validate(html_out)
    assert ok, f"Tag balancing validation failed: {errs}"
    assert v.max_callout_depth == 2
    assert v.callout_open_count == 2
    assert v.callout_close_count == 2

    assert "Outer Blockquote Alert" in html_out
    assert "Inner Container Callout" in html_out


def test_stress_blockquote_alert_inside_container_callout():
    """Verify blockquote alert nested inside container callout."""
    p = MarkdownParser()
    v = CalloutHTMLValidator()

    src = """
::: note Outer Container
Outer container body.

> [!WARNING] Inner Blockquote Alert
> Inner blockquote body.

Outer trailing body.
:::
"""
    html_out, _, _ = p.render(src)
    ok, errs = v.validate(html_out)
    assert ok, f"Tag balancing validation failed: {errs}"
    assert v.max_callout_depth == 2
    assert v.callout_open_count == 2
    assert v.callout_close_count == 2

    assert "Outer Container" in html_out
    assert "Inner Blockquote Alert" in html_out


# ============================================================================
# 7. HIGH-VOLUME BATCH DOCUMENT STRESS
# ============================================================================

def test_stress_high_volume_batch_callouts():
    """Verify document with 50 sequential callouts of alternating types."""
    p = MarkdownParser()
    v = CalloutHTMLValidator()

    types = ["note", "warning", "tip", "caution", "important", "critical"]
    src_blocks = []
    for i in range(50):
        t = types[i % len(types)]
        src_blocks.append(f"> [!{t.upper()}] Callout {i+1}\n> Content paragraph for callout {i+1}.")

    src = "\n\n".join(src_blocks)
    html_out, _, _ = p.render(src)
    ok, errs = v.validate(html_out)
    assert ok, f"Tag balancing validation failed: {errs}"
    assert v.callout_open_count == 50
    assert v.callout_close_count == 50
    assert v.max_callout_depth == 1
