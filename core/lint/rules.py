"""
core/lint/rules.py
Modular prose, structural rhythm, and typographic linting rules.
"""

import re
from typing import List, Optional, Set
from core.lint.models import Issue, LintResult, LinterProfile, LintConfig


def check_density_rules(result: LintResult, profile: LinterProfile, config: LintConfig):
    """E001 and E002: Document-wide formatting density checks."""
    if "E001" not in config.disabled_rules:
        if result.bold_density > profile.fail_bold:
            result.issues.append(
                Issue(
                    code="E001",
                    category="Emphasis",
                    message=(
                        f"Critical bold font density: {result.bold_density:.1f}% "
                        f"(target for '{profile.name}': {profile.target_bold[0]:.0f}–{profile.target_bold[1]:.0f}%, "
                        f"ceiling: {profile.max_bold:.0f}%)"
                    ),
                    severity="FAIL",
                    penalty=15.0,
                )
            )
        elif result.bold_density > profile.max_bold:
            result.issues.append(
                Issue(
                    code="E001",
                    category="Emphasis",
                    message=(
                        f"Elevated bold font density: {result.bold_density:.1f}% "
                        f"(target for '{profile.name}': {profile.target_bold[0]:.0f}–{profile.target_bold[1]:.0f}%)"
                    ),
                    severity="WARN",
                    penalty=8.0,
                )
            )

    if "E002" not in config.disabled_rules:
        if result.italic_density > profile.fail_italic:
            result.issues.append(
                Issue(
                    code="E002",
                    category="Emphasis",
                    message=(
                        f"Critical italic font density: {result.italic_density:.1f}% "
                        f"(target for '{profile.name}': {profile.target_italic[0]:.0f}–{profile.target_italic[1]:.0f}%, "
                        f"ceiling: {profile.max_italic:.0f}%)"
                    ),
                    severity="FAIL",
                    penalty=10.0,
                )
            )
        elif result.italic_density > profile.max_italic:
            result.issues.append(
                Issue(
                    code="E002",
                    category="Emphasis",
                    message=(
                        f"Elevated italic font density: {result.italic_density:.1f}% "
                        f"(target for '{profile.name}': {profile.target_italic[0]:.0f}–{profile.target_italic[1]:.0f}%)"
                    ),
                    severity="WARN",
                    penalty=5.0,
                )
            )


