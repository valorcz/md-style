"""
core/parser/transforms/entities.py
Scans text and code_inline nodes for recognized Knowledge Pack entities and wraps them in .inspectable elements.
"""

import re
import html
from typing import List, Dict, Any, Optional
from markdown_it.token import Token
from core.kb.models import KnowledgePack, Entity

class EntityAnnotator:
    def __init__(self, pack: KnowledgePack):
        self.pack = pack
        self.entities_by_token: Dict[str, Entity] = {}
        self._build_index()

    def _build_index(self):
        for eid, ent in self.pack.entities.items():
            self.entities_by_token[eid.lower()] = ent
            self.entities_by_token[ent.label.lower()] = ent
            for alias in ent.aliases:
                if alias.strip():
                    self.entities_by_token[alias.lower()] = ent

        unique_tokens = sorted(self.entities_by_token.keys(), key=lambda x: len(x), reverse=True)
        filtered = [t for t in unique_tokens if len(t) >= 3 and not t.isdigit()]
        if filtered:
            escaped = [re.escape(t) for t in filtered]
            pattern_str = r"(?<![\w\-])(" + "|".join(escaped) + r")(?![\w\-])"
            self.regex = re.compile(pattern_str, re.IGNORECASE)
        else:
            self.regex = None

    def match_entity(self, token_str: str) -> Optional[Entity]:
        cleaned = token_str.strip().lower()
        if cleaned in self.entities_by_token:
            return self.entities_by_token[cleaned]
        # Also check for event id variants like "event id 4624" or "eid 4624"
        digits = re.findall(r"\b\d{4,5}\b", cleaned)
        for d in digits:
            if f"event-{d}".lower() in self.entities_by_token:
                return self.entities_by_token[f"event-{d}".lower()]
        return None

    def annotate_text(self, text: str) -> str:
        if not self.regex or not text:
            return text

        def _repl(match: re.Match) -> str:
            raw_matched = match.group(0)
            ent = self.match_entity(raw_matched)
            if not ent:
                return raw_matched

            sev_class = f" inspectable-{ent.severity.lower()}" if ent.severity in ["CRITICAL", "HIGH", "MEDIUM"] else ""
            escaped_text = html.escape(raw_matched)
            return (
                f'<span class="inspectable{sev_class}" '
                f'data-type="{html.escape(ent.type)}" '
                f'data-token="{html.escape(ent.id)}" '
                f'data-domain="{html.escape(ent.domain)}" '
                f'tabindex="0">{escaped_text}</span>'
            )

        return self.regex.sub(_repl, text)

    def annotate_code(self, code_text: str) -> Optional[str]:
        ent = self.match_entity(code_text)
        if not ent:
            return None

        sev_class = f" inspectable-{ent.severity.lower()}" if ent.severity in ["CRITICAL", "HIGH", "MEDIUM"] else ""
        escaped_code = html.escape(code_text)
        return (
            f'<code class="inspectable{sev_class}" '
            f'data-type="{html.escape(ent.type)}" '
            f'data-token="{html.escape(ent.id)}" '
            f'data-domain="{html.escape(ent.domain)}" '
            f'tabindex="0">{escaped_code}</code>'
        )

def transform_entities(tokens: List[Token], pack: KnowledgePack) -> List[Token]:
    """Annotates inline text and inline code tokens with inspectable entity tags."""
    if not pack.entities:
        return tokens

    annotator = EntityAnnotator(pack)

    for tok in tokens:
        if tok.type == "inline" and tok.children:
            new_children: List[Token] = []
            for child in tok.children:
                if child.type == "code_inline" and child.content:
                    annotated_code = annotator.annotate_code(child.content)
                    if annotated_code:
                        html_tok = Token("html_inline", "", 0)
                        html_tok.content = annotated_code
                        new_children.append(html_tok)
                        continue
                elif child.type == "text" and child.content:
                    annotated_text = annotator.annotate_text(child.content)
                    if annotated_text != child.content:
                        html_tok = Token("html_inline", "", 0)
                        html_tok.content = annotated_text
                        new_children.append(html_tok)
                        continue

                new_children.append(child)
            tok.children = new_children

    return tokens
