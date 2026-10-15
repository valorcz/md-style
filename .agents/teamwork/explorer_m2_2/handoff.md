# Handoff Report: Explorer M2.2 - Engine Dossier Header Guard & Fingerprint Propagation

**Milestone**: M2 (Print Fidelity & Theme Fixes)  
**Agent**: Explorer M2.2  
**Date**: 2026-10-11  

---

## 1. Observation

### 1.1 Leaking Forensic Badges in Non-Forensic Documents (`core/engine.py:246, 420-503`)
In `core/engine.py:246`:
```python
# Synthesize frontmatter dossier header if appropriate
if self._should_build_dossier_header(style_param, frontmatter):
    dossier_block = self._build_dossier_header(frontmatter, doc_title, catalog, parser=parser, knowledge_pack=pack)
    html_fragment = f"{dossier_block}\n{html_fragment}"
```
And in `core/engine.py:420-446`:
```python
def _should_build_dossier_header(self, style: str, frontmatter: Optional[Dict[str, Any]]) -> bool:
    fm = frontmatter or {}
    if fm.get("dossier_header") is False:
        return False
    is_forensic = "forensic" in (style or "").lower()
    has_meta = any(k in fm for k in ("author", "examiner", "date", "abstract", "subtitle", "case_id", "case"))
    return (is_forensic or has_meta) and bool(fm.get("title"))

def _build_dossier_header(
    self,
    frontmatter: Optional[Dict[str, Any]],
    title: str,
    catalog: I18nCatalog,
    parser: Optional[Any] = None,
    knowledge_pack: Optional[Any] = None
) -> str:
    import html
    fm = frontmatter or {}
    report_badge = (
        fm.get("report_badge")
        or fm.get("report-badge")
        or fm.get("classification")
        or catalog.get("forensics.report_title")
        or catalog.get("meta.report_type")
        or "DIGITAL FORENSIC INVESTIGATION REPORT"
    )
```
And in `core/engine.py:471-477`:
```python
        author_label = (
            catalog.get("forensics.examiner")
            or catalog.get("meta.examiner_label")
            or catalog.get("meta.author_label")
            or "Examiner:"
        )
        meta_items.append(f'<p class="author"><span class="meta-label">{html.escape(author_label)}</span> {html.escape(clean_author)}</p>')
```

**Verbatim Reproduction**:
Compiling `examples/school-report-sample.md` (`style: school`, `author: "Faculty Advisor: Dr. Alistair Vance | Examination Board"`):
```bash
uv run md-style examples/school-report-sample.md -s general/school -p -o /tmp/test-school-report.pdf
pdftotext -f 1 -l 1 /tmp/test-school-report.pdf - | head -n 12
```
Output:
```text
Academic Progress & Evaluation Report

FORENSIC INVESTIGATION REPORT

Academic Progress & Evaluation Report
Department of Computer Science & Software Engineering | Spring Term 2026

Examiner: Faculty Advisor: Dr. Alistair Vance | Examination Board
Date: June 12, 2026
```
Because `_build_dossier_header()` was not passed `style_param` and unconditionally evaluated `catalog.get("forensics.report_title")` and `catalog.get("forensics.examiner")`, non-forensic academic and corporate reports received forensic badges (`FORENSIC INVESTIGATION REPORT`) and examiner labels (`Examiner:`).

---

### 1.2 Missing Fingerprint in CDP Footer Templates (`core/engine.py:362-371` and `core/bundler.py:29-35, 388`)
In `core/engine.py:362-371`:
```python
        print_options: Dict[str, Any] = {}
        if bundler and theme and catalog:
            try:
                print_options = bundler.build_cdp_header_footer_templates(
                    theme=theme,
                    catalog=catalog,
                    title=title,
                    frontmatter=frontmatter
                )
            except Exception as ex:
                Diagnostics.warn(f"Failed to build CDP templates: {ex}")
```
`build_cdp_header_footer_templates` accepts `fingerprint: str = ""` (in `core/bundler.py:215`), but `_compile_pdf` never supplied `fingerprint`.

Crucially, in `core/bundler.py:388`:
```python
fingerprint = hashlib.sha256(html_fragment.encode("utf-8")).hexdigest()
```
`fingerprint` was computed as a local variable inside `AssetBundler.assemble()`, but was never persisted to `self.fingerprint`. Consequently, `AssetBundler` had no attribute `fingerprint` on instance termination.

