# Handoff Report: Explorer M1.2 - Callout Parser Nesting & Title Deduplication

## 1. Observation

### 1.1 Existing Implementation and Defect Manifestation

1. **Target Files**:
   - Implementation: `/home/valor/Devel/personal/md-style/core/parser/plugins/callouts.py` (225 lines)
   - Test suite: `/home/valor/Devel/personal/md-style/tests/test_callout_plugin.py` (67 lines, 5 tests)

2. **Defect 1: Non-Recursive Blockquote Handling (`core/parser/plugins/callouts.py:163-180`)**:
   - The token processing loop in `transform_blockquote_callouts()` gathers inner tokens between `blockquote_open` and matching `blockquote_close`:
     ```python
     # core/parser/plugins/callouts.py:163-180
     depth = 1
     while i < n and depth > 0:
         inner = tokens[i]
         if inner.type == "blockquote_open":
             depth += 1
         elif inner.type == "blockquote_close":
             depth -= 1
             if depth == 0:
                 c_close = Token("html_block", "", 0)
                 ballot_html = render_ballot_block(catalog) if alert_type == "proposal" else ""
                 c_close.content = f"  </div>\n{ballot_html}</div>\n"
                 out.append(c_close)
                 i += 1
                 break
         out.append(inner)
         i += 1
     continue
     ```
   - **Verbatim Behavior Observed**:
     When input contains nested blockquote callouts:
     ```markdown
     > [!NOTE] Outer Note
     > > [!WARNING] Inner Warning
     > > Inner warning body
     ```
     Markdown-it produces an outer `blockquote_open` (depth 1) and inner `blockquote_open` (depth 2). Because line 178 unconditionally executes `out.append(inner)`, the inner blockquote tokens (`blockquote_open`, `paragraph_open`, `inline`, `paragraph_close`, `blockquote_close`) are appended directly into `out` without calling `transform_blockquote_callouts()` on them.
     - **Observed Rendered Output**:
       ```html
       <div class="callout callout-note note">
         <div class="callout-header">
           ...
           <span class="callout-title">Outer Note</span>
         </div>
         <div class="callout-content">
           <blockquote>
             <p>[!WARNING] Inner Warning
             Inner warning body</p>
           </blockquote>
         </div>
       </div>
       ```
     The inner alert is rendered as raw HTML `<blockquote>` containing literal `[!WARNING]`, completely failing to transform into `<div class="callout callout-warning warning">`.

3. **Defect 2: Title Duplication in Single-Line Alerts (`core/parser/plugins/callouts.py:96-162`)**:
   - `CALLOUT_REGEX` matches the alert header line:
     ```python
     # core/parser/plugins/callouts.py:26-29
     CALLOUT_REGEX = re.compile(
         r"^\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION|CRITICAL|INFO|SUCCESS|DANGER|EVIDENCE|FINDING|PROPOSAL)\](?:\s+(.*))?$",
         re.IGNORECASE
     )
     ```
   - When processing a single-line alert without a softbreak (lines 151-162):
     ```python
     # core/parser/plugins/callouts.py:151-162
     else:
         # Single line alert: > [!NOTE] All timestamps are in **UTC**
         if children:
             children[0].content = re.sub(r"^\s*\[![A-Za-z]+\]\s*", "", children[0].content)
             inline_tok.content = re.sub(r"^\s*\[![A-Za-z]+\]\s*", "", inline_tok.content)
             if inline_tok.content:
                 out.append(tokens[i+1]) # paragraph_open
                 inline_tok.children = children
                 out.append(inline_tok)
                 out.append(tokens[i+3]) # paragraph_close
         i += 4
     ```
   - **Verbatim Behavior Observed**:
     When input is `> [!NOTE] Custom Title Only`:
     - Line 103 extracts `custom_title = m.group(2)` (`"Custom Title Only"`).
     - Line 118 creates `c_open` with header `<span class="callout-title">Custom Title Only</span>`.
     - Lines 154-155 only strip `r"^\s*\[![A-Za-z]+\]\s*"`, leaving `inline_tok.content = "Custom Title Only"`.
     - Lines 156-160 then emit `<p>Custom Title Only</p>`.
     - **Observed Rendered Output**:
       ```html
       <div class="callout callout-note note">
         <div class="callout-header">
           ...
           <span class="callout-title">Custom Title Only</span>
         </div>
         <div class="callout-content">
           <p>Custom Title Only</p>
         </div>
       </div>
       ```
     The title `"Custom Title Only"` is duplicated: it appears once in `<span class="callout-title">` and a second time in `<p>` within `<div class="callout-content">`.
     Similarly, when a document has `> [!NOTE] Custom Title\n>\n> Body paragraph`:
     The first paragraph outputs `<p>Custom Title</p>` followed by `<p>Body paragraph</p>`, duplicating the title above the body content.

