# Implementation Plan: Option A (In-Place Modularization) & Headless Chrome Printing Fix

---

## 1. Goal Description

This plan implements **Option A: In-Place Modularization** to resolve the architectural fragility and tight coupling in `md-style`, while immediately fixing browser default header/footer leakage in PDF outputs:

1. **Chromium PDF Header/Footer Fix**: Replace the deprecated/invalid `--print-to-pdf-no-header` flag in `core/engine.py` with the official `--no-pdf-header-footer` flag so that timestamps, page URLs, and titles are never stamped onto PDFs by Chrome.
2. **Declarative Style Manifest Architecture**: Replace hardcoded domain checks in `core/engine.py` (`is_cyber`, `if "svj"`, `TEMPLATES["forensic"]`) with a declarative `StyleManifest` system (`style.yaml`).
3. **Composable CSS Design System**: Decompose the 4,000+ lines of duplicated forensic CSS into layered modules (`base/tokens.css`, `base/tables.css`, `base/print.css`, and slim `theme.css` skins), eliminating duplicate resets, table hacks, and `!important` wars.
4. **Consolidated Lua AST Filters**: Unify timestamp detection, column width un-crushing, and hash tagging into a single shared filter (`filters/table-nowrap.lua`), eliminating 800+ lines of duplicate Lua AST code.

---

## 2. User Review Required

> [!IMPORTANT]
> **Key Architecture Decisions for Review**:
> 1. **Backwards Compatibility**: Existing styles that are single `.css` files (e.g., `styles/school.css`, `styles/announcement.css`) will continue to work seamlessly without requiring a `style.yaml`. The engine will synthesize a default manifest on the fly.
> 2. **Threat Intelligence Stage Decoupling**: Stage 2 (CVE/MITRE/Windows Event resolution) will run **only** if the chosen style specifies `enrichment: true` (or via `--enrich` flag). Generic documents (e.g., school reports, SVJ notices) will completely bypass threat discovery, improving speed and preventing cross-domain side effects.
> 3. **Non-Breaking Visual Guarantee**: All forensic and cyber reports will maintain identical visual appearance, interactive drawer functionality, and font rendering.

---

## 3. Proposed Changes

```
md-style/
├── core/
│   ├── engine.py                  # [MODIFY] Decouple into domain-agnostic orchestrator
│   ├── style.py                   # [NEW] StyleManifest loader (YAML / CSS discovery)
│   └── cli.py                     # [MODIFY] Add --enrich flag, pass manifest options
├── filters/
│   └── table-nowrap.lua           # [MODIFY] Consolidate table & hash AST normalization
├── styles/
│   ├── base/
│   │   ├── tokens.css             # [NEW] Design tokens, typography variables, colors
│   │   ├── tables.css             # [NEW] Unified table styling, nowrap, hash wrap
│   │   └── print.css              # [MODIFY] Paged media rules, HUD suppression, margins
│   ├── forensic/
│   │   ├── style.yaml             # [NEW] Declarative manifest for official forensic report
│   │   ├── theme.css              # [NEW] Pure aesthetic skin (~280 lines)
│   │   ├── dossier.yaml           # [NEW] Manifest for forensic dossier variant
│   │   └── cyber.yaml             # [NEW] Manifest for cyber threat intelligence report
│   ├── forensic.css               # [MODIFY] Compatibility bundle importing layered base
│   └── forensic-cyber.css         # [MODIFY] Compatibility bundle importing layered base
```

---

### Step 0: Fix Chromium Default Header/Footer Suppression

#### [MODIFY] `core/engine.py`
Replace `--print-to-pdf-no-header` with `--no-pdf-header-footer`:

```python
cmd = [
    chosen_browser,
    "--headless",
    "--disable-gpu",
    "--no-sandbox",
    "--run-all-compositor-stages-before-draw",
    "--no-pdf-header-footer",
    f"--print-to-pdf={dst_pdf.resolve()}",
    str(src_html.resolve())
]
```

---

### Phase 1: Declarative Style Manifest Architecture

#### [NEW] `core/style.py`
Create a lightweight, robust `StyleManifest` loader:

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any
import yaml

@dataclass
class StyleManifest:
    name: str
    title: str = ""
    css_files: List[Path] = field(default_factory=list)
    lua_filters: List[Path] = field(default_factory=list)
    include_in_header: List[Path] = field(default_factory=list)
    include_after_body: List[Path] = field(default_factory=list)
    enable_enrichment: bool = False
    enable_auto_nowrap: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, name_or_path: str, styles_dir: Path) -> "StyleManifest":
        """Discovers and resolves style from YAML manifest or standalone CSS."""
        ...
