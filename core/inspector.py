"""
core/inspector.py
Diagnostic and troubleshooting engine that analyzes Markdown documents to inspect
planned security enrichments, AST transformations, and provider resolutions.

Can be executed directly:
  python3 -m core.inspector examples/sample-forensic-cyber.md
  python3 -m core.inspector examples/sample-forensic-cyber.md --dump-ast
  python3 -m core.inspector --list-rules
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, Any, List

from core.diagnostics import Colors
from core.enrichers import get_default_registry, EnricherRegistry

INLINE_CODE_PATTERN = re.compile(r"`([^`]+)`")
CALLOUT_PATTERN = re.compile(r"^>\s*\[!([A-Za-z]+)\]\s*(.*)$")
MERMAID_BLOCK_PATTERN = re.compile(r"^```(?:mermaid)\b", re.IGNORECASE)

class DocumentInspector:
    def __init__(self, registry: EnricherRegistry = None):
        self.registry = registry or get_default_registry()

    def list_rules(self) -> List[Dict[str, str]]:
        rules = []
        for e in self.registry.get_all():
            rules.append({
                "module": e.name,
                "description": e.pattern_description
            })
        return rules

    def inspect_document(self, file_path: Path) -> Dict[str, Any]:
        if not file_path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")

        lines = file_path.read_text(encoding="utf-8").splitlines()

        discovered_tokens = []
        planned_replacements = []
        callouts_found = []
        diagrams_found = []

        kb_payload = {}
        unique_tokens = set()

        in_code_fence = False

        for line_num, line in enumerate(lines, start=1):
            stripped = line.strip()

            # Track fenced code blocks to avoid false positives inside multi-line scripts
            if stripped.startswith("```"):
                if stripped.lower().startswith("```mermaid"):
                    diagrams_found.append({
                        "line": line_num,
                        "type": "mermaid",
                        "preview": line
                    })
                in_code_fence = not in_code_fence
                continue

            if in_code_fence:
                continue

            # 1. Callout detection
            callout_match = CALLOUT_PATTERN.match(stripped)
            if callout_match:
                alert_type = callout_match.group(1).upper()
                callout_title = callout_match.group(2).strip() or alert_type
                callouts_found.append({
                    "line": line_num,
                    "type": alert_type,
                    "original": line,
                    "replacement": f'<div class="callout callout-{alert_type.lower()}"><div class="callout-title">{callout_title}</div>...</div>'
                })

            # 2. Inline code element detection
            for match in INLINE_CODE_PATTERN.finditer(line):
                token = match.group(1).strip()
                if not token or len(token) > 120:
                    continue

                enricher = self.registry.find_enricher_for(token)
                if enricher:
                    unique_tokens.add(token)
                    ast_attrs = enricher.get_ast_attributes(token)

                    # Formulate HTML transformation
                    classes = ast_attrs.get("class", "cyber-ioc")
                    ioc_type = ast_attrs.get("data-ioc-type", "artifact")
                    ioc_val = ast_attrs.get("data-ioc-value", token)
                    html_replacement = f'<code class="{classes}" data-ioc-type="{ioc_type}" data-ioc-value="{ioc_val}">{token}</code>'

                    # Resolve metadata
                    enriched_data = enricher.enrich(token)
                    if enriched_data:
                        kb_payload[token] = enriched_data
                        preview = enriched_data.get("title") or enriched_data.get("name") or "Enriched Record"
                        if enriched_data.get("severity"):
                            preview += f" [{enriched_data.get('severity')}]"
                        elif enriched_data.get("tactics"):
                            preview += f" [Tactics: {', '.join(enriched_data['tactics'])}]"
                        elif enriched_data.get("scope"):
                            preview += f" [{enriched_data.get('scope')}]"
                    else:
                        preview = "Recognized indicator (no metadata)"

                    discovered_tokens.append({
                        "line": line_num,
                        "token": token,
                        "module": enricher.name,
                        "resolved": enriched_data is not None,
                        "preview": preview
                    })

                    planned_replacements.append({
                        "line": line_num,
                        "original": f"`{token}`",
                        "transformed": html_replacement,
                        "module": enricher.name
                    })

            # 3. Plain text indicator extraction (e.g. unbackticked EID 5000, 5001 and 600)
            clean_line = INLINE_CODE_PATTERN.sub("", line)
            for enricher in self.registry.get_all():
                try:
                    for text_token in enricher.extract_tokens(clean_line):
                        if text_token not in unique_tokens and len(text_token) <= 120:
                            unique_tokens.add(text_token)
                            enriched_data = enricher.enrich(text_token)
                            if enriched_data:
                                kb_payload[text_token] = enriched_data
                                preview = enriched_data.get("title") or enriched_data.get("name") or "Enriched Record"
                                if enriched_data.get("severity"):
                                    preview += f" [{enriched_data.get('severity')}]"
                            else:
                                preview = "Recognized indicator"

                            ast_attrs = enricher.get_ast_attributes(text_token)
                            classes = ast_attrs.get("class", "cyber-ioc")
                            ioc_type = ast_attrs.get("data-ioc-type", "artifact")
                            ioc_val = ast_attrs.get("data-ioc-value", text_token)
                            html_replacement = f'<code class="{classes}" data-ioc-type="{ioc_type}" data-ioc-value="{ioc_val}">{text_token}</code>'

                            discovered_tokens.append({
                                "line": line_num,
                                "token": text_token,
                                "module": enricher.name,
                                "resolved": enriched_data is not None,
                                "preview": preview
                            })

                            planned_replacements.append({
                                "line": line_num,
                                "original": text_token,
                                "transformed": html_replacement,
                                "module": enricher.name
                            })
                except Exception:
                    pass

        return {
            "file": str(file_path),
            "total_lines": len(lines),
            "tokens": discovered_tokens,
            "unique_tokens_count": len(unique_tokens),
            "callouts": callouts_found,
            "diagrams": diagrams_found,
            "replacements": planned_replacements,
            "kb_payload": kb_payload
        }

    def print_report(self, result: Dict[str, Any], dump_ast: bool = False):
        print(f"\n{Colors.BOLD}{'=' * 104}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN} DOCUMENT ENRICHMENT & AST REPLACEMENT INSPECTION REPORT{Colors.RESET}")
        print(f"{Colors.BOLD}{'=' * 104}{Colors.RESET}")
        print(f" Target Document: {Colors.BOLD}{result['file']}{Colors.RESET}")
        print(f" Lines Scanned:   {result['total_lines']}")
        print(f" Unique Tokens:   {result['unique_tokens_count']}")

        # 1. Active Enricher Rules
        print(f"\n{Colors.BOLD}[1] ACTIVE ENRICHER RULES{Colors.RESET}")
        print(f"{'-' * 104}")
        print(f" {'MODULE':<18} {'PATTERN DESCRIPTION'}")
        print(f"{'-' * 104}")
        for r in self.list_rules():
            print(f" {Colors.GREEN}{r['module']:<18}{Colors.RESET} {r['description']}")

        # 2. Discovered Tokens & Enrichments
        print(f"\n{Colors.BOLD}[2] DISCOVERED TOKENS & RESOLVED METADATA ({len(result['tokens'])} instances){Colors.RESET}")
        print(f"{'-' * 104}")
        print(f" {'LINE':<6} {'TOKEN':<30} {'MODULE':<16} {'STATUS':<10} {'RESOLVED METADATA PREVIEW'}")
        print(f"{'-' * 104}")

        for item in result["tokens"]:
            status_color = Colors.GREEN if item["resolved"] else Colors.YELLOW
            status_text = "RESOLVED" if item["resolved"] else "IDENTIFIED"
            token_display = item["token"][:28] + (".." if len(item["token"]) > 28 else "")
            preview_display = item["preview"][:44] + ("..." if len(item["preview"]) > 44 else "")

            print(f" L{item['line']:<5} {token_display:<30} {item['module']:<16} {status_color}{status_text:<10}{Colors.RESET} {preview_display}")

        # 3. Callout Transformations
        if result["callouts"]:
            print(f"\n{Colors.BOLD}[3] CALLOUT BLOCKQUOTE TRANSFORMATIONS ({len(result['callouts'])} found){Colors.RESET}")
            print(f"{'-' * 104}")
            for c in result["callouts"]:
                print(f" L{c['line']} [{Colors.YELLOW}{c['type']}{Colors.RESET}]: {c['original']}")
                print(f"    └──▶ {Colors.GRAY}{c['replacement']}{Colors.RESET}")

        # 4. Planned AST Replacements Preview
        print(f"\n{Colors.BOLD}[4] PLANNED AST INLINE CODE TRANSFORMATIONS (Sample Preview){Colors.RESET}")
        print(f"{'-' * 104}")
        sample_replacements = result["replacements"][:12] if not dump_ast else result["replacements"]
        for rep in sample_replacements:
            print(f" L{rep['line']:<4} [{Colors.CYAN}{rep['module']:<14}{Colors.RESET}] {rep['original']}")
            print(f"       └──▶ {Colors.GRAY}{rep['transformed']}{Colors.RESET}")

        if not dump_ast and len(result["replacements"]) > 12:
            print(f"\n {Colors.GRAY}... and {len(result['replacements']) - 12} more replacements (use --dump-ast to view all).{Colors.RESET}")

        # 5. Summary Statistics
        kb_bytes = len(json.dumps(result["kb_payload"]).encode("utf-8"))
        print(f"\n{Colors.BOLD}[5] ENRICHMENT SUMMARY{Colors.RESET}")
        print(f"{'-' * 104}")
        print(f" Total Indicators Scanned:    {len(result['tokens'])}")
        print(f" Unique Indicators Enriched:   {len(result['kb_payload'])}")
        print(f" Pre-computed Payload Size:   {kb_bytes / 1024:.2f} KB (embedded into <script id=\"cyber-kb-data\">)")
        print(f"{'=' * 104}\n")

def main():
    parser = argparse.ArgumentParser(description="Inspect planned document enrichments, AST replacements, and indicator resolution.")
    parser.add_argument("input", nargs="?", help="Markdown file to inspect")
    parser.add_argument("--list-rules", action="store_true", help="Print all active enricher rules and exit")
    parser.add_argument("--dump-ast", action="store_true", help="Dump all AST inline replacements without truncation")
    parser.add_argument("--json", action="store_true", help="Output raw JSON data for CI/CD pipelines")
    args = parser.parse_args()

    inspector = DocumentInspector()

    if args.list_rules:
        rules = inspector.list_rules()
        if args.json:
            print(json.dumps(rules, indent=2))
        else:
            print(f"\n{Colors.BOLD}ACTIVE SECURITY ENRICHER RULES:{Colors.RESET}")
            for r in rules:
                print(f"  • {Colors.CYAN}{r['module']:<18}{Colors.RESET}: {r['description']}")
            print()
        sys.exit(0)

    if not args.input:
        parser.print_help()
        sys.exit(1)

    input_path = Path(args.input)
    try:
        report_data = inspector.inspect_document(input_path)
    except Exception as err:
        print(f"{Colors.RED}[ERROR]{Colors.RESET} Failed to inspect document: {err}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(report_data, indent=2))
    else:
        inspector.print_report(report_data, dump_ast=args.dump_ast)

if __name__ == "__main__":
    main()