---

## 2. Logic Chain

1. **Premise 1 (Recursive Callout AST Transformation)**:
   - *Observation*: Nested blockquotes are represented in the markdown-it token stream as balanced pairs of `blockquote_open` and `blockquote_close` tokens located inside the token span of the parent blockquote.
   - *Inference*: In order for inner blockquotes to be transformed into `<div class="callout ...">` structures, the inner token sub-stream collected between `i + 4` and the matching outer `blockquote_close` must be processed by `transform_blockquote_callouts()`.
   - *Design*:
     Instead of appending `inner` directly to `out`, accumulate inner tokens into `inner_tokens: List[Token]`. When matching outer `blockquote_close` is reached (`depth == 0`), invoke:
     ```python
     if inner_tokens:
         transformed_inner = transform_blockquote_callouts(inner_tokens, catalog, icon_service)
         out.extend(transformed_inner)
     ```
     Because this invocation is recursive:
     - Arbitrary nesting depths (2, 3, 4+ levels) are supported automatically.
     - Sibling callouts within the same parent blockquote are all visited and transformed.
     - Standard blockquotes (`> quotation`) within callouts that do not match `CALLOUT_REGEX` pass through unaffected as standard `<blockquote>` elements.

2. **Premise 2 (Clean Single-Line Title Deduplication)**:
   - *Observation*: When `softbreak_idx is not None` (multi-line alert), line 1 is discarded from `remaining_children` and `remaining_content`, ensuring the title is never duplicated in the body.
   - *Observation*: In the single-line case (`softbreak_idx is None`), the entire line was parsed as `m.group(2)` (`custom_title`). The text after `[!TYPE]` was already assigned as the callout header's title.
   - *Inference*: Leaving `custom_title` in `inline_tok.content` causes markdown-it to generate an redundant paragraph with the title string.
   - *Design*:
     In the `else:` branch of `elif m:`:
     ```python
     if custom_title and custom_title.strip():
         title_escaped = re.escape(custom_title.strip())
         inline_tok.content = re.sub(rf"^\s*{title_escaped}\s*", "", inline_tok.content).strip()
         children[0].content = re.sub(rf"^\s*{title_escaped}\s*", "", children[0].content).strip()
         children = [c for c in children if c.content or c.type != "text"]
     ```
     - For single-line alerts with a title (e.g. `> [!NOTE] Custom Title`), `inline_tok.content` becomes `""`, `inline_tok.children` becomes `[]`, and `if inline_tok.content:` evaluates to `False`. Zero empty or redundant paragraphs are emitted in `<div class="callout-content">`.
     - For multi-paragraph alerts where the title is on its own line (e.g. `> [!NOTE] Title\n>\n> Body`), the first paragraph is stripped cleanly without generating `<p>Title</p>`, and the subsequent paragraph is retained in full.
     - For single-line alerts without custom title (e.g. `> [!NOTE]`), `custom_title` is `None` or empty, so default title `"NOTE"` is shown in header, and body remains clean.

3. **Premise 3 (Zero Regressions on Baseline Test Suite)**:
   - *Observation*: `uv run pytest` executes 87 tests across 18 test files. All 5 existing callout tests in `tests/test_callout_plugin.py` verify multi-line alerts, legacy format `> **WARNING**:`, container callouts `::: warning`, and rich inline formatting.
   - *Inference*: The proposed recursive transform and title deduplication preserve existing behavior for multi-line alerts and legacy formats while fixing both defects.

---

## 3. Caveats

