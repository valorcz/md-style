"""
core/lint/profiles.py
Built-in profiles and baseline allowed dictionaries for prose linting.
"""

from typing import Dict, Set
from core.lint.models import LinterProfile

DEFAULT_ALLOWED_CAPITALIZED_TERMS: Set[str] = {
    # Tech & Industry
    "Title", "Google", "Linux", "Slack", "Teams", "Python", "Rust", "CycloneDX",
    "Locked", "Cloud", "Applicant", "Software", "Digital", "Cyber", "High-Risk",
    "Proof", "Direct", "Restricted", "The", "Accidental", "Essential", "Remote",
    "Prompt", "Insecure", "Training", "S-křivka", "Onboarding", "Růst", "Barcamp",
    "Governance", "Secure", "Cursor", "GitHub", "Pay", "Blue", "Red", "AppSec",
    "Windows", "MacOS", "Apple", "Android", "AWS", "Azure", "GCP", "Kubernetes",
    "Docker", "Markdown", "HTML", "CSS", "JavaScript", "TypeScript", "Svelte",
    "Firefox", "Chromium", "Chrome", "Brave", "Safari", "Edge", "MITRE", "NVD",
    "CVE", "CWE", "ATT&CK", "RO-Crate", "PDF", "SVG", "JSON", "YAML", "XML"
}

BUILTIN_PROFILES: Dict[str, LinterProfile] = {
    "article": LinterProfile(
        name="article",
        title="Scholarly Article / Monograph",
        description="Continuous prose focused on smooth left-to-right reading without visual noise",
        target_bold=(2.0, 5.0),
        max_bold=6.0,
        fail_bold=8.0,
        target_italic=(2.0, 7.0),
        max_italic=8.0,
        fail_italic=12.0,
        allow_bullet_bold_label=False,
        penalize_bold_stacking=True,
        max_paragraph_words=140,
        min_paragraph_words=25,
        max_list_items=6,
        max_heading_chars=50,
        max_heading_words=7,
    ),
    "handbook": LinterProfile(
        name="handbook",
        title="Study Handbook / Practical Manual",
        description="Dual format for studying and quick orientation; permits bold list labels",
        target_bold=(5.0, 9.0),
        max_bold=11.0,
        fail_bold=14.0,
        target_italic=(4.0, 12.0),
        max_italic=14.0,
        fail_italic=18.0,
        allow_bullet_bold_label=True,
        penalize_bold_stacking=True,
        max_paragraph_words=125,
        min_paragraph_words=15,
        max_list_items=9,
        max_heading_chars=65,
        max_heading_words=8,
    ),
    "notes": LinterProfile(
        name="notes",
        title="Lecture Syllabus / Cheat Sheet",
        description="High information density, bulleted layout, and instructor instructions",
        target_bold=(8.0, 14.0),
        max_bold=16.0,
        fail_bold=22.0,
        target_italic=(5.0, 15.0),
        max_italic=16.0,
        fail_italic=22.0,
        allow_bullet_bold_label=True,
        penalize_bold_stacking=False,
        max_paragraph_words=90,
        min_paragraph_words=0,
        max_list_items=14,
        max_heading_chars=75,
        max_heading_words=10,
    ),
    "slides": LinterProfile(
        name="slides",
        title="Presentation Slides (Slidev / Marp)",
        description="High visual contrast, prohibited long paragraphs, max 5 bullets per slide",
        target_bold=(10.0, 18.0),
        max_bold=20.0,
        fail_bold=28.0,
        target_italic=(2.0, 10.0),
        max_italic=12.0,
        fail_italic=18.0,
        allow_bullet_bold_label=True,
        penalize_bold_stacking=False,
        max_paragraph_words=40,
        min_paragraph_words=0,
        max_list_items=5,
        max_heading_chars=45,
        max_heading_words=6,
        max_h1_count=999,
        max_heading_depth=4,
    ),
}
