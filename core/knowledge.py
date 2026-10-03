"""
core/knowledge.py
Custom case and document knowledge base manager (YAML / JSON).
Discovers, parses, validates, and compiles investigator-provided knowledge files
into normalized threat/entity intelligence records and AST matcher manifests.
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from core.diagnostics import Diagnostics

class KnowledgeEntry:
    """Represents a single custom intelligence definition."""
    def __init__(self, data: Dict[str, Any], source_file: str, index: int):
        self.source_file = source_file
        self.index = index
        self.raw_data = data

        # Identifier
        self.id: str = str(data.get("id") or data.get("match") or f"custom-{index}").strip()
        
        # Match rules
        match_cfg = data.get("match")
        self.exact_matches: List[str] = []
        self.regex_pattern: Optional[str] = None
        self.in_code: bool = True
        self.in_prose: bool = True
        self.case_sensitive: bool = False

        if isinstance(match_cfg, str):
            self.exact_matches.append(match_cfg)
        elif isinstance(match_cfg, list):
            self.exact_matches.extend(str(m) for m in match_cfg if m)
        elif isinstance(match_cfg, dict):
            if "exact" in match_cfg:
                exact_val = match_cfg["exact"]
                if isinstance(exact_val, list):
                    self.exact_matches.extend(str(m) for m in exact_val if m)
                elif isinstance(exact_val, str):
                    self.exact_matches.append(exact_val)
            if "regex" in match_cfg and match_cfg["regex"]:
                self.regex_pattern = str(match_cfg["regex"])
            self.in_code = bool(match_cfg.get("in_code", True))
            self.in_prose = bool(match_cfg.get("in_prose", True))
            self.case_sensitive = bool(match_cfg.get("case_sensitive", False))
        elif "id" in data and not match_cfg:
            self.exact_matches.append(str(data["id"]))

        # Also support aliases list at top level
        if "aliases" in data and isinstance(data["aliases"], list):
            self.exact_matches.extend(str(a) for a in data["aliases"] if a)

        # Presentation metadata
        self.title: str = str(data.get("title") or self.id)
        self.badge: str = str(data.get("badge") or "CUSTOM ENTITY").upper()
        self.badge_type: str = str(data.get("badge_type") or data.get("badge_class") or "custom").lower()
        self.category: str = str(data.get("category") or data.get("tactic") or "CASE KNOWLEDGE").upper()
        self.role: str = str(data.get("role") or data.get("type") or "Case Entity")
        self.summary: str = str(data.get("summary") or data.get("description") or "Investigator-annotated case entity.")
        
        # Custom key-value fields
        self.fields: Dict[str, str] = {}
        fields_input = data.get("fields") or data.get("attributes") or data.get("meta") or {}
        if isinstance(fields_input, dict):
            for k, v in fields_input.items():
                self.fields[str(k).upper()] = str(v)

        # Intel blocks
        self.investigation_tips: List[str] = [str(x) for x in data.get("investigation_tips", []) if x]
        self.attacker_behavior: List[str] = [str(x) for x in data.get("attacker_behavior", []) if x]
        self.benign_causes: List[str] = [str(x) for x in data.get("benign_causes", []) if x]
        
        # Pivot links
        self.pivots: List[Dict[str, str]] = []
        pivots_input = data.get("pivots") or data.get("links") or []
        if isinstance(pivots_input, list):
            for p in pivots_input:
                if isinstance(p, dict) and "url" in p:
                    self.pivots.append({
                        "label": str(p.get("label") or "CASE REFERENCE ↗"),
                        "url": str(p["url"])
                    })
                elif isinstance(p, str):
                    self.pivots.append({"label": "CASE REFERENCE ↗", "url": p})

        # Compiled regex
        self._compiled_regex = None
        if self.regex_pattern:
            try:
                flags = 0 if self.case_sensitive else re.IGNORECASE
                self._compiled_regex = re.compile(self.regex_pattern, flags)
            except Exception as e:
                Diagnostics.warn(f"[Knowledge] Invalid regex '{self.regex_pattern}' in {source_file}: {e}")

    def matches(self, token: str) -> bool:
        """Returns True if the given token matches this knowledge entry."""
        if not token:
            return False
        clean_token = token.strip()
        for exact in self.exact_matches:
            if self.case_sensitive:
                if clean_token == exact:
                    return True
            else:
                if clean_token.lower() == exact.lower():
                    return True
        if self._compiled_regex:
            return bool(self._compiled_regex.search(clean_token))
        return False

    def to_kb_record(self, matched_token: Optional[str] = None) -> Dict[str, Any]:
        """Converts into normalized KB format for browser drawer consumption."""
        val = matched_token or self.id
        return {
            "type": "custom",
            "custom": True,
            "id": self.id,
            "val": val,
            "title": self.title,
            "badge": self.badge,
            "badge_type": self.badge_type,
            "category": self.category,
            "role": self.role,
            "summary": self.summary,
            "fields": self.fields,
            "investigation_tips": self.investigation_tips,
            "attacker_behavior": self.attacker_behavior,
            "benign_causes": self.benign_causes,
            "pivots": self.pivots
        }


class KnowledgeManager:
    """Manages custom case knowledge discovery, loading, and compilation."""

    def __init__(self):
        self.entries: List[KnowledgeEntry] = []
        self._exact_map: Dict[str, KnowledgeEntry] = {}
        self.loaded_files: List[Path] = []
        self.knowledge_root: Optional[Path] = None

    @classmethod
    def discover_path(cls, doc_path: Path, explicit_path: Optional[Path] = None) -> Optional[Path]:
        """
        Discovers the custom knowledge location:
        1. Explicit path (CLI or frontmatter)
        2. Sibling directory: ./knowledge or ./kb
        3. Sibling file: ./knowledge.yaml, ./knowledge.yml, ./kb.yaml
        4. Parent case directories (e.g. 0report/../knowledge or ../kb)
        """
        if explicit_path:
            p = explicit_path if explicit_path.is_absolute() else (doc_path.parent / explicit_path)
            if p.exists():
                return p.resolve()
            return None

        doc_dir = doc_path.parent.resolve()

        # Check in document directory
        candidates = [
            doc_dir / "knowledge",
            doc_dir / "kb",
            doc_dir / "knowledge.yaml",
            doc_dir / "knowledge.yml",
            doc_dir / "kb.yaml",
            doc_dir / "kb.json",
        ]
        for c in candidates:
            if c.exists():
                return c

        # Check in parent directories up to 3 levels (e.g., case root)
        curr = doc_dir.parent
        for _ in range(3):
            if curr == curr.parent:
                break
            candidates = [
                curr / "knowledge",
                curr / "kb",
                curr / "case-knowledge",
                curr / "knowledge.yaml",
                curr / "knowledge.yml",
            ]
            for c in candidates:
                if c.exists():
                    return c
            curr = curr.parent

        return None

    def load(self, target_path: Path) -> int:
        """Loads knowledge files from a directory or single file."""
        self.entries.clear()
        self._exact_map.clear()
        self.loaded_files.clear()
        self.knowledge_root = target_path

        files_to_read: List[Path] = []
        if target_path.is_file():
            files_to_read.append(target_path)
        elif target_path.is_dir():
            for ext in ("*.yaml", "*.yml", "*.json"):
                files_to_read.extend(sorted(target_path.glob(ext)))

        for fpath in files_to_read:
            self._load_file(fpath)

        # Build exact lookup map
        for entry in self.entries:
            for exact in entry.exact_matches:
                k = exact if entry.case_sensitive else exact.lower()
                if k not in self._exact_map:
                    self._exact_map[k] = entry

        return len(self.entries)

    def _load_file(self, fpath: Path):
        """Loads entries from a single YAML or JSON file."""
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()

            raw_items = []
            if fpath.suffix.lower() in (".yaml", ".yml"):
                if not HAS_YAML:
                    Diagnostics.warn(f"[Knowledge] PyYAML not installed. Skipping {fpath.name}")
                    return
                loaded = yaml.safe_load(content)
                if isinstance(loaded, list):
                    raw_items = loaded
                elif isinstance(loaded, dict):
                    # Could be { "entities": [...] } or dictionary of id -> entry
                    if "entities" in loaded and isinstance(loaded["entities"], list):
                        raw_items = loaded["entities"]
                    else:
                        for k, v in loaded.items():
                            if isinstance(v, dict):
                                if "id" not in v:
                                    v["id"] = k
                                raw_items.append(v)
            elif fpath.suffix.lower() == ".json":
                loaded = json.loads(content)
                if isinstance(loaded, list):
                    raw_items = loaded
                elif isinstance(loaded, dict):
                    raw_items = [loaded]

            for idx, item in enumerate(raw_items):
                if isinstance(item, dict):
                    entry = KnowledgeEntry(item, source_file=fpath.name, index=idx)
                    self.entries.append(entry)

            self.loaded_files.append(fpath)
        except Exception as e:
            Diagnostics.warn(f"[Knowledge] Failed to parse {fpath.name}: {e}")

    def find_entry(self, token: str) -> Optional[KnowledgeEntry]:
        """Finds the knowledge entry matching a token."""
        if not token:
            return None
        clean = token.strip()
        # 1. Fast exact map check
        lower = clean.lower()
        if clean in self._exact_map:
            return self._exact_map[clean]
        if lower in self._exact_map:
            return self._exact_map[lower]

        # 2. Iterate regex rules
        for entry in self.entries:
            if entry.matches(clean):
                return entry
        return None

    def enrich_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Resolves metadata for a token."""
        entry = self.find_entry(token)
        if entry:
            return entry.to_kb_record(matched_token=token)
        return None

    def export_lua_manifest(self) -> Dict[str, Any]:
        """
        Exports a lightweight manifest for the Pandoc Lua filter to know which tokens
        and prose regexes should be tagged as interactive pills.
        """
        exact_tokens: List[Dict[str, Any]] = []
        prose_rules: List[Dict[str, Any]] = []

        for entry in self.entries:
            # Code tokens
            if entry.in_code:
                for exact in entry.exact_matches:
                    exact_tokens.append({
                        "token": exact,
                        "id": entry.id,
                        "case_sensitive": entry.case_sensitive
                    })

            # Prose rules
            if entry.in_prose:
                for exact in entry.exact_matches:
                    # Word boundary pattern for prose matching
                    pattern = r"\b" + re.escape(exact) + r"\b"
                    prose_rules.append({
                        "pattern": pattern,
                        "token": exact,
                        "id": entry.id,
                        "case_sensitive": entry.case_sensitive
                    })
                if entry.regex_pattern:
                    prose_rules.append({
                        "pattern": entry.regex_pattern,
                        "token": entry.id,
                        "id": entry.id,
                        "case_sensitive": entry.case_sensitive
                    })

        return {
            "exact_tokens": exact_tokens,
            "prose_rules": prose_rules
        }
