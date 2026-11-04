"""
tests/test_lint_prose.py
Unit tests for core/lint prose and typography linter.
"""

from pathlib import Path
import pytest
from core.lint import ProseLinter, LintConfig, LinterProfile, BUILTIN_PROFILES


def test_builtin_profiles_loaded():
    linter = ProseLinter()
    assert "article" in linter.profiles
    assert "handbook" in linter.profiles
    assert "notes" in linter.profiles
    assert "slides" in linter.profiles


def test_profile_detection_frontmatter():
    linter = ProseLinter()
    text = "---\ntitle: Test\ndoc_type: article\n---\n# Heading\nBody text."
    profile, detected_via = linter.detect_profile(text)
    assert profile.name == "article"
    assert "frontmatter" in detected_via


def test_bold_overload_rule_e001():
    linter = ProseLinter()
    # High bold density
    text = "# Title\n\n**This is all bold text here** **and more bold words**."
    res = linter.lint_text(text, requested_profile="article")
    assert any(i.code == "E001" for i in res.issues)
    assert res.score < 100.0


def test_heading_hygiene_rules_h001_to_h004():
    linter = ProseLinter()
    text = """# This is an excessively long heading that exceeds normal character thresholds for articles

# Heading with trailing period.

## Headless Subheading Immediately
"""
    res = linter.lint_text(text, requested_profile="article")
    codes = [i.code for i in res.issues]
    assert "H001" in codes  # Long heading
    assert "H003" in codes  # Trailing period
    assert "H004" in codes  # Headless section


def test_list_and_paragraph_rules_r002_r003_e004():
    linter = ProseLinter()
    text = """# Section

* Item 1
* Item 2
* Item 3
* Item 4
* Item 5
* Item 6
* Item 7
* Item 8
* Item 9
* Item 10

* **Label**: and here is **another bold block** inside the bullet.
"""
    res = linter.lint_text(text, requested_profile="article")
    codes = [i.code for i in res.issues]
    assert "R003" in codes  # Bullet Hell
    assert "E004" in codes  # Bold Stacking


def test_czech_typography_gated():
    linter = ProseLinter()
    # T001: Capital in parentheses inside Czech text
    cz_text = "---\nlang: cs\n---\n# Nadpis\nToto je česká věta (NeznáméSlovo) s divným slovem."
    res_cz = linter.lint_text(cz_text)
    assert any(i.code == "T001" for i in res_cz.issues)

    # In English document, T001 should not trigger
    en_text = "---\nlang: en\n---\n# Heading\nThis is an English sentence (UnknownWord) inside parens."
    res_en = linter.lint_text(en_text)
    assert not any(i.code == "T001" for i in res_en.issues)


def test_custom_allowed_terms_override():
    linter = ProseLinter()
    # With frontmatter allowed_terms, T001 should be suppressed for that term
    cz_text = """---
lang: cs
prose_lint:
  allowed_terms: ["MojeFirma"]
---
# Nadpis
Věta s povoleným slovem (MojeFirma) uvnitř.
"""
    res = linter.lint_text(cz_text)
    assert not any(i.code == "T001" and "MojeFirma" in i.snippet for i in res.issues)


def test_disabled_rules_config():
    linter = ProseLinter()
    text = """---
prose_lint:
  disabled_rules: ["H003"]
---
# Heading ending with dot.
Normal body text.
"""
    res = linter.lint_text(text)
    assert not any(i.code == "H003" for i in res.issues)


def test_heading_structure_best_practices_h005_to_h009():
    linter = ProseLinter()

    # 1. H005: Multiple H1 headings
    multi_h1 = """# First Main Title
Introduction paragraph text.

# Second Main Title (Should be H2)
Another paragraph text.
"""
    res_h1 = linter.lint_text(multi_h1, requested_profile="handbook")
    assert any(i.code == "H005" for i in res_h1.issues)

    # Slides should allow multiple H1s
    res_slides = linter.lint_text(multi_h1, requested_profile="slides")
    assert not any(i.code == "H005" for i in res_slides.issues)

    # 2. H006: Skipped heading levels (H1 directly to H3)
    skipped_level = """# Chapter One
Intro text.

### Subsection Without H2
Detail text.
"""
    res_skipped = linter.lint_text(skipped_level, requested_profile="handbook")
    assert any(i.code == "H006" for i in res_skipped.issues)

    # 3. H007: Excessive heading depth (H5)
    deep_heading = """# Chapter One
Intro text.

## Section Two
Section text.

### Subsection Three
Sub text.

#### Sub-subsection Four
Sub-sub text.

##### Way Too Deep Five
Deep text.
"""
    res_deep = linter.lint_text(deep_heading, requested_profile="handbook")
    assert any(i.code == "H007" for i in res_deep.issues)

    # 4. H008: Duplicate heading titles
    duplicate_headings = """# Document Title
Intro text.

## Summary Section
First summary.

## Summary Section
Duplicate summary title.
"""
    res_dup = linter.lint_text(duplicate_headings, requested_profile="handbook")
    assert any(i.code == "H008" for i in res_dup.issues)

    # 5. H009: First heading entrance level
    deep_start = """### Starting at H3 directly
Text content.
"""
    res_start = linter.lint_text(deep_start, requested_profile="handbook")
    assert any(i.code == "H009" for i in res_start.issues)

