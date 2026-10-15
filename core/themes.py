"""
core/themes.py
Declarative theme resolution system with hierarchical inheritance (theme.yaml).
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
import yaml

from core.config import STYLES_DIR
from core.diagnostics import Diagnostics

STYLE_NAME_ALIASES = {
    "forensic-cyber": "forensic/cyber",
    "forensic/cyber": "forensic/cyber",
    "forensic": "forensic/dossier",
    "forensic-dossier": "forensic/dossier",
    "forensic/dossier": "forensic/dossier",
    "forensic/base": "forensic/dossier",
    "svj": "svj/base",
    "svj-modern": "svj/base",
    "svj/base": "svj/base",
    "svj-invitation": "svj/invitation",
    "svj/invitation": "svj/invitation",
    "svj-ballot": "svj/ballot",
    "svj/ballot": "svj/ballot",
    "svj-community": "svj/community",
    "svj/community": "svj/community",
    "svj-typewriter": "svj/typewriter",
    "svj/typewriter": "svj/typewriter",
    "announcement": "general/announcement",
    "school": "general/school",
    "family-invite": "general/family-invite",
    "base": "base",
}

@dataclass
class ThemeDefinition:
    name: str
    directory: Path
    title: str = ""
    extends: Optional[str] = None
    stylesheets: List[str] = field(default_factory=list)
    features: Dict[str, bool] = field(default_factory=dict)
    variables: Dict[str, str] = field(default_factory=dict)
    fonts: List[str] = field(default_factory=list)
    highlight_style: str = "one-dark"
    paged: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ResolvedTheme:
    name: str
    title: str
    inheritance_chain: List[str]
    stylesheet_paths: List[Path]
    features: Dict[str, bool]
    variables: Dict[str, str]
    fonts: List[str]
    highlight_style: str = "one-dark"
    paged: Dict[str, Any] = field(default_factory=dict)
    variable_sources: Dict[str, str] = field(default_factory=dict)
    feature_sources: Dict[str, str] = field(default_factory=dict)

    def render_css_variables(self) -> str:
        """Renders CSS custom properties block."""
        if not self.variables:
            return ""
        lines = [":root {"]
        for k, v in self.variables.items():
            var_name = k if k.startswith("--") else f"--{k}"
            lines.append(f"  {var_name}: {v};")
        lines.append("}")
        return "\n".join(lines)

class ThemeResolver:
    """Discovers, loads, and resolves cascading themes."""

    def __init__(self, styles_root: Path = STYLES_DIR):
        self.styles_root = styles_root
        self._themes: Dict[str, ThemeDefinition] = {}
        self.discover_themes()

    def canonicalize_name(self, name: str) -> str:
        cleaned = name.strip().lower()
        return STYLE_NAME_ALIASES.get(cleaned, cleaned)

    def discover_themes(self):
        """Scans styles_root for theme.yaml files."""
        for yaml_path in self.styles_root.glob("**/theme.yaml"):
            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}

                rel_dir = yaml_path.parent.relative_to(self.styles_root)
                theme_name = data.get("name") or str(rel_dir).replace("\\", "/")

                theme_def = ThemeDefinition(
                    name=theme_name,
                    directory=yaml_path.parent,
                    title=data.get("title", theme_name),
                    extends=data.get("extends"),
                    stylesheets=list(data.get("stylesheets") or []),
                    features=dict(data.get("features") or {}),
                    variables=dict(data.get("variables") or {}),
                    fonts=list(data.get("fonts") or []),
                    highlight_style=data.get("highlight_style", "one-dark"),
                    paged=dict(data.get("paged") or {})
                )
                self._themes[theme_name] = theme_def
                self._themes[str(rel_dir).replace("\\", "/")] = theme_def
            except Exception as e:
                Diagnostics.warn(f"Failed to load theme definition from {yaml_path}: {e}")

    def get_theme_definition(self, name: str) -> Optional[ThemeDefinition]:
        canonical = self.canonicalize_name(name)
        if canonical not in self._themes:
            direct_dir = self.styles_root / name
            if (direct_dir / "theme.yaml").exists():
                self.discover_themes()
        return self._themes.get(self.canonicalize_name(name))

    def list_all_theme_definitions(self) -> Dict[str, ThemeDefinition]:
        """Returns unique ThemeDefinitions indexed by primary name."""
        unique: Dict[str, ThemeDefinition] = {}
        for k, v in self._themes.items():
            if v.name not in unique:
                unique[v.name] = v
        return unique

    def resolve(self, requested_name: Optional[str] = None) -> ResolvedTheme:
        name = self.canonicalize_name(requested_name or "base")
        if name not in self._themes:
            # Fallback check if path exists directly
            direct_dir = self.styles_root / name
            if (direct_dir / "theme.yaml").exists():
                self.discover_themes()

        if name not in self._themes:
            Diagnostics.warn(f"Theme '{requested_name}' not found. Falling back to 'base'.")
            name = "base"

        # Build inheritance chain from root base to child
        chain: List[ThemeDefinition] = []
        curr_name: Optional[str] = name
        visited: Set[str] = set()

        while curr_name:
            curr_canonical = self.canonicalize_name(curr_name)
            if curr_canonical in visited:
                Diagnostics.warn(f"Circular theme inheritance detected involving '{curr_canonical}'")
                break
            visited.add(curr_canonical)

            t_def = self._themes.get(curr_canonical)
            if not t_def:
                # If base is missing, synthesize default base
                break
            chain.append(t_def)
            curr_name = t_def.extends

        # Order from base ancestor -> child descendant
        chain.reverse()

        def _merge_dict(base_d: dict, over_d: dict) -> dict:
            res = dict(base_d)
            for k, v in over_d.items():
                if isinstance(v, dict) and k in res and isinstance(res[k], dict):
                    res[k] = _merge_dict(res[k], v)
                else:
                    res[k] = v
            return res

        # Merge properties
        merged_features: Dict[str, bool] = {}
        feature_sources: Dict[str, str] = {}
        merged_variables: Dict[str, str] = {}
        variable_sources: Dict[str, str] = {}
        merged_paged: Dict[str, Any] = {}
        merged_fonts: List[str] = []
        stylesheet_paths: List[Path] = []
        chain_names: List[str] = [t.name for t in chain]
        merged_highlight_style: str = "one-dark"

        for t in chain:
            for fk, fv in t.features.items():
                merged_features[fk] = fv
                feature_sources[fk] = t.name

            for vk, vv in t.variables.items():
                merged_variables[vk] = vv
                variable_sources[vk] = t.name

            merged_paged = _merge_dict(merged_paged, t.paged)
            if t.highlight_style:
                merged_highlight_style = t.highlight_style
            for f in t.fonts:
                if f not in merged_fonts:
                    merged_fonts.append(f)

            for s_name in t.stylesheets:
                s_path = t.directory / s_name
                if s_path.is_file() and s_path not in stylesheet_paths:
                    stylesheet_paths.append(s_path)

        leaf_theme = chain[-1] if chain else ThemeDefinition(name=name, directory=self.styles_root)

        return ResolvedTheme(
            name=name,
            title=leaf_theme.title,
            inheritance_chain=chain_names,
            stylesheet_paths=stylesheet_paths,
            features=merged_features,
            variables=merged_variables,
            fonts=merged_fonts,
            highlight_style=merged_highlight_style,
            paged=merged_paged,
            variable_sources=variable_sources,
            feature_sources=feature_sources
        )