def check_headings_and_structure(
    lines: List[str],
    result: LintResult,
    profile: LinterProfile,
    config: LintConfig,
):
    """H001-H009 and R003: Heading hygiene, hierarchy, and list structure."""
    in_code = False
    in_frontmatter = False
    frontmatter_count = 0

    current_list_count = 0
    list_start_line = 0

    h1_count = 0
    prev_heading_level: Optional[int] = None
    first_heading = True
    seen_headings: dict = {}

    for i, line in enumerate(lines):
        line_str = line.strip()

        if line_str == "---":
            frontmatter_count += 1
            in_frontmatter = frontmatter_count < 2
            continue
        if in_frontmatter:
            continue

        if line_str.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue

        # R003: Bullet Hell (excessive unsegmented list items)
        if "R003" not in config.disabled_rules:
            if re.match(r"^(\*|-|\d+\.)\s+", line):
                if current_list_count == 0:
                    list_start_line = i + 1
                current_list_count += 1
            elif not line.startswith(("  ", "\t")):
                if current_list_count > profile.max_list_items and not line_str.startswith("<"):
                    result.issues.append(
                        Issue(
                            code="R003",
                            category="Structure",
                            message=(
                                f"Excessive continuous list ({current_list_count} items > limit {profile.max_list_items}) "
                                f"without subheadings or segmentation"
                            ),
                            line=list_start_line,
                            severity="WARN",
                            penalty=3.0,
                        )
                    )
                current_list_count = 0

        # Headings: H001, H002, H003, H004
        if line_str.startswith("#"):
            h_level = len(line_str) - len(line_str.lstrip("#"))
            h_text = line_str.lstrip("#").strip()

            # H001: Heading character length
            if "H001" not in config.disabled_rules:
                if len(h_text) > profile.max_heading_chars:
                    result.issues.append(
                        Issue(
                            code="H001",
                            category="Heading",
                            message=f"Heading too long ({len(h_text)} chars > limit {profile.max_heading_chars}): '{h_text[:45]}...'",
                            line=i + 1,
                            snippet=h_text,
                            severity="WARN",
                            penalty=2.0,
                        )
                    )

            # H002: Heading word count
            if "H002" not in config.disabled_rules:
                h_words = len(h_text.split())
                if h_words > profile.max_heading_words:
                    result.issues.append(
                        Issue(
                            code="H002",
                            category="Heading",
                            message=f"Heading contains too many words ({h_words} words > limit {profile.max_heading_words}): '{h_text[:45]}...'",
                            line=i + 1,
                            snippet=h_text,
                            severity="WARN",
                            penalty=2.0,
                        )
                    )

            # H003: Trailing punctuation in heading
            if "H003" not in config.disabled_rules:
                if h_text.endswith((".", ":", ";")):
                    result.issues.append(
                        Issue(
                            code="H003",
                            category="Heading",
                            message=f"Heading ends with punctuation ('{h_text[-1]}'): '{h_text}'",
                            line=i + 1,
                            snippet=h_text,
                            severity="WARN",
                            penalty=1.5,
                        )
                    )

            # H004: Headless section (heading immediately followed by another heading)
            if "H004" not in config.disabled_rules:
                for next_i in range(i + 1, min(i + 6, len(lines))):
                    next_str = lines[next_i].strip()
                    if not next_str:
                        continue
                    if next_str.startswith("<") or next_str.startswith("!["):
                        break
                    if next_str.startswith("#"):
                        result.issues.append(
                            Issue(
                                code="H004",
                                category="Heading",
                                message=f"Section without introductory body text: #{h_level} heading immediately followed by #{len(next_str) - len(next_str.lstrip('#'))}",
                                line=i + 1,
                                snippet=h_text,
                                severity="WARN",
                                penalty=3.0,
                            )
                        )
                    break

            # H005: Multiple H1 headings (Single H1 principle)
            if h_level == 1:
                h1_count += 1
                if "H005" not in config.disabled_rules and h1_count > profile.max_h1_count:
                    result.issues.append(
                        Issue(
                            code="H005",
                            category="Structure",
                            message=(
                                f"Multiple H1 headings in document ({h1_count} > limit {profile.max_h1_count}). "
                                f"Use H2 for major sections to maintain single-root outline and accessibility."
                            ),
                            line=i + 1,
                            snippet=h_text,
                            severity="WARN",
                            penalty=3.0,
                        )
                    )

            # H006: Skipped heading levels (e.g. H1 directly to H3)
            if prev_heading_level is not None and "H006" not in config.disabled_rules:
                if h_level > prev_heading_level + 1:
                    result.issues.append(
                        Issue(
                            code="H006",
                            category="Structure",
                            message=(
                                f"Heading level skipped from H{prev_heading_level} directly to H{h_level} "
                                f"(expected H{prev_heading_level + 1}). Maintain sequential hierarchy."
                            ),
                            line=i + 1,
                            snippet=h_text,
                            severity="WARN",
                            penalty=2.5,
                        )
                    )

            # H007: Excessive heading depth (e.g. H5 or H6)
            if "H007" not in config.disabled_rules and h_level > profile.max_heading_depth:
                result.issues.append(
                    Issue(
                        code="H007",
                        category="Structure",
                        message=(
                            f"Excessive heading depth (H{h_level} > max H{profile.max_heading_depth}). "
                            f"Overly deep nesting reduces readability; consider using bold paragraph intros."
                        ),
                        line=i + 1,
                        snippet=h_text,
                        severity="WARN",
                        penalty=2.0,
                    )
                )

            # H008: Duplicate heading titles
            norm_title = re.sub(r"[^\w\s-]", "", h_text.lower()).strip()
            if "H008" not in config.disabled_rules and norm_title:
                if norm_title in seen_headings:
                    orig_line = seen_headings[norm_title]
                    result.issues.append(
                        Issue(
                            code="H008",
                            category="Structure",
                            message=(
                                f"Duplicate heading title '{h_text}' (previously defined on line {orig_line}). "
                                f"Duplicate headings cause anchor collisions and confuse Table of Contents."
                            ),
                            line=i + 1,
                            snippet=h_text,
                            severity="WARN",
                            penalty=2.0,
                        )
                    )
                else:
                    seen_headings[norm_title] = i + 1

            # H009: First heading entrance level
            if first_heading:
                first_heading = False
                if "H009" not in config.disabled_rules and h_level > 2:
                    result.issues.append(
                        Issue(
                            code="H009",
                            category="Structure",
                            message=(
                                f"Document starts with deeply nested heading H{h_level}. "
                                f"The first heading should be H1 (or H2 if title is defined in frontmatter)."
                            ),
                            line=i + 1,
                            snippet=h_text,
                            severity="WARN",
                            penalty=2.0,
                        )
                    )

            prev_heading_level = h_level


