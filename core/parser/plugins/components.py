"""
core/parser/plugins/components.py
Markdown-it-py plugin for document-defined interactive Svelte components.

Supports fenced blocks:
```component LogicalPhysicalMap title="MMU Address Mapping" #mmu-map
initialFilter: "procA"
```

or:
```svelte ./components/LogicalPhysicalMap.svelte
initialFilter: "fault"
```
"""

import re
import html
import json
import yaml
from typing import Optional, Dict, Any
from markdown_it import MarkdownIt


def parse_props(content: str) -> Dict[str, Any]:
    """Parses component properties from block body (YAML or JSON)."""
    text = content.strip()
    if not text:
        return {}
    try:
        parsed = yaml.safe_load(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    return {}


def components_plugin(md: MarkdownIt):
    """Registers fence rule for interactive document components."""
    orig_fence = md.renderer.rules.get("fence")

    def fence_wrapper(tokens, idx, options, env):
        token = tokens[idx]
        info = token.info.strip() if token.info else ""

        is_component = False
        rest = ""

        if info.startswith("component"):
            is_component = True
            rest = info[len("component"):].strip()
        elif info.startswith("svelte"):
            is_component = True
            rest = info[len("svelte"):].strip()
        elif info.startswith("{.component") or info.startswith("{.svelte"):
            is_component = True
            rest = info.strip("{}").strip()
            if rest.startswith(".component"):
                rest = rest[len(".component"):].strip()
            elif rest.startswith(".svelte"):
                rest = rest[len(".svelte"):].strip()

        if is_component:
            parts = rest.split()
            target = parts[0] if parts else ""
            attrs_str = " ".join(parts[1:]) if len(parts) > 1 else ""

            # Extract id and title/caption
            id_attr = ""
            id_m = re.search(r"#([A-Za-z0-9_\-]+)", attrs_str)
            if id_m:
                id_attr = id_m.group(1)

            caption = ""
            cap_m = re.search(r'(?:caption|title)=["\']([^"\']+)["\']', attrs_str)
            if cap_m:
                caption = cap_m.group(1)

            # Component name resolution
            # If target is a file path like ./components/LogicalPhysicalMap.svelte, derive component name
            comp_path = target
            comp_name = target
            if "/" in target or target.endswith(".svelte"):
                comp_name = target.split("/")[-1].replace(".svelte", "")

            # Parse props from fence content
            props = parse_props(token.content)
            props_json = json.dumps(props, ensure_ascii=False)
            safe_props_attr = html.escape(props_json, quote=True)

            # Track in env for stage 4 / stage 5 compilation
            if isinstance(env, dict):
                comp_registry = env.setdefault("doc_components", {})
                comp_registry[comp_name] = {
                    "name": comp_name,
                    "target": comp_path,
                    "props": props
                }

            fig_id_attr = f' id="{html.escape(id_attr)}"' if id_attr else ""
            caption_html = ""
            if caption:
                caption_html = (
                    f'  <figcaption class="doc-figure-caption">\n'
                    f'    <span class="caption-text">{html.escape(caption)}</span>\n'
                    f'  </figcaption>\n'
                )

            # Emit container with mount point and accessible static fallback
            html_out = (
                f'<figure class="doc-figure doc-component-container"{fig_id_attr} data-component="{html.escape(comp_name)}">\n'
                f'  <div class="doc-component-mount" data-component="{html.escape(comp_name)}" data-props="{safe_props_attr}">\n'
                f'    <div class="doc-component-fallback">\n'
                f'      <span class="fallback-badge">⚡ Interactive Component</span>\n'
                f'      <strong class="fallback-title">{html.escape(comp_name)}</strong>\n'
                f'      <span class="fallback-hint">Loading interactive view...</span>\n'
                f'    </div>\n'
                f'  </div>\n'
                f'{caption_html}'
                f'</figure>\n'
            )
            return html_out

        if orig_fence:
            return orig_fence(tokens, idx, options, env)
        return ""

    md.renderer.rules["fence"] = fence_wrapper
