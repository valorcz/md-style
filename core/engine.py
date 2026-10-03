"""
core/engine.py
Multi-stage modular pipeline orchestrator:
  Stage 1: Pre-processing & Diagram Rendering (beautiful-mermaid via Bun/Node)
  Stage 2: Modular Indicator Discovery & Threat Intelligence Enrichment
  Stage 3: Pure Pandoc AST Compilation (Semantic HTML + Lua filters)
  Stage 4: Post-Assembly & Output Generation (KB injection, template attach, PDF export)
"""

import sys
import os
import re
import json
import shutil
import tempfile
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple

from .config import (
    PROJECT_DIR, STYLES_DIR, TEMPLATES_DIR, FILTERS_DIR,
    TEMPLATES, STYLE_CATEGORIES
)
from .diagnostics import Colors, Diagnostics, PipelineTimer, DiagnosticMetrics
from .diagrams import MermaidRenderer
from .enrichers import registry, CustomKnowledgeEnricher
from .knowledge import KnowledgeManager
from .i18n import resolve_locale, generate_pandoc_metadata_args, generate_css_custom_properties

@dataclass
class PipelineConfig:
    input_file: Path
    output_file: Optional[Path] = None
    style: Optional[str] = None
    title: Optional[str] = None
    lang: Optional[str] = None
    toc: bool = True
    toc_depth: int = 3
    number_sections: bool = False
    embed_resources: bool = True
    highlight_style: str = "kate"
    paged: bool = False
    print_mode: bool = False
    generate_pdf: bool = False
    pdf_engine: Optional[str] = None
    enable_mermaid: bool = True
    auto_nowrap: bool = True
    allow_online: bool = True
    knowledge_path: Optional[Path] = None
    verbose: bool = False
    quiet: bool = False