def check_line_rules(
    lines: List[str],
    result: LintResult,
    profile: LinterProfile,
    config: LintConfig,
):
    """R002, R004, E003, E004, E005, T001, T002."""
    in_details = False
    in_table = False

    is_czech_or_slovak = config.lang in ("cs", "sk", "czech", "slovak")
    allowed_terms = config.allowed_capitalized_terms

    for idx, line in enumerate(lines, 1):
        line_str = line.strip()

        if "<details" in line_str:
            in_details = True
        if "</details>" in line_str:
            in_details = False
            continue

        if line_str.startswith("|"):
            in_table = True
        elif in_table and not line_str.startswith("|"):
            in_table = False

        if in_details or in_table or not line_str:
            continue

        # R002: Wall of Text in a paragraph
        if "R002" not in config.disabled_rules:
            if not line_str.startswith(("#", "*", "-", ">", "<", "|", "1.", "2.", "3.", "4.", "5.")):
                p_words = len(re.findall(r"\b\w+\b", line_str))
                if p_words > profile.max_paragraph_words:
                    result.issues.append(
                        Issue(
                            code="R002",
                            category="Structure",
                            message=f"Monolithic wall-of-text paragraph ({p_words} words > limit {profile.max_paragraph_words})",
                            line=idx,
                            snippet=line_str[:50] + "...",
                            severity="WARN",
                            penalty=2.0,
                        )
                    )

        # E004: Bold Stacking in list item
        if "E004" not in config.disabled_rules:
            if re.match(r"^(\*|-|\d+\.)\s+\*\*", line_str):
                bolds = re.findall(r"\*\*([^*]+)\*\*", line_str)
                if len(bolds) > 1:
                    if profile.penalize_bold_stacking:
                        result.issues.append(
                            Issue(
                                code="E004",
                                category="Emphasis",
                                message=f"Bold stacking in single bullet: label + extra bold block '**{bolds[1][:30]}**'",
                                line=idx,
                                snippet=line_str[:60],
                                severity="WARN",
                                penalty=1.5,
                            )
                        )
                    else:
                        result.issues.append(
                            Issue(
                                code="E004",
                                category="Emphasis",
                                message=f"Bold stacking in bullet: label + '**{bolds[1][:30]}**'",
                                line=idx,
                                snippet=line_str[:60],
                                severity="INFO",
                                penalty=0.0,
                            )
                        )

        # E003: Entire sentence bolded
        if "E003" not in config.disabled_rules:
            full_bolds = re.findall(r"(?:^|[.!?]\s+)\*\*([^*]+)\*\*[.!?]", line_str)
            for fb in full_bolds:
                fb_words = len(re.findall(r"\b\w+\b", fb))
                if fb_words > 8:
                    result.issues.append(
                        Issue(
                            code="E003",
                            category="Emphasis",
                            message=f"Entire complex sentence is bolded ({fb_words} words): '**{fb[:35]}...**'",
                            line=idx,
                            snippet=fb[:50],
                            severity="WARN",
                            penalty=2.0,
                        )
                    )

        # E005: Stacked emphasis (***text***)
        if "E005" not in config.disabled_rules:
            if "***" in line_str:
                result.issues.append(
                    Issue(
                        code="E005",
                        category="Emphasis",
                        message="Stacked emphasis (bold italic ***text***)",
                        line=idx,
                        snippet=line_str[:50],
                        severity="INFO",
                        penalty=1.0,
                    )
                )

        # R004: Bullet Run-on (> 3 sentences, > 250 chars)
        if "R004" not in config.disabled_rules:
            if re.match(r"^(\*|-)\s+", line_str):
                sentences = re.split(r"[.!?]\s+[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ]", line_str)
                if len(sentences) > 3 and len(line_str) > 250:
                    result.issues.append(
                        Issue(
                            code="R004",
                            category="Structure",
                            message=f"List bullet is overly verbose ({len(sentences)} sentences, {len(line_str)} chars); consider converting to body paragraph",
                            line=idx,
                            snippet=line_str[:50] + "...",
                            severity="INFO",
                            penalty=1.5,
                        )
                    )

        # T001: Capital in parentheses (Language-gated for cs/sk)
        if is_czech_or_slovak and "T001" not in config.disabled_rules:
            paren_matches = re.finditer(r"(?<!^)\(([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]{2,}[^)]*)\)", line_str)
            for pm in paren_matches:
                content = pm.group(1).strip()
                if re.search(r"\b(19\d\d|20\d\d)\b", content):
                    continue
                parts = [p.strip() for p in content.split(",")]
                if len(parts) > 1 and all(p and p[0].isupper() for p in parts if p):
                    continue
                first_word = content.split()[0].rstrip(",;:.")
                if first_word not in allowed_terms and not content.isupper():
                    result.issues.append(
                        Issue(
                            code="T001",
                            category="Typography",
                            message=f"Suspicious uppercase word in parentheses inside Czech sentence: '({content[:30]})'",
                            line=idx,
                            snippet=pm.group(0),
                            severity="WARN",
                            penalty=1.0,
                        )
                    )

        # T002: Double punctuation / typographical collision
        if "T002" not in config.disabled_rules:
            if re.search(r"(\.\)|\?\!\.|\,\s*\:|\.\s*\.)", line_str):
                result.issues.append(
                    Issue(
                        code="T002",
                        category="Typography",
                        message="Typographical punctuation collision (e.g. '.)' or double period)",
                        line=idx,
                        snippet=line_str[:50],
                        severity="INFO",
                        penalty=0.5,
                    )
                )
