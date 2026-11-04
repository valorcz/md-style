"""
core/lint/linter.py
Core prose, rhythm, and typography linter engine.
"""

import re
import sys
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, Set

from core.lint.models import LinterProfile, LintResult, LintConfig
from core.lint.profiles import BUILTIN_PROFILES, DEFAULT_ALLOWED_CAPITALIZED_TERMS
from core.lint.rules import check_density_rules, check_headings_and_structure, check_line_rules
from core.lint.readability import calculate_readability


class ProseLinter:
    """Publication-grade Prose & Typography Linter."""

    def __init__(self, config: Optional[LintConfig] = None):
        self.config = config or LintConfig()
        # Ensure built-in profiles are present if not overridden
        self.profiles = dict(BUILTIN_PROFILES)
        if self.config.profiles:
            self.profiles.update(self.config.profiles)

        # Merge allowed terms
        self.allowed_terms = set(DEFAULT_ALLOWED_CAPITALIZED_TERMS)
        if self.config.allowed_capitalized_terms:
            self.allowed_terms.update(self.config.allowed_capitalized_terms)
        self.config.allowed_capitalized_terms = self.allowed_terms

    def detect_profile(self, text: str, requested_name: Optional[str] = None) -> Tuple[LinterProfile, str]:
        """Detects the appropriate linter profile from CLI argument or frontmatter."""
        if requested_name:
            if requested_name in self.profiles:
                return self.profiles[requested_name], "CLI argument"
            else:
                print(f"Warning: Unknown profile '{requested_name}', falling back to 'handbook'.", file=sys.stderr)

        # Inspect frontmatter
        if text.startswith("---"):
            fm_parts = text.split("---", 2)
            if len(fm_parts) >= 3:
                fm = fm_parts[1].lower()
                if "doc_type: article" in fm or "profile: article" in fm or "style: academic/monograph" in fm:
                    return self.profiles["article"], "frontmatter (doc_type: article)"
                if "doc_type: slides" in fm or "profile: slides" in fm or "slidev" in fm:
                    return self.profiles["slides"], "frontmatter (doc_type: slides)"
                if "doc_type: notes" in fm or "profile: notes" in fm:
                    return self.profiles["notes"], "frontmatter (doc_type: notes)"
                if "doc_type: handbook" in fm or "report_type: \"studijní text\"" in fm or "style: \"academic" in fm:
                    return self.profiles["handbook"], "frontmatter (report_type / academic)"

        default_name = self.config.profile_name or "handbook"
        return self.profiles.get(default_name, self.profiles["handbook"]), "default configuration"

    def detect_lang(self, text: str, default_lang: str = "en") -> str:
        """Detects document language from frontmatter."""
        if text.startswith("---"):
            fm_parts = text.split("---", 2)
            if len(fm_parts) >= 3:
                m = re.search(r"^\s*(?:lang|language):\s*['\"]?([a-zA-Z_-]+)['\"]?", fm_parts[1], re.MULTILINE)
                if m:
                    val = m.group(1).lower()
                    if val in ("cz", "czech", "cs"):
                        return "cs"
                    if val in ("sk", "slovak"):
                        return "sk"
                    return val[:2]
                if "style: svj" in fm_parts[1] or "style: \"svj" in fm_parts[1]:
                    return "cs"
        return default_lang

    def extract_frontmatter_lint_config(self, text: str) -> Dict[str, Any]:
        """Extracts prose_lint dictionary from frontmatter if present."""
        if not text.startswith("---"):
            return {}
        try:
            import yaml
            fm_parts = text.split("---", 2)
            if len(fm_parts) >= 3:
                data = yaml.safe_load(fm_parts[1]) or {}
                if isinstance(data, dict):
                    return data.get("prose_lint") or {}
        except Exception:
            pass
        return {}

    def lint_text(
        self,
        text: str,
        file_path: Optional[Path] = None,
        requested_profile: Optional[str] = None,
        lang: Optional[str] = None,
    ) -> LintResult:
        """Lints a Markdown text string and returns a LintResult."""
        # Check frontmatter config overrides
        fm_config = self.extract_frontmatter_lint_config(text)

        # Clone config for this run
        run_config = LintConfig(
            profile_name=requested_profile or fm_config.get("profile") or self.config.profile_name,
            profiles=dict(self.profiles),
            allowed_capitalized_terms=set(self.allowed_terms),
            disabled_rules=set(self.config.disabled_rules),
            strict=self.config.strict,
            verbose=self.config.verbose,
            lang=lang or fm_config.get("lang") or self.detect_lang(text, default_lang=self.config.lang),
        )

        if "disabled_rules" in fm_config and isinstance(fm_config["disabled_rules"], list):
            run_config.disabled_rules.update(fm_config["disabled_rules"])

        if "allowed_terms" in fm_config and isinstance(fm_config["allowed_terms"], list):
            run_config.allowed_capitalized_terms.update(fm_config["allowed_terms"])

        profile, detected_via = self.detect_profile(text, requested_name=run_config.profile_name)

        # Apply profile field overrides if specified in frontmatter
        if "profile_overrides" in fm_config and isinstance(fm_config["profile_overrides"], dict):
            for k, v in fm_config["profile_overrides"].items():
                if hasattr(profile, k):
                    setattr(profile, k, v)

        result = LintResult(
            file_path=file_path,
            profile=profile,
            detected_via=detected_via,
            lang=run_config.lang,
        )

        # Strip frontmatter, comments, and fenced code blocks for word calculation
        clean_text = re.sub(r"^---[\s\S]*?---\n", "", text)
        clean_text = re.sub(r"```[\s\S]*?```", "", clean_text)
        clean_text = re.sub(r"<!--[\s\S]*?-->", "", clean_text)

        lines = text.splitlines()

        # Word counts
        words = re.findall(r"\b\w+\b", clean_text)
        result.total_words = len(words) or 1

        bold_matches = re.findall(r"\*\*([^*]+)\*\*", clean_text)
        result.bold_words = sum(len(re.findall(r"\b\w+\b", m)) for m in bold_matches)
        result.bold_density = (result.bold_words / result.total_words) * 100

        italic_matches = re.findall(r"(?<!\*)\*([^*\n]+)\*(?!\*)", clean_text)
        result.italic_words = sum(len(re.findall(r"\b\w+\b", m)) for m in italic_matches)
        result.italic_density = (result.italic_words / result.total_words) * 100

        # Execute rules
        check_density_rules(result, profile, run_config)
        check_headings_and_structure(lines, result, profile, run_config)
        check_line_rules(lines, result, profile, run_config)

        # Compute score
        total_penalties = sum(issue.penalty for issue in result.issues)
        result.score = max(0.0, min(100.0, 100.0 - total_penalties))

        # Compute deterministic readability metrics
        result.readability = calculate_readability(text, lang=run_config.lang)

        return result

    def lint_file(
        self,
        path: Path,
        requested_profile: Optional[str] = None,
        lang: Optional[str] = None,
    ) -> LintResult:
        """Lints a Markdown file from path."""
        if not path.is_file():
            raise FileNotFoundError(f"Markdown file {path} not found.")

        raw_text = path.read_text(encoding="utf-8")
        return self.lint_text(raw_text, file_path=path, requested_profile=requested_profile, lang=lang)