```

#### [MODIFY] `core/engine.py`
Refactor `run()` to remove domain hardcoding:
- Replace `self.resolve_style()` with `StyleManifest.load()`.
- Replace hardcoded `if is_cyber` with `if manifest.enable_enrichment:`.
- Replace hardcoded template injection with `manifest.include_after_body`.
- Pass `manifest.css_files` and `manifest.lua_filters` directly into Pandoc.

---

### Phase 2: Composable CSS Design System

#### [NEW] `styles/base/tokens.css`
Define standardized CSS custom properties, shared typography stacks, and alert color definitions.

#### [NEW] `styles/base/tables.css`
Consolidate all table layout rules:
- Universal timestamp protection:
  ```css
  td.nowrap, th.nowrap, .nowrap, .nowrap * {
    white-space: nowrap !important;
    word-break: keep-all !important;
    overflow-wrap: normal !important;
  }
  ```
- Inline technical identifiers:
  ```css
  code:not(pre code), kbd, samp, .ioc, .cyber-ioc, .mitre-pill, .eid, .custom-pill {
    white-space: nowrap !important;
    word-break: keep-all !important;
    overflow-wrap: normal !important;
  }
  ```
- Hashes and long tokens allowed to break:
  ```css
  code.hash, .hash, code.break-all, .break-all {
    white-space: normal !important;
    word-break: break-all !important;
    overflow-wrap: anywhere !important;
  }
  ```

#### [MODIFY] `styles/base/print.css`
Consolidate Chromium paged-media rules:
- `@page { margin: 15mm 15mm 15mm 15mm; }`
- Strict suppression of screen HUDs (`#cyber-hud`, `#ioc-inspector-drawer`, `#report-toc-hud`, `.theme-toggle`).
- Page-break controls: `tr, img, figure, table, .callout { break-inside: avoid; }`.

#### [NEW] `styles/forensic/theme.css` & `styles/forensic/cyber.css`
Streamline forensic CSS from 4,000 lines down to clean aesthetic skins (~300 lines each) that `@import` or layer on top of `base/`.

---

### Phase 3: Consolidated Lua AST Filters

#### [MODIFY] `filters/table-nowrap.lua`
Consolidate table cell analysis, timestamp detection, crushed column width normalization, and automatic `.hash` tagging.

#### [DELETE / DEPRECATE]
Retain backwards-compatible stubs or replace monolithic filters with the shared pipeline filter.

---

## 4. Verification Plan

### Automated Tests
1. **Chromium Default Header Suppression**:
   ```bash
   python3 -m core.cli examples/school-report-sample.md -s school -o output/test_school.pdf
   pdftotext output/test_school.pdf - | grep -iE "([0-9]+/[0-9]+/[0-9]+|file:///)"
   ```
   *Expected Result*: Empty output (no browser timestamp or `file:///` URL in extracted text).

2. **SVJ Meeting Notice & School Report (Generic Documents)**:
   ```bash
   python3 -m core.cli examples/pozvánka-shromáždění-svj.md -s svj/modern -o output/test_pozvanka.pdf
   python3 -m core.cli examples/school-report-sample.md -s school -o output/test_school.pdf
   ```
   *Expected Result*: Zero threat intelligence execution in logs; clean compilation in <8s.

3. **Official Forensic Report**:
   ```bash
   python3 -m core.cli examples/sample-forensic-report.md -s forensic -o output/test_forensic.pdf
   python3 -m core.cli examples/sample-forensic-report.md -s forensic -o output/test_forensic.html
   ```
   *Expected Result*: Title block header intact, abstract rendered, inline code non-breaking, hashes breaking cleanly.

4. **Forensic Cyber Dossier with Threat Intel**:
   ```bash
   python3 -m core.cli examples/sample-forensic-cyber.md -s forensic-cyber -o output/test_cyber.html
   python3 -m core.cli examples/sample-forensic-cyber.md -s forensic-cyber -o output/test_cyber.pdf
   ```
   *Expected Result*: CVE-2024-21762 and CVE-2026-3184 fully populated in drawer; interactive drawer opens on click; dark theme applies; PDF renders 7 pages cleanly.

---

## 5. Execution Order
1. **Fix Step 0 immediately** (Chromium flag fix).
2. Implement **Phase 1** (`core/style.py` & decoupled `engine.py`).
3. Implement **Phase 2** (Modular CSS layers).
4. Implement **Phase 3** (Consolidated Lua filter).
5. Run automated verification suite and update `walkthrough.md`.
