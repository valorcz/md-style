# Secondary Review & Adversarial Audit Report — Milestone M2 (Print Fidelity & Theme Fixes)

## Review Summary

**Verdict**: APPROVE

---

## 1. Observation

### O1. W3C Paged Media & Page Break Rules
- **Files**: `styles/base/paged.css:80-95, 200-215` and `styles/base/print.css:54-68`.
- **Implementation**:
  - Universal `break-inside: avoid !important` and legacy `page-break-inside: avoid !important` applied across `.signature-block`, `.signature-line`, `.signature-row`, `.committee-signature`, `.sign-off`, `.callout`, `.admonition`, `.kpi-card`, `.kpi-grid`, and `figure`.
  - Tables protected via `thead { display: table-header-group !important; break-inside: avoid !important; }` and `tr { break-inside: avoid !important; }`.
  - Headings protected via `break-after: avoid !important` and `page-break-after: avoid !important`.
- **Direct verification**:
  - `tests/test_print_fidelity.py::test_signature_block_integrity`: Confirmed both Dr. Vance and Prof. Thorne attestation blocks remain together on the same page.
  - `tests/test_print_fidelity.py::test_zero_table_header_splits`: Confirmed zero blocks across all 4 sample PDFs (cyber, dossier, svj, school) cross the bottom margin boundary.
  - `tests/test_print_fidelity.py::test_zero_orphan_headings`: Confirmed zero orphan headings at page bottoms without subsequent body text.

### O2. SVJ Invitation Duplicate Page Counter Resolution
- **File**: `styles/svj/invitation/invitation.css:313-325`.
- **Implementation**: Removed `@bottom-right { content: counter(page); ... }` and `@page:first` margin box suppressions.
- **Direct verification**:
  - Running `pdftotext output/pozvanka-svj.pdf -` reveals strictly monotonic footer strings `Strana 1 z 5` through `Strana 5 z 5`.
  - `tests/test_print_fidelity.py::test_monotonic_page_numbers[svj]` asserts `len(bare_number_blocks) == 0`. Zero bare numbers (e.g. standalone "2", "3") were found.

### O3. Forensic Theme Isolation & Metadata Formatting
- **File**: `core/engine.py:426-515`.
- **Implementation**:
  - `_build_dossier_header()` inspects `is_forensic = "forensic" in style_val.lower()`.
  - Non-forensic themes (e.g., `general/school`, `general/announcement`, `svj/invitation`) suppress the default `"DIGITAL FORENSIC INVESTIGATION REPORT"` badge unless explicitly requested in frontmatter.
  - Metadata labels dynamically map to `catalog.get("meta.author_label")` ("Author:") rather than `catalog.get("forensics.examiner")` ("Examiner:").
  - Author prefix labels (e.g. `Examiner: `, `Author: `) are sanitized via `re.sub(r"^(?:lead\s+examiner|examiner|vyšetřovatel|vedoucí\s+vyšetřovatel|autor|author):\s*", "", ...)`.
- **Direct verification**:
  - Inspecting `output/school-report.pdf` via `pdftotext` confirms:
    - Zero occurrences of `"FORENSIC INVESTIGATION REPORT"`, `"DIGITAL FORENSIC"`, `"Examiner:"`, or `"Vyšetřovatel:"`.
    - Frontmatter author renders cleanly as `Author: Faculty Advisor: Dr. Alistair Vance | Examination Board`.

### O4. Cryptographic SHA-256 Fingerprint Parameter Handling
- **Files**: `core/bundler.py:35, 239-241, 390` and `core/engine.py:369-376`.
- **Implementation**:
  - `AssetBundler.assemble()` computes `self.fingerprint = hashlib.sha256(html_fragment.encode("utf-8")).hexdigest()`.
  - `ReportEngine._compile_pdf()` passes `fingerprint=getattr(bundler, "fingerprint", "")` into `bundler.build_cdp_header_footer_templates()`.
  - `build_cdp_header_footer_templates()` populates context variables `fingerprint` (16 chars) and `fingerprint_short` (8 chars) and interpolates theme footer templates.
- **Direct verification**:
  - In `output/sample-forensic-report.pdf`, page 2 running footer contains `September 11, 2026 • SHA-256: 43729da0f6ca3477`.
  - Verified by `tests/test_print_fidelity.py::test_forensic_metadata_correctness`.

### O5. PDF Layout Inspection Test Suite Design
- **File**: `tests/test_print_fidelity.py:1-562` (21 tests).
- **Implementation**:
  - Invokes `/usr/bin/pdftotext -bbox-layout` via subprocess and parses the resulting XML ElementTree.
  - Extracts word-, line-, and block-level bounding boxes (`xMin, yMin, xMax, yMax`).
  - Verifies clearance geometry: `max(header.yMax) < min(body.yMin) >= 10pt`, `max(body.yMax) < min(footer.yMin) >= 10pt`, and footer inter-block intersection checks.
  - Contains fallback skip fixture (`print_environment_check`) if Chromium or pdftotext are absent.

