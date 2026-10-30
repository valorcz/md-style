# Product & Technical Roadmap — `md-style`

This document tracks planned architectural milestones and future distribution deliverables for `md-style`.

---

## 1. Standalone Binary & Zero-Prerequisite Distribution

### Goal
Allow any end-user on Linux, macOS, or Windows to compile reports without requiring Python, `uv`, `pip`, or virtual environments installed on their system.

### Planned Milestones:

#### Milestone 1.1: PyInstaller Standalone Executable Packaging
- **Target Deliverables**:
  - `md-style-linux-x86_64` (single-file ELF binary)
  - `md-style-macos-arm64` / `x86_64` (Mach-O universal binary)
  - `md-style-windows-x86_64.exe` (PE executable)
- **Path Resolution**: Audit `core/config.py` and `core/bundler/html_assembler.py` to transparently resolve asset directories (`data/`, `styles/`, `core/assets/`) from PyInstaller's extracted runtime root (`sys._MEIPASS`).
- **Data Bundling**: Embed offline Single Sources of Truth (`data/statutes.json`, `cve.json`, `cwe.json`) and core theme assets directly into the binary package.

#### Milestone 1.2: Node/Bun Runtime Elimination for Server-Side Diagrams
- **Target**: Eliminate the external Node.js / Bun runtime dependency for ahead-of-time Mermaid SVG rendering.
- **Approaches**:
  - **Option A (In-Process QuickJS Engine)**: Integrate a lightweight C-based JavaScript runtime (`quickjs-cffi` / `python-quickjs`) into Python to execute `pele` / diagram compilation directly in-process with 0 external binaries.
  - **Option B (Bundled Portable Bun)**: Provide an automated bootstrap or bundled static `bun` binary (~35 MB) cached in `~/.cache/md-style/bin/bun`.
  - **Option C (Current Fallback)**: Transparent client-side fallback via `pele` inside `viewer.bundle.js` when no JS runtime is available on the compilation host.

#### Milestone 1.3: Automated Multi-Platform Release Pipeline
- **GitHub Actions Release Matrix**: Trigger automated multi-platform compilation on release tags.
- **Homebrew Formula**: `brew install valorcz/tap/md-style` for macOS users.
- **Official OCI Container**: Multi-arch Docker/Podman image (`ghcr.io/valorcz/md-style`) with Chromium and fonts pre-baked for CI/CD pipelines.

---

## 2. Diagram Geometry & Print Page Budgeting

### Goal
Ensure vector diagrams (Mermaid, D2, SVG figures) seamlessly fit the document layout and never overflow printable page heights or render text at disproportionate optical scales.

### Planned Milestones:
- **Optical Font Sizing**: Constrain diagram rendering scale so diagram text visually matches or slightly undershoots body typography (~11–13px).
- **Aspect Ratio & Height Budgeting**: Enforce automatic vertical height ceilings (`max-height: 500px` on screen, `135mm` in print) for tall flowcharts ($H > W$).
- **Figure Geometry Annotations**: Support Markdown attributes (`{.compact}`, `{.tall}`, `{.wide}`, `{.full-page}`) for fine-grained diagram layout overrides.