**Verbatim Reproduction**:
Compiling `examples/sample-forensic-report.md` (`styles/forensic/dossier/theme.yaml` specifies `footers: center: "{date} • SHA-256: {fingerprint}"`):
```bash
uv run md-style examples/sample-forensic-report.md -s forensic/dossier -p -o /tmp/test-forensic.pdf
pdftotext -f 2 -l 2 /tmp/test-forensic.pdf - | tail -n 8
```
Output:
```text
Forensic Investigation Unit

September 11, 2026 • SHA-256:

Page 2 of 10
```
The hash following `SHA-256:` is completely blank.

---

### 1.3 Missing Sample Target in Makefile (`Makefile:38-42`)
In `Makefile:38-42`:
```makefile
samples-pdf: samples
	uv run md-style examples/sample-forensic-cyber.md -s forensic/cyber -p -o output/sample-forensic-cyber.pdf
	uv run md-style examples/sample-forensic-report.md -s forensic/dossier -p -o output/sample-forensic-report.pdf
	uv run md-style "examples/pozvánka-shromáždění-svj.md" -s svj/invitation -p -o output/pozvanka-svj.pdf
```
`examples/school-report-sample.md` is compiled in `samples` (HTML) at line 35, but omitted from `samples-pdf` (PDF via Chromium).

---

## 2. Logic Chain

1. **Interface Contract Compliance**:
   - `PROJECT.md:64-67` mandates:
     - "Dossier badge and examiner label MUST only activate for themes where `"forensic" in style.lower()`."
     - "Non-forensic themes with frontmatter author/date receive standard metadata blocks without "FORENSIC INVESTIGATION REPORT" or "Examiner:"."
