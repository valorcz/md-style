"""
core/svg/processor.py
Pure-Python SVG sanitizer, ID-namespacer, CSS scoper, and viewBox normalizer.
Adheres strictly to Invariant #1 (Zero Pandoc/C-binary dependency) and Invariant #2 (Offline Air-Gap Safety).
"""

import re
import html
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Dict, Set, Tuple

from core.diagnostics import Diagnostics

DANGEROUS_TAGS: Set[str] = {
    "script",
    "foreignobject",
    "applet",
    "object",
    "embed",
    "iframe",
}

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"

ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", XLINK_NS)


class SVGProcessor:
    """Sanitizes, namespaces, scopes CSS, and normalizes SVG vector graphics for DOM inlining."""

    def __init__(self, allow_online: bool = True):
        self.allow_online = allow_online

    @staticmethod
    def _strip_ns(tag: str) -> str:
        """Strips XML namespace prefix from tag name."""
        if "}" in tag:
            return tag.split("}", 1)[1].lower()
        return tag.lower()

    @staticmethod
    def _find_statement_end(css: str, start: int) -> int:
        """Finds the terminating semicolon of a statement, ignoring semicolons inside url(...) or quotes."""
        pos = start
        length = len(css)
        in_quote = None
        in_url = False

        while pos < length:
            ch = css[pos]
            if in_quote:
                if ch == "\\":
                    pos += 2
                    continue
                elif ch == in_quote:
                    in_quote = None
            elif in_url:
                if ch == ")":
                    in_url = False
                elif ch in ('"', "'"):
                    in_quote = ch
            else:
                if ch in ('"', "'"):
                    in_quote = ch
                elif css[pos:pos+4].lower() == "url(":
                    in_url = True
                    pos += 3
                elif ch == ";":
                    return pos
                elif ch == "{":
                    # Reached block before semicolon
                    return -1
            pos += 1
        return -1

    @staticmethod
    def scope_css(css: str, scope_id: str) -> str:
        """
        Prefixes CSS selectors inside <style> with the figure's container ID (#scope_id).
        Preserves @import, @font-face, and @keyframes without mangling.
        """
        if not css or not css.strip():
            return ""

        output_parts = []
        pos = 0
        length = len(css)

        while pos < length:
            # Skip whitespace
            while pos < length and css[pos].isspace():
                output_parts.append(css[pos])
                pos += 1
            if pos >= length:
                break

            # Check for at-rule
            if css[pos] == "@":
                semi_pos = SVGProcessor._find_statement_end(css, pos)
                brace_pos = css.find("{", pos)

                if semi_pos != -1 and (brace_pos == -1 or semi_pos < brace_pos):
                    # Statement-level at-rule: e.g. @import ...;
                    at_stmt = css[pos:semi_pos + 1]
                    output_parts.append(at_stmt)
                    pos = semi_pos + 1
                    continue
                elif brace_pos != -1:
                    # At-rule block: e.g. @font-face { ... } or @keyframes name { ... }
                    at_name_m = re.match(r"@([A-Za-z0-9_\-]+)", css[pos:])
                    at_name = at_name_m.group(1).lower() if at_name_m else ""
                    
                    if at_name in {"font-face", "import"}:
                        # Keep @font-face as-is
                        # Find matching closing brace
                        depth = 0
                        start = pos
                        while pos < length:
                            if css[pos] == "{":
                                depth += 1
                            elif css[pos] == "}":
                                depth -= 1
                                if depth == 0:
                                    pos += 1
                                    break
                            pos += 1
                        output_parts.append(css[start:pos])
                        continue
                    elif at_name == "keyframes" or at_name.endswith("keyframes"):
                        # Keep @keyframes as-is
                        depth = 0
                        start = pos
                        while pos < length:
                            if css[pos] == "{":
                                depth += 1
                            elif css[pos] == "}":
                                depth -= 1
                                if depth == 0:
                                    pos += 1
                                    break
                            pos += 1
                        output_parts.append(css[start:pos])
                        continue
                    else:
                        # Other at-rule (like @media): scope selectors inside recursively
                        header = css[pos:brace_pos + 1]
                        output_parts.append(header)
                        pos = brace_pos + 1
                        depth = 1
                        inner_start = pos
                        while pos < length and depth > 0:
                            if css[pos] == "{":
                                depth += 1
                            elif css[pos] == "}":
                                depth -= 1
                                if depth == 0:
                                    break
                            pos += 1
                        inner_css = css[inner_start:pos]
                        output_parts.append(SVGProcessor.scope_css(inner_css, scope_id))
                        if pos < length and css[pos] == "}":
                            output_parts.append("}")
                            pos += 1
                        continue

            # Standard CSS rule: selector { decls }
            brace_pos = css.find("{", pos)
            if brace_pos == -1:
                # Remaining trailing content
                output_parts.append(css[pos:])
                break

            raw_selector = css[pos:brace_pos].strip()
            # Find closing brace
            close_brace = css.find("}", brace_pos)
            if close_brace == -1:
                output_parts.append(css[pos:])
                break

            decls = css[brace_pos:close_brace + 1]

            # Scope each comma-separated selector
            scoped_selectors = []
            for sel in raw_selector.split(","):
                sel = sel.strip()
                if not sel:
                    continue
                # If selector is root 'svg', map directly to container #scope_id
                if sel == "svg":
                    scoped_selectors.append(f"#{scope_id}")
                elif sel.startswith("svg "):
                    scoped_selectors.append(f"#{scope_id} {sel[4:].strip()}")
                elif sel.startswith(":root"):
                    scoped_selectors.append(f"#{scope_id}")
                else:
                    scoped_selectors.append(f"#{scope_id} {sel}")

            if scoped_selectors:
                output_parts.append(", ".join(scoped_selectors) + " " + decls)
            else:
                output_parts.append(raw_selector + " " + decls)

            pos = close_brace + 1

        return "".join(output_parts)

    def process(
        self,
        svg_content: str,
        prefix: str,
        scope_id: str,
        source_label: str = "SVG"
    ) -> Tuple[str, bool]:
        """
        Processes SVG markup:
          - Sanitizes dangerous elements and attributes.
          - Namespaces all IDs and reference attributes with 'prefix'.
          - Scopes CSS selectors inside <style> with '#scope_id'.
          - Normalizes viewBox and ensures responsive scaling.
        Returns: (processed_svg_html, success_flag)
        """
        if not svg_content or not svg_content.strip():
            return "", False

        # 1. Parse XML safely
        try:
            # Strip XML declaration / DOCTYPE if present for cleaner parsing
            clean_xml = re.sub(r"<\?xml[^>]*\?>", "", svg_content.strip(), count=1)
            clean_xml = re.sub(r"<!DOCTYPE[^>]*>", "", clean_xml, count=1).strip()
            
            # Protect unescaped ampersands inside <style> blocks from crashing XML parser
            def _escape_style_amps(m: re.Match) -> str:
                tag_open, style_body, tag_close = m.groups()
                # Escape & not followed by entity name
                fixed_body = re.sub(r"&(?!([a-zA-Z]+|#\d+|#x[0-9a-fA-F]+);)", "&amp;", style_body)
                return f"{tag_open}{fixed_body}{tag_close}"

            clean_xml = re.compile(r"(<style\b[^>]*>)(.*?)(</style>)", re.DOTALL | re.IGNORECASE).sub(_escape_style_amps, clean_xml)
            root = ET.fromstring(clean_xml)
        except Exception as ex:
            Diagnostics.warn(f"Failed to parse {source_label} as XML: {ex}")
            return svg_content, False

        # Verify root is <svg>
        if self._strip_ns(root.tag) != "svg":
            Diagnostics.warn(f"{source_label} root element is '<{root.tag}>', expected '<svg>'.")
            return svg_content, False

        # 2. Collect all IDs declared in the SVG for namespacing
        id_map: Dict[str, str] = {}
        for elem in root.iter():
            elem_id = elem.get("id")
            if elem_id and elem_id.strip():
                clean_id = elem_id.strip()
                id_map[clean_id] = f"{prefix}_{clean_id}"

        # 3. Traverse and sanitize elements & attributes
        nodes_to_remove = []

        def _clean_node(parent: Optional[ET.Element], elem: ET.Element):
            tag_name = self._strip_ns(elem.tag)

            # Check dangerous tag
            if tag_name in DANGEROUS_TAGS:
                Diagnostics.warn(f"Stripped dangerous '<{tag_name}>' tag from {source_label}")
                if parent is not None:
                    nodes_to_remove.append((parent, elem))
                    return

            # Sanitize attributes
            attrs_to_delete = []
            for attr_name, attr_val in list(elem.attrib.items()):
                clean_attr_name = attr_name.lower().split("}")[-1]

                # Strip inline event handlers: onclick, onload, onerror, etc.
                if clean_attr_name.startswith("on"):
                    Diagnostics.warn(f"Stripped inline event handler '{clean_attr_name}' from {source_label}")
                    attrs_to_delete.append(attr_name)
                    continue

                # Check href / xlink:href for javascript: or dangerous URIs
                if clean_attr_name in {"href", "xlink:href"}:
                    val_low = attr_val.strip().lower()
                    if val_low.startswith(("javascript:", "vbscript:", "data:text/html")):
                        Diagnostics.warn(f"Stripped malicious '{clean_attr_name}' URI from {source_label}")
                        attrs_to_delete.append(attr_name)
                        continue
                    if not self.allow_online and val_low.startswith(("http://", "https://")):
                        Diagnostics.warn(f"Air-gap: stripped remote WAN link in '{clean_attr_name}' from {source_label}")
                        attrs_to_delete.append(attr_name)
                        continue

            for a in attrs_to_delete:
                del elem.attrib[a]

            # Namespace element id
            if "id" in elem.attrib and elem.attrib["id"] in id_map:
                elem.attrib["id"] = id_map[elem.attrib["id"]]

            # Namespace reference attributes (url(#...), href="#...", etc.)
            for attr_name, attr_val in list(elem.attrib.items()):
                if "#" in attr_val:
                    new_val = attr_val
                    for old_id, new_id in id_map.items():
                        # Replace url(#old_id)
                        new_val = re.sub(
                            rf"url\(['\"]?#{re.escape(old_id)}['\"]?\)",
                            f"url(#{new_id})",
                            new_val
                        )
                        # Replace href="#old_id"
                        if new_val == f"#{old_id}":
                            new_val = f"#{new_id}"
                    elem.attrib[attr_name] = new_val

            # Recursively clean children
            for child in list(elem):
                _clean_node(elem, child)

        _clean_node(None, root)

        for parent, child in nodes_to_remove:
            try:
                parent.remove(child)
            except Exception:
                pass

        # 4. Process <style> blocks: scope CSS selectors & update ID references
        for elem in root.iter():
            if self._strip_ns(elem.tag) == "style" and elem.text:
                style_css = elem.text

                # Update ID references in CSS: url(#old_id) -> url(#new_id)
                for old_id, new_id in id_map.items():
                    style_css = re.sub(
                        rf"url\(['\"]?#{re.escape(old_id)}['\"]?\)",
                        f"url(#{new_id})",
                        style_css
                    )
                    style_css = re.sub(
                        rf"#{re.escape(old_id)}\b",
                        f"#{new_id}",
                        style_css
                    )

                # Scope CSS rules with container #scope_id
                scoped = self.scope_css(style_css, scope_id)
                elem.text = scoped

        # 5. Normalize viewBox and responsive dimensions
        has_viewbox = "viewBox" in root.attrib or "viewbox" in root.attrib
        width_str = root.attrib.get("width", "").strip()
        height_str = root.attrib.get("height", "").strip()

        def _to_num(val: str) -> Optional[float]:
            val_clean = re.sub(r"(px|pt|mm|cm|in)$", "", val.strip(), flags=re.IGNORECASE).strip()
            try:
                return float(val_clean)
            except Exception:
                return None

        w_num = _to_num(width_str)
        h_num = _to_num(height_str)

        if not has_viewbox and w_num is not None and h_num is not None and w_num > 0 and h_num > 0:
            # Auto-synthesize viewBox="0 0 w h"
            root.attrib["viewBox"] = f"0 0 {int(w_num) if w_num.is_integer() else w_num} {int(h_num) if h_num.is_integer() else h_num}"
            Diagnostics.info(f"Synthesized missing viewBox for {source_label}: '{root.attrib['viewBox']}'")

        # Set responsive width and height
        root.attrib["width"] = "100%"
        root.attrib["height"] = "auto"
        if "preserveAspectRatio" not in root.attrib and "preserveaspectratio" not in root.attrib:
            root.attrib["preserveAspectRatio"] = "xMidYMid meet"

        # Ensure root SVG element has the scope_id as its ID so internal scoped CSS rules match
        # both when rendered in place and when cloned into Lightbox modals or saved standalone.
        root.attrib["id"] = scope_id

        # 6. Serialize back to HTML-ready SVG markup
        try:
            serialized = ET.tostring(root, encoding="unicode", method="xml")
            return serialized, True
        except Exception as ex:
            Diagnostics.warn(f"Failed to serialize processed SVG for {source_label}: {ex}")
            return svg_content, False