### O6. Verification Suite Execution
- `uv run pytest tests/test_print_fidelity.py -v`: 21 passed in 11.09s.
- `uv run pytest`: 183 passed in 31.60s.
- `make samples-pdf`: All 4 vector PDFs generated without errors via `/usr/bin/bun` CDP bridge.

---

## 2. Logic Chain

1. **Resolution of Bug A (Duplicate Page Numbers)**:
   - Observation O2 confirms removal of the rogue `@bottom-right` CSS rule in `styles/svj/invitation/invitation.css`.
   - Inspection of `output/pozvanka-svj.pdf` and execution of `test_monotonic_page_numbers[svj]` proves that only the authoritative CDP running footer (`Strana X z Y`) is rendered. Bug A is resolved.

2. **Resolution of Bug B (Forensic Header Leaks)**:
   - Observation O3 confirms that `_build_dossier_header` checks `is_forensic` and suppresses forensic title badges and examiner labels for non-forensic themes.
   - Direct pdftotext inspection of `output/school-report.pdf` and automated check in `test_theme_isolation_no_forensic_leaks` confirm zero forensic leakages. Bug B is resolved.

3. **Resolution of Bug C (Missing SHA-256 Fingerprint)**:
   - Observation O4 confirms `bundler.fingerprint` is now persisted on the bundler instance and passed to `build_cdp_header_footer_templates()`.
   - Inspection of `output/sample-forensic-report.pdf` verifies that the template token `{fingerprint}` expands to the 16-character SHA-256 digest `43729da0f6ca3477`. Bug C is resolved.

4. **W3C Paged Media & Break Protection**:
   - Observation O1 shows universal component break avoidance rules across base stylesheets.
   - Observation O5 and O6 confirm that bounding boxes, table rows, headings, signature blocks, and multi-page ordered lists compile cleanly without splits or collisions across page boundaries.

5. **Integrity & Authenticity**:
   - Audited tests parse dynamic XML emitted by `/usr/bin/pdftotext` on real PDF binaries generated by Headless Chromium CDP.
   - Zero hardcoded mock returns, zero facade implementations, and zero test circumventions.

---

## 3. Caveats & Adversarial Findings

1. **Adversarial Edge Case: Frontmatter Prefix Stripping without Colon**:
   - *Observation*: `core/engine.py:489` uses `re.sub(r"^(?:lead\s+examiner|examiner|vyšetřovatel|vedoucí\s+vyšetřovatel|autor|author):\s*", "", clean_author)`.
   - *Behavior*: If a user specifies `author: "Examiner Dr. Alexander Vance"` without a colon, `"Examiner"` is retained as part of the author name. However, the label is correctly mapped to `<span class="meta-label">Author:</span>` and no forensic badge is rendered.
   - *Severity*: Minor / cosmetic edge case. Does not violate theme isolation contracts.

2. **Adversarial Edge Case: Oversized Component Break-Before Push**:
   - *Observation*: An adversarial test created a massive callout (>1000pt) following a Table of Contents.
   - *Behavior*: Because `break-inside: avoid !important` is active, Chromium pushes the start of the callout from Page 1 to Page 2. On Page 2, because the component exceeds a full page, it fragments across subsequent pages.
   - *Severity*: Desirable behavior. Confirms `break-inside: avoid` pushes large components to clean page boundaries rather than clipping or fragmenting at the end of Page 1.

---

## 4. Conclusion

Milestone M2 (Print Fidelity & Theme Fixes - R2) is completely and correctly implemented.
All four major defects (duplicate SVJ page numbers, forensic header leakage in general themes, missing cryptographic footer fingerprint, and incomplete component break rules) are resolved.
The verification harness in `tests/test_print_fidelity.py` provides genuine, automated layout and bounding-box validation.
All 183 tests pass cleanly with zero regressions.

**Final Verdict: APPROVE**.

---

## 5. Verification Method

Execute the following commands in the workspace root:

```bash
# 1. Run the print fidelity test suite
uv run pytest tests/test_print_fidelity.py -v

# 2. Run the full regression test suite (183 tests)
uv run pytest

# 3. Compile all sample PDFs
make samples-pdf

# 4. Verify output PDF text and metadata
pdftotext output/pozvanka-svj.pdf - | tail -n 15
pdftotext output/school-report.pdf - | head -n 20
pdftotext output/sample-forensic-report.pdf - | tail -n 15
```

### Invalidation Conditions
- Any bounding box clearance failure in `tests/test_print_fidelity.py`.
- Appearance of duplicate bare page numbers in `output/pozvanka-svj.pdf`.
- Appearance of "FORENSIC INVESTIGATION REPORT" in `output/school-report.pdf`.
- Empty or missing SHA-256 hash in `output/sample-forensic-report.pdf`.