2. **Title Block Scoping**:
   - In `core/engine.py:246`, `style_param` represents the active theme (e.g. `"general/school"`, `"forensic/cyber"`).
   - Passing `style=style_param` to `self._build_dossier_header(...)` enables the renderer to distinguish forensic from non-forensic contexts.
   - In `_build_dossier_header()`:
     - `is_forensic` is determined via `style` (falling back to `self.config.style` or frontmatter). If unspecified (e.g. in standalone unit test assertions without style arguments), it detects forensic tokens in author/title.
     - `report_badge`: Only frontmatter explicit badges (`report_badge`, `report-badge`, `classification`) or forensic catalog fallbacks are rendered. In non-forensic documents without an explicit frontmatter badge, `report_badge` is omitted entirely (`<div class="report-badge">` is not emitted).
     - `author_label`: When `is_forensic` is False (and frontmatter didn't explicitly specify `examiner`), `author_label` falls back to `catalog.get("meta.author_label") or "Author:"` rather than `"Examiner:"` / `"Vyšetřovatel:"`.
3. **Fingerprint Lifecycle and CDP Propagation**:
   - `AssetBundler.assemble()` calculates the SHA-256 hash of `html_fragment`.
   - By declaring `self.fingerprint: str = ""` in `AssetBundler.__init__` and setting `self.fingerprint = fingerprint` in `assemble()`, `bundler.fingerprint` becomes an official instance attribute containing the 64-character hash.
   - In `core/engine.py:_compile_pdf()`, passing `fingerprint=getattr(bundler, "fingerprint", "")` propagates the hash into `build_cdp_header_footer_templates()`.
   - `build_cdp_header_footer_templates()` truncates `fingerprint[:16]` for `{fingerprint}` in `theme.yaml`, populating the footer template with the 16-character SHA-256 fingerprint.
4. **Makefile Target Completeness**:
   - Adding `uv run md-style examples/school-report-sample.md -s general/school -p -o output/school-report.pdf` ensures that all three theme branches (Forensic, SVJ, and General) are compiled during `make samples-pdf`.

---

## 3. Caveats

1. **Unit Test Backwards-Compatibility**:
   - Standalone tests such as `tests/test_paged_theme.py:test_dossier_header_author_sanitization` invoke `_build_dossier_header` directly with `PipelineConfig(input_file=Path("/tmp/fake.md"))` without specifying `style="forensic/..."`. The fallback heuristic in `_build_dossier_header` ensures that forensic test cases with titles like "Forenzní zpráva" or authors like "Lead Examiner: S. Mercer" continue to pass without breaking existing tests.
2. **Explicit User Overrides**:
   - If a non-forensic document explicitly specifies `report_badge: "TERM REPORT"` or `examiner: "Dr. Vance"` in its YAML frontmatter, the engine honors the user's explicit frontmatter keys while avoiding unsolicited forensic defaults.

---

## 4. Conclusion

The proposed patches solve all three targets for Milestone M2:
1. Forensic badges and examiner labels are strictly scoped to forensic themes in `core/engine.py`. Non-forensic documents with frontmatter render clean title blocks with `Author:` and no forensic badge.
2. `bundler.fingerprint` is persisted in `core/bundler.py` and passed in `core/engine.py:_compile_pdf()`, restoring the SHA-256 verification hash in vector PDF footers.
3. `examples/school-report-sample.md` is added to `Makefile:samples-pdf`.

### Proposed Patches

#### Patch 1: `core/engine.py`
```diff
--- a/core/engine.py
+++ b/core/engine.py
@@ -244,7 +244,9 @@ class ReportEngine:
 
         # Synthesize frontmatter dossier header if appropriate
         if self._should_build_dossier_header(style_param, frontmatter):
-            dossier_block = self._build_dossier_header(frontmatter, doc_title, catalog, parser=parser, knowledge_pack=pack)
+            dossier_block = self._build_dossier_header(
+                frontmatter, doc_title, catalog, parser=parser, knowledge_pack=pack, style=style_param
+            )
             html_fragment = f"{dossier_block}\n{html_fragment}"
 
         total_diagrams = 0
@@ -362,11 +364,13 @@ class ReportEngine:
             print_options: Dict[str, Any] = {}
             if bundler and theme and catalog:
                 try:
+                    fingerprint_val = getattr(bundler, "fingerprint", "")
                     print_options = bundler.build_cdp_header_footer_templates(
                         theme=theme,
                         catalog=catalog,
                         title=title,
-                        frontmatter=frontmatter
+                        frontmatter=frontmatter,
+                        fingerprint=fingerprint_val
                     )
                 except Exception as ex:
                     Diagnostics.warn(f"Failed to build CDP templates: {ex}")
@@ -421,20 +425,36 @@ class ReportEngine:
         fm = frontmatter or {}
         if fm.get("dossier_header") is False:
             return False
+        if fm.get("dossier_header") is True:
+            return bool(fm.get("title"))
         is_forensic = "forensic" in (style or "").lower()
         has_meta = any(k in fm for k in ("author", "examiner", "date", "abstract", "subtitle", "case_id", "case"))
         return (is_forensic or has_meta) and bool(fm.get("title"))
 
     def _build_dossier_header(
         self,
         frontmatter: Optional[Dict[str, Any]],
         title: str,
         catalog: I18nCatalog,
         parser: Optional[Any] = None,
-        knowledge_pack: Optional[Any] = None
+        knowledge_pack: Optional[Any] = None,
+        style: str = ""
     ) -> str:
         import html
         fm = frontmatter or {}
-        report_badge = (
-            fm.get("report_badge")
-            or fm.get("report-badge")
-            or fm.get("classification")
-            or catalog.get("forensics.report_title")
-            or catalog.get("meta.report_type")
-            or "DIGITAL FORENSIC INVESTIGATION REPORT"
-        )
+        style_val = (
+            style
+            or (self.config.style if self.config else "")
+            or str(fm.get("style") or fm.get("theme") or "")
+        )
+        if style_val:
+            is_forensic = "forensic" in style_val.lower()
+        else:
+            is_forensic = (
+                bool(fm.get("examiner"))
+                or bool(re.search(r"\b(?:examiner|vyšetřovatel)\b", str(fm.get("author", "")), re.IGNORECASE))
+                or "forensic" in str(title).lower()
+                or "forenzní" in str(title).lower()
+            )
+
+        report_badge = fm.get("report_badge") or fm.get("report-badge") or fm.get("classification")
+        if not report_badge and is_forensic:
+            report_badge = (
+                catalog.get("forensics.report_title")
+                or catalog.get("meta.report_type")
+                or "DIGITAL FORENSIC INVESTIGATION REPORT"
+            )
         subtitle = fm.get("subtitle", "")
         author = fm.get("author") or fm.get("examiner", "")
         date = fm.get("date", "")
         case_id = fm.get("case_id") or fm.get("case", "")
         abstract = fm.get("abstract", "")
 
         lines = ['<header id="title-block-header">']
-        lines.append(f'  <div class="report-badge">{html.escape(str(report_badge))}</div>')
+        if report_badge:
+            lines.append(f'  <div class="report-badge">{html.escape(str(report_badge))}</div>')
         lines.append(f'  <h1 class="title">{html.escape(str(title))}</h1>')
         if subtitle:
             if parser and hasattr(parser, "md"):
@@ -468,14 +488,20 @@ class ReportEngine:
                 clean_author,
                 flags=re.IGNORECASE
             ).strip()
-            author_label = (
-                catalog.get("forensics.examiner")
-                or catalog.get("meta.examiner_label")
-                or catalog.get("meta.author_label")
-                or "Examiner:"
-            )
+            if is_forensic or fm.get("examiner"):
+                author_label = (
+                    catalog.get("forensics.examiner")
+                    or catalog.get("meta.examiner_label")
+                    or catalog.get("meta.author_label")
+                    or "Examiner:"
+                )
+            else:
+                author_label = (
+                    catalog.get("meta.author_label")
+                    or "Author:"
+                )
             meta_items.append(f'<p class="author"><span class="meta-label">{html.escape(author_label)}</span> {html.escape(clean_author)}</p>')
         if date:
-            date_label = catalog.get("forensics.date") or catalog.get("meta.date_label") or "Date:"
+            date_label = (catalog.get("forensics.date") if is_forensic else None) or catalog.get("meta.date_label") or "Date:"
             meta_items.append(f'<p class="date"><span class="meta-label">{html.escape(date_label)}</span> {html.escape(str(date))}</p>')
         if case_id:
             case_label = catalog.get("forensics.case_id") or catalog.get("meta.case_label") or "Case ID:"
```

#### Patch 2: `core/bundler.py`
```diff
--- a/core/bundler.py
+++ b/core/bundler.py
@@ -32,6 +32,7 @@ class AssetBundler:
         self.allow_online = allow_online
         self.font_bundler = FontBundler(allow_online=allow_online)
         self.icon_service = IconService(allow_online=allow_online)
+        self.fingerprint: str = ""
 
     def encode_file_base64(self, file_path: Path) -> Optional[str]:
         if not file_path.is_file():
@@ -386,6 +387,7 @@ class AssetBundler:
         catalog = catalog or I18nCatalog(lang)
         frontmatter = frontmatter or {}
         fingerprint = hashlib.sha256(html_fragment.encode("utf-8")).hexdigest()
+        self.fingerprint = fingerprint
 
         # 1. Collect all CSS stylesheets and process through FontBundler
         css_blocks: List[str] = []
```

#### Patch 3: `Makefile`
```diff
--- a/Makefile
+++ b/Makefile
@@ -39,6 +39,7 @@ samples-pdf: samples
 	uv run md-style examples/sample-forensic-cyber.md -s forensic/cyber -p -o output/sample-forensic-cyber.pdf
 	uv run md-style examples/sample-forensic-report.md -s forensic/dossier -p -o output/sample-forensic-report.pdf
 	uv run md-style "examples/pozvánka-shromáždění-svj.md" -s svj/invitation -p -o output/pozvanka-svj.pdf
+	uv run md-style examples/school-report-sample.md -s general/school -p -o output/school-report.pdf
 
 clean:
 	rm -rf output/ .pytest_cache/ viewer/dist/
```

---

## 5. Verification Method

### 5.1 Run Test Suite
```bash
uv run pytest
```
Verify that all 162 existing tests pass with 0 regressions.

### 5.2 Verify Absence of Forensic Leaks in School Report
```bash
uv run md-style examples/school-report-sample.md -s general/school -p -o output/school-report.pdf
pdftotext -f 1 -l 1 output/school-report.pdf - | grep -E "FORENSIC|Examiner:"
```
**Expected**: Exit code 1 (no matches found).

Inspect header text:
```bash
pdftotext -f 1 -l 1 output/school-report.pdf - | head -n 10
```
**Expected**:
- Shows `Author: Faculty Advisor: Dr. Alistair Vance | Examination Board`
- No `FORENSIC INVESTIGATION REPORT` badge.

### 5.3 Verify Populated SHA-256 Fingerprint in Forensic PDF Footer
```bash
uv run md-style examples/sample-forensic-report.md -s forensic/dossier -p -o output/sample-forensic-report.pdf
pdftotext -f 2 -l 2 output/sample-forensic-report.pdf - | grep -E "SHA-256:"
```
**Expected**: Matches regex `SHA-256:\s+[a-f0-9]{16}`.

### 5.4 Verify Makefile Target
```bash
make samples-pdf
ls -la output/school-report.pdf
```
**Expected**: `output/school-report.pdf` is successfully generated with non-zero size.

### Invalidation Conditions
- Any occurrence of "FORENSIC INVESTIGATION REPORT" or "Examiner:" in `output/school-report.pdf`.
- Empty string following `SHA-256:` in `output/sample-forensic-report.pdf`.
- Failure of any unit test in `tests/test_paged_theme.py` or `tests/test_style_remediation.py`.
