"""
core/bundler/svelte_compiler.py
Compiles per-document Svelte 5 components into lightweight, self-contained client bundles.
Externalizes the Svelte runtime to the host viewer (window.MdStyleViewer).
"""

import json
import shutil
import hashlib
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from core.diagnostics import Diagnostics

SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "viewer" / "scripts"
COMPILER_SCRIPT = SCRIPTS_DIR / "build-components.mjs"
CACHE_DIR = Path.home() / ".cache" / "md-style" / "components"


class SvelteComponentCompiler:
    """Manages build-time compilation and caching of document-defined Svelte components."""

    def __init__(self, node_or_bun: Optional[str] = None):
        self.runtime = node_or_bun or self._detect_runtime()
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _detect_runtime() -> Optional[str]:
        """Detects whether node or bun is installed on the host system."""
        for binary in ("node", "bun"):
            path = shutil.which(binary)
            if path:
                return path
        return None

    def is_available(self) -> bool:
        """Returns True if a JavaScript runtime and the compiler script are available."""
        return bool(self.runtime and COMPILER_SCRIPT.is_file())

    def compile_components(
        self,
        component_defs: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        Compiles a list of component definitions.
        Each item in component_defs should be: {"name": str, "path": str}

        Returns:
            {
                "success": bool,
                "components": {
                    "Name": { "name": str, "filePath": str, "hash": str, "js": str, "css": str }
                },
                "aggregatedCss": str
            }
        """
        if not component_defs:
            return {"success": True, "components": {}, "aggregatedCss": ""}

        if not self.is_available():
            Diagnostics.warn(
                "Node.js / Bun not found on system. Dynamic Svelte components cannot be compiled "
                "and will render static fallback placeholders."
            )
            return {"success": False, "error": "Runtime not available", "components": {}, "aggregatedCss": ""}

        # Check cache for components
        all_cached = True
        cached_components: Dict[str, Any] = {}
        cached_css_parts: List[str] = []

        for item in component_defs:
            name = item["name"]
            fpath = Path(item["path"])
            if not fpath.is_file():
                all_cached = False
                break
            try:
                content = fpath.read_bytes()
                h = hashlib.sha256(content).hexdigest()
                cache_file = CACHE_DIR / f"{name}_{h[:16]}.json"
                if cache_file.is_file():
                    with open(cache_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        cached_components[name] = data
                        if data.get("css"):
                            cached_css_parts.append(f"/* [md-style component: {name}] */\n{data['css']}\n")
                else:
                    all_cached = False
                    break
            except Exception:
                all_cached = False
                break

        if all_cached and len(cached_components) == len(component_defs):
            return {
                "success": True,
                "components": cached_components,
                "aggregatedCss": "\n".join(cached_css_parts)
            }

        # Run compiler script via subprocess
        try:
            input_json = json.dumps(component_defs)
            cmd = [self.runtime, str(COMPILER_SCRIPT), "-"]
            proc = subprocess.run(
                cmd,
                input=input_json,
                capture_output=True,
                text=True,
                check=False
            )

            if proc.returncode != 0:
                err_msg = proc.stderr.strip() or f"Compiler exited with code {proc.returncode}"
                try:
                    err_json = json.loads(err_msg)
                    err_msg = err_json.get("error", err_msg)
                except Exception:
                    pass
                Diagnostics.warn(f"Failed to compile Svelte components: {err_msg}")
                return {"success": False, "error": err_msg, "components": {}, "aggregatedCss": ""}

            result = json.loads(proc.stdout)
            if not result.get("success"):
                Diagnostics.warn(f"Component compilation failed: {result.get('error')}")
                return result

            # Save to disk cache
            for cname, cinfo in result.get("components", {}).items():
                chash = cinfo.get("hash", "")
                if chash:
                    cache_file = CACHE_DIR / f"{cname}_{chash[:16]}.json"
                    try:
                        with open(cache_file, "w", encoding="utf-8") as f:
                            json.dump(cinfo, f)
                    except Exception:
                        pass

            return result

        except Exception as e:
            Diagnostics.warn(f"Exception while executing Svelte component compiler: {e}")
            return {"success": False, "error": str(e), "components": {}, "aggregatedCss": ""}
