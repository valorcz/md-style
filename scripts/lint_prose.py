#!/usr/bin/env python3
"""
scripts/lint_prose.py - Linter kvality prózy, hustoty formátování a české typografie s podporou profilů.

Profily:
  • article   - Souvislý odborný článek, esej nebo monografie (přísné limity na bold, zákaz odrážkového stylingu)
  • handbook  - Studijní příručka, praktický manuál (povolená bold návěští odrážek, didaktická struktura)
  • notes     - Přednáškový sylabus, lektorské taháky a poznámky (vysoká informační hustota)
  • slides    - Prezentační snímky (žádné dlouhé textové bloky, max. 5 odrážek na slide)

Pravidla:
  [E] Emphasis & Contrast:
      E001 - Bold Overload: Celková hustota tučného písma v dokumentu přesahuje limit profilu
      E002 - Italic Overload: Celková hustota kurzívy v dokumentu přesahuje limit profilu
      E003 - Full Sentence Bold: Ztučněná celá věta o více než 8 slovech
      E004 - Bold Stacking: Zdvojené tučnění v jedné odrážce (tučné návěští + další tučný blok v těle)
      E005 - Stacked Emphasis: Vícenásobné vrstvení (např. ***bold italic***)
  [H] Heading Hygiene:
      H001 - Long Heading: Nadpis delší než limit profilu (znaků)
      H002 - Wordy Heading: Nadpis s více slovy než limit profilu
      H003 - Trailing Punctuation: Tečka nebo dvojtečka na konci nadpisu
      H004 - Headless Section: Nadpis bezprostředně následovaný podnadpisem bez úvodního odstavce
  [R] Structural Rhythm:
      R001 - Staccato Paragraph: Izolovaný odstavec kratší než limit profilu
      R002 - Wall of Text: Souvislý odstavec delší než limit profilu
      R003 - Bullet Hell: Seznam s více odrážkami než limit profilu bez rozdělení
      R004 - Bullet Run-on: Odrážka obsahující více než 3 rozvité věty
  [T] Czech Typography & Style:
      T001 - Capital in Parentheses: Neobvyklé velké písmeno v závorce uvnitř české věty
      T002 - Double Punctuation: Typografická kolize interpunkce (např. '.)', '?!.', ', :')
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class LinterProfile:
    name: str
    title: str
    description: str
    target_bold: Tuple[float, float]
    max_bold: float  # WARN threshold
    fail_bold: float  # FAIL threshold
    target_italic: Tuple[float, float]
    max_italic: float  # WARN threshold
    fail_italic: float  # FAIL threshold
    allow_bullet_bold_label: bool
    penalize_bold_stacking: bool
    max_paragraph_words: int
    min_paragraph_words: int
    max_list_items: int
    max_heading_chars: int
    max_heading_words: int


PROFILES: Dict[str, LinterProfile] = {
    "article": LinterProfile(
        name="article",
        title="Odborný článek / Monografie",
        description="Souvislý text zaměřený na plynulé čtení zleva doprava bez vizuálního šumu",
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
        title="Studijní příručka / Praktický manuál",
        description="Duální formát pro studium i rychlou orientaci; povoluje tučná návěští odrážek",
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
        title="Přednáškový sylabus / Taháky",
        description="Vysoká informační hustota, heslovitá struktura a lektorské instrukce",
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
        title="Prezentační snímky (Slidev / Marp)",
        description="Vysoký vizuální kontrast, zákaz dlouhých odstavců, max. 5 odrážek na slide",
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
    ),
}


@dataclass
class Issue:
    code: str
    category: str
    message: str
    line: Optional[int] = None
    snippet: Optional[str] = None
    severity: str = "WARN"  # "INFO", "WARN", "FAIL"
    penalty: float = 2.0


@dataclass
class LintResult:
    file_path: Path
    profile: LinterProfile
    detected_via: str = "default"
    total_words: int = 0
    bold_words: int = 0
    italic_words: int = 0
    bold_density: float = 0.0
    italic_density: float = 0.0
    issues: List[Issue] = field(default_factory=list)
    score: float = 100.0

    @property
    def grade(self) -> Tuple[str, str]:
        if self.score >= 95:
            return "A+", "\033[92m"  # Green
        elif self.score >= 90:
            return "A", "\033[92m"
        elif self.score >= 80:
            return "B", "\033[94m"  # Blue
        elif self.score >= 70:
            return "C", "\033[93m"  # Yellow
        elif self.score >= 60:
            return "D", "\033[33m"
        else:
            return "F", "\033[91m"  # Red


class ProseLinter:
    def __init__(self, profile: Optional[LinterProfile] = None):
        self.default_profile = profile or PROFILES["handbook"]

    def detect_profile(self, text: str, requested_name: Optional[str] = None) -> Tuple[LinterProfile, str]:
        if requested_name:
            if requested_name in PROFILES:
                return PROFILES[requested_name], "CLI argument"
            else:
                print(f"Varování: Neznámý profil '{requested_name}', použije se výchozí 'handbook'.", file=sys.stderr)

        # Hledání ve frontmatteru
        if text.startswith("---"):
            fm_parts = text.split("---", 2)
            if len(fm_parts) >= 3:
                fm = fm_parts[1].lower()
                if "doc_type: article" in fm or "profile: article" in fm:
                    return PROFILES["article"], "frontmatter (doc_type: article)"
                if "doc_type: slides" in fm or "profile: slides" in fm or "slidev" in fm:
                    return PROFILES["slides"], "frontmatter (doc_type: slides)"
                if "doc_type: notes" in fm or "profile: notes" in fm:
                    return PROFILES["notes"], "frontmatter (doc_type: notes)"
                if "doc_type: handbook" in fm or "report_type: \"studijní text\"" in fm or "style: \"academic" in fm:
                    return PROFILES["handbook"], "frontmatter (report_type / academic)"

        return self.default_profile, "výchozí nastavení"

    def lint_file(self, path: Path, requested_profile: Optional[str] = None) -> LintResult:
        if not path.is_file():
            raise FileNotFoundError(f"Soubor {path} nebyl nalezen.")

        raw_text = path.read_text(encoding="utf-8")
        profile, detected_via = self.detect_profile(raw_text, requested_profile)

        result = LintResult(file_path=path, profile=profile, detected_via=detected_via)

        # 1. Odstranit frontmatter, komentáře a bloky kódu
        clean_text = re.sub(r"^---[\s\S]*?---\n", "", raw_text)
        clean_text = re.sub(r"```[\s\S]*?```", "", clean_text)
        clean_text = re.sub(r"<!--[\s\S]*?-->", "", clean_text)

        lines = raw_text.splitlines()

        # Globální počty slov
        words = re.findall(r"\b\w+\b", clean_text)
        result.total_words = len(words) or 1

        bold_matches = re.findall(r"\*\*([^*]+)\*\*", clean_text)
        result.bold_words = sum(len(re.findall(r"\b\w+\b", m)) for m in bold_matches)
        result.bold_density = (result.bold_words / result.total_words) * 100

        italic_matches = re.findall(r"(?<!\*)\*([^*\n]+)\*(?!\*)", clean_text)
        result.italic_words = sum(len(re.findall(r"\b\w+\b", m)) for m in italic_matches)
        result.italic_density = (result.italic_words / result.total_words) * 100

        # Kontrola globálních hustot dle profilu
        if result.bold_density > profile.fail_bold:
            result.issues.append(
                Issue(
                    code="E001",
                    category="Emphasis",
                    message=(
                        f"Kritická hustota tučného písma: {result.bold_density:.1f} % "
                        f"(cíl pro profil '{profile.name}': {profile.target_bold[0]:.0f}–{profile.target_bold[1]:.0f} %, strop: {profile.max_bold:.0f} %)"
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
                        f"Zvýšená hustota tučného písma: {result.bold_density:.1f} % "
                        f"(cíl pro profil '{profile.name}': {profile.target_bold[0]:.0f}–{profile.target_bold[1]:.0f} %)"
                    ),
                    severity="WARN",
                    penalty=8.0,
                )
            )

        if result.italic_density > profile.fail_italic:
            result.issues.append(
                Issue(
                    code="E002",
                    category="Emphasis",
                    message=(
                        f"Kritická hustota kurzívy: {result.italic_density:.1f} % "
                        f"(cíl pro profil '{profile.name}': {profile.target_italic[0]:.0f}–{profile.target_italic[1]:.0f} %, strop: {profile.max_italic:.0f} %)"
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
                        f"Zvýšená hustota kurzívy: {result.italic_density:.1f} % "
                        f"(cíl pro profil '{profile.name}': {profile.target_italic[0]:.0f}–{profile.target_italic[1]:.0f} %)"
                    ),
                    severity="WARN",
                    penalty=5.0,
                )
            )

        # Kontrola po řádcích a blocích
        self._check_headings_and_structure(lines, result, profile)
        self._check_line_rules(lines, result, profile)

        # Výpočet skóre (100 - suma penalt, min 0)
        total_penalties = sum(issue.penalty for issue in result.issues)
        result.score = max(0.0, min(100.0, 100.0 - total_penalties))

        return result

    def _check_headings_and_structure(self, lines: List[str], result: LintResult, profile: LinterProfile):
        in_code = False
        in_frontmatter = False
        frontmatter_count = 0

        current_list_count = 0
        list_start_line = 0

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

            # Kontrola délky seznamů (R003: Bullet Hell) - pouze pro položky nejvyšší úrovně
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
                                f"Dlouhý nepřerušený seznam ({current_list_count} položek > limit {profile.max_list_items}) "
                                f"bez mezititulku či rozdělení"
                            ),
                            line=list_start_line,
                            severity="WARN",
                            penalty=3.0,
                        )
                    )
                current_list_count = 0

            # Kontrola nadpisů
            if line_str.startswith("#"):
                h_level = len(line_str) - len(line_str.lstrip("#"))
                h_text = line_str.lstrip("#").strip()

                # H001: Délka znaků
                if len(h_text) > profile.max_heading_chars:
                    result.issues.append(
                        Issue(
                            code="H001",
                            category="Heading",
                            message=f"Příliš dlouhý nadpis ({len(h_text)} znaků > limit {profile.max_heading_chars}): '{h_text[:45]}...'",
                            line=i + 1,
                            snippet=h_text,
                            severity="WARN",
                            penalty=2.0,
                        )
                    )

                # H002: Počet slov
                h_words = len(h_text.split())
                if h_words > profile.max_heading_words:
                    result.issues.append(
                        Issue(
                            code="H002",
                            category="Heading",
                            message=f"Mnoho slov v nadpisu ({h_words} slov > limit {profile.max_heading_words}): '{h_text[:45]}...'",
                            line=i + 1,
                            snippet=h_text,
                            severity="WARN",
                            penalty=2.0,
                        )
                    )

                # H003: Interpunkce na konci nadpisu
                if h_text.endswith((".", ":", ";")):
                    result.issues.append(
                        Issue(
                            code="H003",
                            category="Heading",
                            message=f"Nadpis končí interpunkcí ('{h_text[-1]}'): '{h_text}'",
                            line=i + 1,
                            snippet=h_text,
                            severity="WARN",
                            penalty=1.5,
                        )
                    )

                # H004: Headless sekce
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
                                message=f"Sekce bez úvodního odstavce: Nadpis #{h_level} je ihned následován dalším nadpisem",
                                line=i + 1,
                                snippet=h_text,
                                severity="WARN",
                                penalty=3.0,
                            )
                        )
                    break

    def _check_line_rules(self, lines: List[str], result: LintResult, profile: LinterProfile):
        in_details = False
        in_table = False

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

            # R002: Wall of Text v odstavci
            if not line_str.startswith(("#", "*", "-", ">", "<", "|", "1.", "2.", "3.", "4.", "5.")):
                p_words = len(re.findall(r"\b\w+\b", line_str))
                if p_words > profile.max_paragraph_words:
                    result.issues.append(
                        Issue(
                            code="R002",
                            category="Structure",
                            message=f"Příliš dlouhý monolitický odstavec ({p_words} slov > limit {profile.max_paragraph_words})",
                            line=idx,
                            snippet=line_str[:50] + "...",
                            severity="WARN",
                            penalty=2.0,
                        )
                    )

            # E004: Zdvojené tučnění v odrážce (Bold Stacking)
            if re.match(r"^(\*|-|\d+\.)\s+\*\*", line_str):
                bolds = re.findall(r"\*\*([^*]+)\*\*", line_str)
                if len(bolds) > 1:
                    if profile.penalize_bold_stacking:
                        result.issues.append(
                            Issue(
                                code="E004",
                                category="Emphasis",
                                message=f"Zdvojené tučnění v jedné odrážce: návěští + další tučný blok '**{bolds[1][:30]}**'",
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
                                message=f"Zdvojené tučnění v odrážce: návěští + '**{bolds[1][:30]}**'",
                                line=idx,
                                snippet=line_str[:60],
                                severity="INFO",
                                penalty=0.0,
                            )
                        )

            # E003: Celá věta tučně
            full_bolds = re.findall(r"(?:^|[.!?]\s+)\*\*([^*]+)\*\*[.!?]", line_str)
            for fb in full_bolds:
                fb_words = len(re.findall(r"\b\w+\b", fb))
                if fb_words > 8:
                    result.issues.append(
                        Issue(
                            code="E003",
                            category="Emphasis",
                            message=f"Celá rozvitá věta je ztučněna ({fb_words} slov): '**{fb[:35]}...**'",
                            line=idx,
                            snippet=fb[:50],
                            severity="WARN",
                            penalty=2.0,
                        )
                    )

            # E005: Trojité zvýraznění (***text***)
            if "***" in line_str:
                result.issues.append(
                    Issue(
                        code="E005",
                        category="Emphasis",
                        message="Vrstvené zvýraznění (tučná kurzíva ***text***)",
                        line=idx,
                        snippet=line_str[:50],
                        severity="INFO",
                        penalty=1.0,
                    )
                )

            # R004: Odrážka s příliš mnoha větami (Run-on bullet)
            if re.match(r"^(\*|-)\s+", line_str):
                sentences = re.split(r"[.!?]\s+[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ]", line_str)
                if len(sentences) > 3 and len(line_str) > 250:
                    result.issues.append(
                        Issue(
                            code="R004",
                            category="Structure",
                            message=f"Odrážka je příliš rozvláčná ({len(sentences)} vět, {len(line_str)} znaků); zvažte převod na odstavec",
                            line=idx,
                            snippet=line_str[:50] + "...",
                            severity="INFO",
                            penalty=1.5,
                        )
                    )

            # T001: Podezřelé velké písmeno v závorce uvnitř české věty
            paren_matches = re.finditer(r"(?<!^)\(([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]{2,}[^)]*)\)", line_str)
            for pm in paren_matches:
                content = pm.group(1).strip()
                if re.search(r"\b(19\d\d|20\d\d)\b", content):
                    continue
                parts = [p.strip() for p in content.split(",")]
                if len(parts) > 1 and all(p and p[0].isupper() for p in parts if p):
                    continue
                allowed_terms = {
                    "Title", "Google", "Linux", "Slack", "Teams", "Python", "Rust", "CycloneDX",
                    "Locked", "Cloud", "Applicant", "Software", "Digital", "Cyber", "High-Risk",
                    "Proof", "Direct", "Restricted", "The", "Accidental", "Essential", "Remote",
                    "Prompt", "Insecure", "Training", "S-křivka", "Onboarding", "Růst", "Barcamp",
                    "Governance", "Secure", "Cursor", "GitHub", "Pay", "Blue", "Red", "AppSec"
                }
                first_word = content.split()[0].rstrip(",;:")
                if first_word not in allowed_terms and not content.isupper():
                    result.issues.append(
                        Issue(
                            code="T001",
                            category="Typography",
                            message=f"Podezřelé velké počáteční písmeno v závorce: '({content[:30]})'",
                            line=idx,
                            snippet=pm.group(0),
                            severity="WARN",
                            penalty=1.0,
                        )
                    )

            # T002: Dvojitá interpunkce
            if re.search(r"(\.\)|\?\!\.|\,\s*\:|\.\s*\.)", line_str):
                result.issues.append(
                    Issue(
                        code="T002",
                        category="Typography",
                        message="Typografická kolize interpunkce (např. '.)' nebo dvojitá tečka)",
                        line=idx,
                        snippet=line_str[:50],
                        severity="INFO",
                        penalty=0.5,
                    )
                )


def format_report(result: LintResult, verbose: bool = False) -> str:
    reset = "\033[0m"
    bold = "\033[1m"
    cyan = "\033[96m"
    dim = "\033[2m"

    p = result.profile
    grade, grade_color = result.grade

    lines = []
    lines.append(f"{bold}=== Prose & Typography Linter ==={reset}")
    lines.append(f"Soubor: {cyan}{result.file_path}{reset}")
    lines.append(f"Profil: \033[1;35m{p.name}\033[0m ({p.title}) [{dim}detekováno přes: {result.detected_via}{reset}]")
    lines.append(f"{dim}Popis profilu: {p.description}{reset}\n")

    lines.append(f"{bold}📊 Globální metriky a rozsah:{reset}")
    lines.append(f"   • Celkový rozsah:         {result.total_words:,} slov")

    b_color = (
        "\033[91m"
        if result.bold_density > p.fail_bold
        else "\033[93m"
        if result.bold_density > p.max_bold
        else "\033[92m"
    )
    lines.append(
        f"   • Tučný text (**bold**):   {result.bold_words:,} slov ({b_color}{result.bold_density:.1f} %{reset}) "
        f"[cíl: {p.target_bold[0]:.0f}–{p.target_bold[1]:.0f} %, max: {p.max_bold:.0f} %]"
    )

    i_color = (
        "\033[91m"
        if result.italic_density > p.fail_italic
        else "\033[93m"
        if result.italic_density > p.max_italic
        else "\033[92m"
    )
    lines.append(
        f"   • Kurzíva (*italic*):     {result.italic_words:,} slov ({i_color}{result.italic_density:.1f} %{reset}) "
        f"[cíl: {p.target_italic[0]:.0f}–{p.target_italic[1]:.0f} %, max: {p.max_italic:.0f} %]"
    )

    lines.append(
        f"   • Celkové zvýraznění:     {result.bold_words + result.italic_words:,} slov "
        f"({(result.bold_words + result.italic_words) / result.total_words * 100:.1f} %)"
    )
    lines.append(f"   • Výsledné skóre:         {grade_color}{bold}{result.score:.1f} / 100  (Stupeň {grade}){reset}\n")

    if not result.issues:
        lines.append(f"\033[92m✓ Dokument plně vyhovuje pravidlům profilu '{p.name}'.{reset}")
        return "\n".join(lines)

    lines.append(f"{bold}🔍 Nalezené podněty ke zlepšení ({len(result.issues)}):{reset}")

    warns = [i for i in result.issues if i.severity in ("FAIL", "WARN")]
    infos = [i for i in result.issues if i.severity == "INFO"]

    for issue in (warns + (infos if verbose else [])):
        loc = f"L{issue.line:4d} " if issue.line else "GLOBAL "
        sev_badge = (
            "\033[91mFAIL\033[0m"
            if issue.severity == "FAIL"
            else "\033[93mWARN\033[0m"
            if issue.severity == "WARN"
            else "\033[94mINFO\033[0m"
        )
        lines.append(f"   {dim}{loc}{reset}[{sev_badge}] \033[1m[{issue.code}]\033[0m {issue.message}")
        if issue.snippet and verbose:
            lines.append(f"          {dim}↳ {issue.snippet}{reset}")

    if not verbose and infos:
        lines.append(f"\n   {dim}... a {len(infos)} drobných doporučení (zobrazíte volbou --verbose / -v).{reset}")

    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Linter kvality prózy, hustoty formátování a typografie s podporou profilů."
    )
    parser.add_argument(
        "file",
        nargs="?",
        default="pruvodce-karierou-fi-muni-2026.md",
        help="Cesta k Markdown souboru k analýze (výchozí: pruvodce-karierou-fi-muni-2026.md)",
    )
    parser.add_argument(
        "-p", "--profile",
        choices=list(PROFILES.keys()),
        help=f"Profil dokumentu: {', '.join(PROFILES.keys())} (pokud není zadán, detekuje se z frontmatteru)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Zobrazit detailní náhledy řádků a méně závažná doporučení (INFO)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Ukončit s nenulovým kódem (exit 1), pokud je skóre < 80 nebo existují chyby FAIL",
    )

    args = parser.parse_args()
    target_path = Path(args.file)

    linter = ProseLinter()
    try:
        res = linter.lint_file(target_path, requested_profile=args.profile)
    except FileNotFoundError as err:
        print(f"Chyba: {err}", file=sys.stderr)
        sys.exit(1)

    print(format_report(res, verbose=args.verbose))

    if args.strict and (res.score < 80.0 or any(i.severity == "FAIL" for i in res.issues)):
        sys.exit(1)


if __name__ == "__main__":
    main()