1. **CommonMark Lazy Continuation in Deeply Nested Quotes**:
   In standard CommonMark, lines following a nested blockquote without a blank quote separator (e.g. `> > [!WARNING] Inner\n> After nested text`) may be parsed by CommonMark as lazy continuation belonging to the inner blockquote. To reliably return to the outer blockquote level in Markdown source, an explicit quote marker line (`> `) is standard practice. The recursive transformer honors standard markdown-it token streams accurately in both cases.
2. **Container-Style Callouts**:
   Container-style callouts (`::: note Title ... :::`) use `mdit_py_plugins.container`, which operate at the block parser stage. They already nest cleanly. The changes in this specification are localized to `transform_blockquote_callouts()` and do not touch the container parser rule.

---

## 4. Conclusion & Precise Code Specifications

### 4.1 Specification for `core/parser/plugins/callouts.py`

Modify `transform_blockquote_callouts()` at lines 151-180:

```python
<<<< ORIGINAL (lines 151-180):
                        else:
                            # Single line alert: > [!NOTE] All timestamps are in **UTC**
                            if children:
                                children[0].content = re.sub(r"^\s*\[![A-Za-z]+\]\s*", "", children[0].content)
                                inline_tok.content = re.sub(r"^\s*\[![A-Za-z]+\]\s*", "", inline_tok.content)
                                if inline_tok.content:
                                    out.append(tokens[i+1]) # paragraph_open
                                    inline_tok.children = children
                                    out.append(inline_tok)
                                    out.append(tokens[i+3]) # paragraph_close
                            i += 4

                    # Collect remaining inner tokens until matching blockquote_close
                    depth = 1
                    while i < n and depth > 0:
                        inner = tokens[i]
                        if inner.type == "blockquote_open":
                            depth += 1
                        elif inner.type == "blockquote_close":
                            depth -= 1
                            if depth == 0:
                                c_close = Token("html_block", "", 0)
                                ballot_html = render_ballot_block(catalog) if alert_type == "proposal" else ""
                                c_close.content = f"  </div>\n{ballot_html}</div>\n"
                                out.append(c_close)
                                i += 1
                                break
                        out.append(inner)
                        i += 1
                    continue
==== PROPOSED REPLACEMENT:
                        else:
                            # Single line alert: > [!NOTE] Custom Title
                            if children:
                                children[0].content = re.sub(r"^\s*\[![A-Za-z]+\]\s*", "", children[0].content)
                                inline_tok.content = re.sub(r"^\s*\[![A-Za-z]+\]\s*", "", inline_tok.content)
                                if custom_title and custom_title.strip():
                                    title_escaped = re.escape(custom_title.strip())
                                    inline_tok.content = re.sub(rf"^\s*{title_escaped}\s*", "", inline_tok.content).strip()
                                    children[0].content = re.sub(rf"^\s*{title_escaped}\s*", "", children[0].content).strip()
                                    children = [c for c in children if c.content or c.type != "text"]

                                if inline_tok.content:
                                    out.append(tokens[i+1]) # paragraph_open
                                    inline_tok.children = children
                                    out.append(inline_tok)
                                    out.append(tokens[i+3]) # paragraph_close
                            i += 4

                    # Collect remaining inner tokens until matching blockquote_close
                    inner_tokens: List[Token] = []
                    depth = 1
                    while i < n and depth > 0:
                        inner = tokens[i]
                        if inner.type == "blockquote_open":
                            depth += 1
                            inner_tokens.append(inner)
                        elif inner.type == "blockquote_close":
                            depth -= 1
                            if depth == 0:
                                i += 1
                                break
                            inner_tokens.append(inner)
                        else:
                            inner_tokens.append(inner)
                        i += 1

                    if inner_tokens:
                        transformed_inner = transform_blockquote_callouts(inner_tokens, catalog, icon_service)
                        out.extend(transformed_inner)

                    c_close = Token("html_block", "", 0)
                    ballot_html = render_ballot_block(catalog) if alert_type == "proposal" else ""
                    c_close.content = f"  </div>\n{ballot_html}</div>\n"
                    out.append(c_close)
                    continue
>>>>
```

### 4.2 Specification for `tests/test_callout_plugin.py`

Append the following 6 targeted unit tests to `/home/valor/Devel/personal/md-style/tests/test_callout_plugin.py`:

```python
def test_nested_callout_alerts():
    """Verifies recursive parsing of nested callout blockquotes."""
    p = MarkdownParser()
    src = """
> [!NOTE] Outer Note
> Outer body text
> 
> > [!WARNING] Inner Warning
> > Inner body text
"""
    html_out, _, _ = p.render(src)
    assert 'class="callout callout-note note"' in html_out
    assert 'class="callout callout-warning warning"' in html_out
    assert 'Outer Note' in html_out
    assert 'Inner Warning' in html_out
    assert 'Outer body text' in html_out
    assert 'Inner body text' in html_out
    note_pos = html_out.find('callout-note')
    warn_pos = html_out.find('callout-warning')
    assert 0 <= note_pos < warn_pos

def test_deeply_nested_callout_alerts_3_levels():
    """Verifies that arbitrary callout nesting depth (3+ levels) functions cleanly."""
    p = MarkdownParser()
    src = """
> [!NOTE] Level 1 Note
> > [!WARNING] Level 2 Warning
> > > [!CRITICAL] Level 3 Critical
"""
    html_out, _, _ = p.render(src)
    assert 'callout-note' in html_out
    assert 'callout-warning' in html_out
    assert 'callout-critical' in html_out
    idx1 = html_out.find('callout-note')
    idx2 = html_out.find('callout-warning')
    idx3 = html_out.find('callout-critical')
    assert 0 <= idx1 < idx2 < idx3

def test_single_line_callout_title_deduplication():
    """Verifies that single-line alerts do not duplicate their custom title in the body paragraph."""
    p = MarkdownParser()
    src = "> [!NOTE] Dedicated Custom Title"
    html_out, _, _ = p.render(src)
    assert '<span class="callout-title">Dedicated Custom Title</span>' in html_out
    assert '<p>Dedicated Custom Title</p>' not in html_out

def test_single_line_callout_multi_paragraph_deduplication():
    """Verifies that a title line separated by a blank line does not duplicate in callout content."""
    p = MarkdownParser()
    src = """
> [!NOTE] Custom Header
>
> Body paragraph content.
"""
    html_out, _, _ = p.render(src)
    assert '<span class="callout-title">Custom Header</span>' in html_out
    assert '<p>Custom Header</p>' not in html_out
    assert '<p>Body paragraph content.</p>' in html_out

def test_callout_with_standard_blockquote_inside():
    """Verifies that regular blockquotes inside a callout remain rendered as standard blockquotes."""
    p = MarkdownParser()
    src = """
> [!NOTE] Callout Header
>
> > Normal quote content
"""
    html_out, _, _ = p.render(src)
    assert 'callout-note' in html_out
    assert '<blockquote>' in html_out
    assert 'Normal quote content' in html_out

def test_standard_blockquote_with_nested_callout():
    """Verifies that a callout nested inside a standard blockquote is properly transformed."""
    p = MarkdownParser()
    src = """
> Normal quote
>
> > [!WARNING] Nested Alert
> > Watch out
"""
    html_out, _, _ = p.render(src)
    assert '<blockquote>' in html_out
    assert 'callout-warning' in html_out
    assert 'Watch out' in html_out
```

### 4.3 Pre-Generated Patch File
A machine-applicable patch file has been generated at:
`/home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m1_2/callouts.patch`

---

## 5. Verification Method

To independently verify the implementation and test coverage:

1. **Apply the patch (or make the modifications described above)**:
   ```bash
   git apply /home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m1_2/callouts.patch
   ```

2. **Execute the Callout Plugin Test Suite**:
   ```bash
   uv run pytest tests/test_callout_plugin.py -v
   ```
   *Expected Result*: All 11 tests pass (5 baseline + 6 new tests).

3. **Execute Full Suite Regression Guard**:
   ```bash
   uv run pytest
   ```
   *Expected Result*: All 93 tests pass (87 baseline + 6 new) with 0 regressions.

4. **Verify Rendered Output Manually**:
   ```bash
   uv run python -c "
   from core.parser import MarkdownParser
   p = MarkdownParser()
   h, _, _ = p.render('> [!NOTE] Level 1\n> > [!WARNING] Level 2')
   assert 'callout-note' in h and 'callout-warning' in h
   h_dedup, _, _ = p.render('> [!NOTE] Unique Title')
   assert '<p>Unique Title</p>' not in h_dedup
   print('Verification passed!')
   "
   ```