class ReportEngine:
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.timer = PipelineTimer()
        self.metrics = DiagnosticMetrics()
        Diagnostics.verbose = config.verbose

    def resolve_style(self) -> Tuple[str, Path]:
        """Resolves the active style name and CSS path."""
        style_param = self.config.style
        if style_param:
            # Explicit style passed
            p = Path(style_param)
            if p.is_file():
                return p.stem, p.resolve()
            # Check relative to STYLES_DIR
            candidate = STYLES_DIR / style_param
            if candidate.is_file():
                return candidate.stem, candidate.resolve()
            candidate_css = STYLES_DIR / f"{style_param}.css"
            if candidate_css.is_file():
                return style_param, candidate_css.resolve()
            candidate_dir = STYLES_DIR / style_param / "style.css"
            if candidate_dir.is_file():
                return style_param, candidate_dir.resolve()
            # Fallback
            return p.stem, p.resolve()

        # Inspect frontmatter
        try:
            with open(self.config.input_file, "r", encoding="utf-8") as f:
                content = f.read(2048)
            fm_match = re.search(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
            if fm_match:
                fm_text = fm_match.group(1)
                m = re.search(r"^(?:style|theme|layout):\s*['\"]?([a-zA-Z0-9_\-\/]+)['\"]?", fm_text, re.MULTILINE)
                if m:
                    name = m.group(1).strip()
                    candidate = STYLES_DIR / f"{name}.css"
                    if candidate.is_file():
                        return name, candidate.resolve()
                    candidate_dir = STYLES_DIR / name / "style.css"
                    if candidate_dir.is_file():
                        return name, candidate_dir.resolve()
                    if "-" in name:
                        hierarchical_css = STYLES_DIR / (name.replace("-", "/", 1) + ".css")
                        if hierarchical_css.is_file():
                            return name, hierarchical_css.resolve()
                    return name, candidate.resolve()
        except Exception:
            pass

        # Default style is forensic
        default_css = STYLES_DIR / "forensic.css"
        return "forensic", default_css.resolve()

    def parse_frontmatter(self, content: str) -> Dict[str, Any]:
        """Simple frontmatter extractor."""
        fm = {}
        m = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if m:
            for line in m.group(1).splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(":", 1)
                if len(parts) == 2:
                    key = parts[0].strip().lower()
                    val = parts[1].strip().strip("'\"")
                    fm[key] = val
        return fm

    def run(self) -> Path:
        """Executes the 4-stage pipeline."""
        total_start = self.timer.start("total")

        if not self.config.quiet:
            Diagnostics.info(f"Initiating modular build: {self.config.input_file.name}")

        # Determine target output file
        if not self.config.output_file:
            stem = self.config.input_file.stem
            ext = ".pdf" if self.config.generate_pdf else ".html"
            self.config.output_file = self.config.input_file.parent / f"{stem}{ext}"

        # Resolve Style
        style_name, css_path = self.resolve_style()
        if not self.config.quiet:
            Diagnostics.info(f"Target format: {self.config.output_file.name} | Theme: {style_name}")

        with open(self.config.input_file, "r", encoding="utf-8") as f:
            raw_content = f.read()

        fm = self.parse_frontmatter(raw_content)

        # Frontmatter overrides
        doc_lang = self.config.lang or fm.get("lang") or fm.get("language") or "en"
        doc_title = self.config.title or fm.get("title")

        # Resolve cascading layered locale catalog
        locale_catalog = resolve_locale(doc_lang, style_name, fm)
        css_custom_props = generate_css_custom_properties(locale_catalog)
        pandoc_meta_args = generate_pandoc_metadata_args(locale_catalog)

        if "toc" in fm and not hasattr(self.config, "_user_custom_toc"):
            fm_toc = fm["toc"].lower()
            if fm_toc in {"false", "no", "0"}:
                self.config.toc = False

        # Resolve custom knowledge location (CLI > frontmatter > auto-discovery)
        explicit_kb = self.config.knowledge_path
        if not explicit_kb and "knowledge" in fm:
            fm_kb = str(fm["knowledge"]).strip()
            explicit_kb = Path(fm_kb)
        kb_path = KnowledgeManager.discover_path(self.config.input_file, explicit_kb)

        knowledge_mgr = KnowledgeManager()
        custom_rules_count = 0
        manifest_tmp_path: Optional[Path] = None
        if kb_path:
            custom_rules_count = knowledge_mgr.load(kb_path)
            if not self.config.quiet and custom_rules_count > 0:
                Diagnostics.info(f"Loaded {custom_rules_count} custom knowledge definitions from {kb_path.name}")
            # Register CustomKnowledgeEnricher in enricher registry
            registry.register(CustomKnowledgeEnricher(knowledge_mgr))

        # ------------------------------------------------------------------
        # STAGE 1: Pre-processing & Diagram Rendering
        # ------------------------------------------------------------------
        self.timer.start("stage1")
        processed_md = raw_content
        rendered_diagrams = 0
        fallback_diagrams = 0

        if self.config.enable_mermaid:
            renderer = MermaidRenderer()
            processed_md, rendered_diagrams, fallback_diagrams = renderer.transform_markdown(
                raw_content, lang=locale_catalog.get("code", "en")
            )
            self.metrics.diagrams_rendered = rendered_diagrams

        self.timer.stop("stage1")
        if not self.config.quiet and rendered_diagrams > 0:
            Diagnostics.info(f"Stage 1: Pre-rendered {rendered_diagrams} Mermaid diagrams to static SVG ({self.timer.get('stage1'):.2f}s)")

        # ------------------------------------------------------------------
        # STAGE 2: Modular Token Discovery & Enrichment
        # ------------------------------------------------------------------
        self.timer.start("stage2")
        kb_data: Dict[str, Any] = {}
        unresolved_indicators: List[Dict[str, Any]] = []

        # Run Stage 2 enrichment for cyber styles or when indicators exist
        is_cyber = (style_name == "forensic-cyber" or "cyber" in style_name)
        if is_cyber:
            # Configure online permission on providers
            for enricher in registry.get_all():
                prov = getattr(enricher, "provider", None)
                if prov and hasattr(prov, "allow_online"):
                    prov.allow_online = self.config.allow_online

            # Extract tokens using modular enrichers on markdown text + inline code backticks
            candidate_tokens = set()
            for enricher in registry.get_all():
                try:
                    candidate_tokens.update(enricher.extract_tokens(processed_md))
                except Exception:
                    pass

            code_tokens = set(re.findall(r"`([^`\n]+)`", processed_md))
            candidate_tokens.update(t.strip() for t in code_tokens if t.strip())

            for token_clean in candidate_tokens:
                for enricher in registry.get_all():
                    if enricher.can_handle(token_clean):
                        res = enricher.enrich(token_clean)
                        if res:
                            kb_data[token_clean] = res
                            is_unres = res.get("unresolved", False)
                            if is_unres:
                                unresolved_indicators.append({
                                    "token": token_clean,
                                    "module": enricher.name,
                                    "reason": res.get("error_reason", "Not found in database or online sources")
                                })
                            self.metrics.record_token(
                                token=token_clean,
                                module=enricher.name,
                                line=0,
                                resolved=not is_unres,
                                metadata_preview=res.get("title") or res.get("name") or "",
                                cached=True
                            )
                        break

            # Save dirty caches
            for enricher in registry.get_all():
                prov = getattr(enricher, "provider", None)
                if prov and hasattr(prov, "save_cache"):
                    prov.save_cache()

        self.timer.stop("stage2")
        if not self.config.quiet and kb_data:
            resolved_count = len(kb_data) - len(unresolved_indicators)
            Diagnostics.info(f"Stage 2: Discovered {len(kb_data)} indicators ({resolved_count} resolved, {len(unresolved_indicators)} unresolved) ({self.timer.get('stage2'):.2f}s)")
            if unresolved_indicators:
                Diagnostics.warn(f"{len(unresolved_indicators)} threat indicator(s) could not be verified from knowledge sources:")
                for unres in unresolved_indicators:
                    print(f"  {Colors.YELLOW}⚠{Colors.RESET} {Colors.BOLD}{unres['token']}{Colors.RESET}: {unres['reason']}", file=sys.stderr)

        # ------------------------------------------------------------------
        # STAGE 3: Pure Pandoc AST Compilation
        # ------------------------------------------------------------------
        self.timer.start("stage3")

        # Determine intermediate output
        target_html = self.config.output_file if not self.config.generate_pdf else self.config.output_file.with_suffix(".tmp.html")
        target_html.parent.mkdir(parents=True, exist_ok=True)

        # Check Pandoc installed
        if not shutil.which("pandoc"):
            Diagnostics.error("Pandoc executable not found in PATH.")
            sys.exit(1)

        pandoc_cmd = [
            "pandoc",
            "--standalone",
            "-f", "markdown+smart+gfm_auto_identifiers+pipe_tables"
        ]

        if self.config.embed_resources and not self.config.generate_pdf:
            pandoc_cmd.append("--embed-resources")

        # Stylesheets
        fonts_css = STYLES_DIR / "fonts.css"
        base_css = STYLES_DIR / "base.css"
        if fonts_css.is_file():
            pandoc_cmd.extend(["--css", str(fonts_css)])
        if base_css.is_file():
            pandoc_cmd.extend(["--css", str(base_css)])
        pandoc_cmd.extend(["--css", str(css_path)])

        # Print / Paged options
        if self.config.paged:
            paged_css = STYLES_DIR / "paged.css"
            paged_hdr = TEMPLATES["paged-header"]
            if paged_css.is_file():
                pandoc_cmd.extend(["--css", str(paged_css)])
            if paged_hdr.is_file():
                pandoc_cmd.append(f"--include-in-header={paged_hdr}")
        elif self.config.print_mode:
            print_css = STYLES_DIR / "print.css"
            print_act = TEMPLATES["print-action"]
            if print_css.is_file():
                pandoc_cmd.extend(["--css", str(print_css)])
            if print_act.is_file():
                pandoc_cmd.append(f"--include-after-body={print_act}")

        # Interactive Screen Enhancements (TOC, IoC drawer, reading bar)
        if not self.config.print_mode and not self.config.generate_pdf:
            if is_cyber and TEMPLATES["forensic-cyber"].is_file():
                pandoc_cmd.append(f"--include-after-body={TEMPLATES['forensic-cyber']}")
            elif (style_name.startswith("forensic") or style_name in ("forensic", "forensic/dossier", "forensic/base")) and TEMPLATES["forensic"].is_file():
                pandoc_cmd.append(f"--include-after-body={TEMPLATES['forensic']}")

        # TOC & Sections
        if self.config.toc:
            pandoc_cmd.extend(["--toc", f"--toc-depth={self.config.toc_depth}"])
        if self.config.number_sections:
            pandoc_cmd.append("--number-sections")

        # Highlighting & Meta
        if self.config.highlight_style != "none":
            pandoc_cmd.append(f"--highlight-style={self.config.highlight_style}")
        if doc_title:
            pandoc_cmd.extend(["--metadata", f"title={doc_title}"])
        
        # Extend with layered i18n metadata arguments (--metadata=lang:..., --metadata=toc-title:...)
        pandoc_cmd.extend(pandoc_meta_args)

        # Custom Knowledge Base Manifest for Lua Filter
        if custom_rules_count > 0:
            manifest_data = knowledge_mgr.export_lua_manifest()
            manifest_file = tempfile.NamedTemporaryFile("w", suffix="-kb-manifest.json", delete=False, encoding="utf-8")
            json.dump(manifest_data, manifest_file, ensure_ascii=False, indent=2)
            manifest_file.close()
            manifest_tmp_path = Path(manifest_file.name)
            pandoc_cmd.extend(["--metadata", f"custom-knowledge-manifest={manifest_tmp_path.resolve()}"])

        # Prepend CSS custom properties style block
        if css_custom_props:
            processed_md = f"<style>\n{css_custom_props}\n</style>\n\n" + processed_md

        # Lua Filters
        callouts_lua = FILTERS_DIR / "callouts.lua"
        octicons_lua = FILTERS_DIR / "octicons.lua"
        if callouts_lua.is_file():
            pandoc_cmd.append(f"--lua-filter={callouts_lua}")
        if octicons_lua.is_file():
            pandoc_cmd.append(f"--lua-filter={octicons_lua}")

        # SVJ filter
        if "svj" in style_name or re.search(r"(\[TOC\]|<!--\s*TOC\s*-->|:::\s*\{\.toc\})", processed_md):
            svj_lua = FILTERS_DIR / "svj-prep.lua"
            if svj_lua.is_file():
                pandoc_cmd.append(f"--lua-filter={svj_lua}")

        # Style-specific filters with hierarchical discovery
        filter_candidates = [
            STYLES_DIR / f"{style_name}.lua",
            (STYLES_DIR / (style_name.replace("/", "-") + ".lua")) if "/" in style_name else None,
            (STYLES_DIR / (style_name.replace("-", "/", 1) + ".lua")) if "-" in style_name else None,
            (STYLES_DIR / (style_name.split("/")[0] + "/" + style_name.split("/")[0] + ".lua")) if "/" in style_name else None,
            (STYLES_DIR / (style_name.split("/")[0] + ".lua")) if "/" in style_name else None,
        ]
        for fc in filter_candidates:
            if fc and fc.is_file():
                pandoc_cmd.append(f"--lua-filter={fc.resolve()}")
                break

        pandoc_cmd.extend(["-o", str(target_html)])

        # Run Pandoc
        try:
            res = subprocess.run(
                pandoc_cmd,
                input=processed_md,
                text=True,
                capture_output=True,
                check=False
            )
            if res.returncode != 0:
                Diagnostics.error(f"Pandoc compilation failed:\n{res.stderr}")
                sys.exit(res.returncode)
        except Exception as e:
            Diagnostics.error(f"Failed to execute pandoc: {e}")
            sys.exit(1)

        self.timer.stop("stage3")
        if not self.config.quiet:
            Diagnostics.info(f"Stage 3: Pandoc AST compilation complete ({self.timer.get('stage3'):.2f}s)")

        # ------------------------------------------------------------------
        # STAGE 4: Post-Assembly & Output Generation
        # ------------------------------------------------------------------
        self.timer.start("stage4")

        # Inject KB Data and i18n into HTML if not already injected
        if target_html.is_file():
            with open(target_html, "r", encoding="utf-8") as f:
                html_out = f.read()

            injected_blocks = []

            # 1. Injected i18n catalog
            if locale_catalog:
                i18n_json_str = json.dumps(locale_catalog, ensure_ascii=False, indent=2)
                i18n_tag = f'<script id="report-i18n" type="application/json">\n{i18n_json_str}\n</script>'
                if 'id="report-i18n"' in html_out:
                    html_out = re.sub(r'<script id="report-i18n"[^>]*>.*?</script>', i18n_tag, html_out, flags=re.DOTALL)
                else:
                    injected_blocks.append(i18n_tag)

            # 2. Injected threat intelligence knowledge base
            if kb_data:
                kb_json_str = json.dumps(kb_data, ensure_ascii=False, indent=2)
                kb_tag = f'<script id="cyber-kb-data" type="application/json">\n{kb_json_str}\n</script>'
                if 'id="cyber-kb-data"' in html_out:
                    html_out = re.sub(r'<script id="cyber-kb-data"[^>]*>.*?</script>', kb_tag, html_out, flags=re.DOTALL)
                else:
                    injected_blocks.append(kb_tag)

            if injected_blocks:
                injection_str = "\n" + "\n".join(injected_blocks) + "\n"
                if "</body>" in html_out:
                    html_out = html_out.replace("</body>", f"{injection_str}</body>")
                else:
                    html_out += injection_str

                with open(target_html, "w", encoding="utf-8") as f:
                    f.write(html_out)

        # PDF Compilation if requested
        if self.config.generate_pdf:
            self._compile_pdf(target_html, self.config.output_file)
            if target_html.is_file() and target_html != self.config.output_file:
                target_html.unlink(missing_ok=True)

        self.timer.stop("stage4")
        total_time = self.timer.stop("total")

        if not self.config.quiet:
            Diagnostics.success(f"Report generated: {self.config.output_file.resolve()} (Total: {total_time:.2f}s)")

        if manifest_tmp_path and manifest_tmp_path.exists():
            try:
                manifest_tmp_path.unlink()
            except Exception:
                pass

        return self.config.output_file

    def _compile_pdf(self, src_html: Path, dst_pdf: Path):
        """Converts HTML to PDF using Headless Chrome/Chromium or WeasyPrint."""
        browsers = ["chromium-browser", "chromium", "google-chrome", "brave-browser", "microsoft-edge"]
        chosen_browser = None
        for b in browsers:
            if shutil.which(b):
                chosen_browser = b
                break

        if chosen_browser:
            Diagnostics.info(f"Generating PDF via headless {chosen_browser}...")
            cmd = [
                chosen_browser,
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                "--run-all-compositor-stages-before-draw",
                "--print-to-pdf-no-header",
                f"--print-to-pdf={dst_pdf.resolve()}",
                str(src_html.resolve())
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if res.returncode != 0:
                Diagnostics.warn(f"Browser PDF failed: {res.stderr}")
            else:
                return

        # Fallback to WeasyPrint
        if shutil.which("weasyprint"):
            Diagnostics.info("Generating PDF via WeasyPrint...")
            cmd = ["weasyprint", str(src_html.resolve()), str(dst_pdf.resolve())]
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if res.returncode == 0:
                return

        Diagnostics.error("No suitable PDF engine found (install chromium or weasyprint).")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Modular Markdown Report Compiler")
    parser.add_argument("input", nargs="?", default=None, help="Source Markdown document")
    parser.add_argument("output", nargs="?", default=None, help="Target HTML/PDF file")
    parser.add_argument("-s", "--style", help="Style name or CSS path")
    parser.add_argument("-t", "--title", help="Override document title")
    parser.add_argument("-l", "--lang", help="Override document language")
    parser.add_argument("--toc", action="store_true", default=True, help="Enable Table of Contents")
    parser.add_argument("--no-toc", dest="toc", action="store_false", help="Disable Table of Contents")
    parser.add_argument("--toc-depth", type=int, default=3, help="TOC heading depth")
    parser.add_argument("-N", "--number-sections", action="store_true", help="Auto-number sections")
    parser.add_argument("--paged", action="store_true", help="Enable Paged.js preview")
    parser.add_argument("--print", dest="print_mode", action="store_true", help="Enable Native Print mode")
    parser.add_argument("--highlight-style", default="kate", help="Pandoc syntax highlighting theme (default: kate)")
    parser.add_argument("--embed-resources", action="store_true", default=True, help="Embed resources into self-contained HTML")
    parser.add_argument("--no-embed-resources", dest="embed_resources", action="store_false", help="Link external stylesheets")
    parser.add_argument("-p", "--pdf", dest="generate_pdf", action="store_true", help="Generate PDF directly")
    parser.add_argument("--pdf-engine", help="Explicit PDF engine (chromium, weasyprint, etc.)")
    parser.add_argument("--open", dest="open_after", action="store_true", help="Open generated report in viewer")
    parser.add_argument("--no-mermaid", dest="enable_mermaid", action="store_false", default=True, help="Disable Mermaid diagram rendering")
    parser.add_argument("--no-auto-nowrap", dest="auto_nowrap", action="store_false", default=True, help="Disable auto-nowrap on tables")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose debug output")
    parser.add_argument("-q", "--quiet", action="store_true", help="Quiet output")

    args = parser.parse_args()

    if not args.input:
        Diagnostics.error("No input markdown file specified.")
        print("Try 'md-to-report.sh --help' for usage information.", file=sys.stderr)
        sys.exit(1)

    cfg = PipelineConfig(
        input_file=Path(args.input),
        output_file=Path(args.output) if args.output else None,
        style=args.style,
        title=args.title,
        lang=args.lang,
        toc=args.toc,
        toc_depth=args.toc_depth,
        number_sections=args.number_sections,
        embed_resources=args.embed_resources,
        highlight_style=args.highlight_style,
        paged=args.paged,
        print_mode=args.print_mode,
        generate_pdf=args.generate_pdf,
        pdf_engine=args.pdf_engine,
        enable_mermaid=args.enable_mermaid,
        auto_nowrap=args.auto_nowrap,
        verbose=args.verbose,
        quiet=args.quiet
    )

    engine = ReportEngine(cfg)
    out_file = engine.run()

    if getattr(args, "open_after", False) and out_file and out_file.is_file():
        if shutil.which("xdg-open"):
            subprocess.Popen(["xdg-open", str(out_file.resolve())], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif shutil.which("open"):
            subprocess.Popen(["open", str(out_file.resolve())], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    main()
