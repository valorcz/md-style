"""
core/lint/readability.py
Deterministic bilingual (English & Czech/Slovak) readability and text complexity engine.
Pure-Python, zero external dependencies.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class ReadabilityMetrics:
    lang: str
    total_words: int
    total_sentences: int
    total_syllables: int
    total_characters: int
    avg_sentence_words: float
    avg_word_syllables: float
    avg_word_characters: float
    complex_words: int
    complex_word_ratio: float
    # English formulas
    flesch_reading_ease: Optional[float] = None
    flesch_kincaid_grade: Optional[float] = None
    automated_readability_index: Optional[float] = None
    # Czech / Slavic formulas
    mistrik_index: Optional[float] = None
    czech_flesch_index: Optional[float] = None
    interpretation: str = ""
    target_recommendation: str = ""


# Non-closing abbreviations that never terminate a sentence
NEVER_CLOSING_ABBREVIATIONS = {
    "e.g.", "i.e.", "např.", "tj.", "tzn.", "tzv."
}

# Common abbreviations that do NOT end a sentence when followed by lower case or continuing words
EN_ABBREVIATIONS = {
    "etc.", "vs.", "al.", "fig.", "vol.", "no.", "inc.", "ltd."
}
EN_TITLES = {
    "dr.", "prof.", "mr.", "mrs.", "ms."
}

CZ_ABBREVIATIONS = {
    "popř.", "atd.", "apod.", "resp.", "č.", "odst.", "písm.", "sb.", "zn.", "sv.", "kol.", "hod."
}
CZ_TITLES = {
    "ing.", "mgr.", "bc.", "mudr.", "judr.", "rndr.", "phdr.", "prof.", "doc.", "dr.", "ph.d.", "csc."
}

# Czech vowels (phonemes that always form a syllable peak)
CZ_VOWELS = set("aeiouyáéíóúůýě")
CZ_DIPHTHONGS = ("ou", "au", "eu")
CZ_CONSONANTS = set("bcčdďfghjklmnňprřsštťvzžcdz")


def count_syllables_czech(word: str) -> int:
    """
    Deterministic phonetic syllable counter for Czech and Slovak words.
    Counts vowel nuclei and syllabic liquids ('r', 'l' between consonants, and terminal 'm' in sedm/osm).
    """
    clean = re.sub(r"[^\w]", "", word.lower())
    if not clean:
        return 0

    n = len(clean)
    syllables = 0
    i = 0

    while i < n:
        # Check diphthong (ou, au, eu count as 1 nucleus)
        if i + 1 < n and clean[i:i+2] in CZ_DIPHTHONGS:
            syllables += 1
            i += 2
            continue

        char = clean[i]
        if char in CZ_VOWELS:
            syllables += 1
            i += 1
            continue

        # Check syllabic consonant:
        # Primarily 'r' and 'l' when surrounded by consonants
        # 'm' is syllabic only at the end of word after consonant (sedm, osm)
        is_syllabic_liquid = char in ("r", "l")
        is_terminal_m = (char == "m" and i + 1 == n and i > 0 and clean[i-1] in CZ_CONSONANTS)

        if is_syllabic_liquid or is_terminal_m:
            prev_is_cons = (i == 0) or (clean[i-1] in CZ_CONSONANTS)
            next_is_cons = (i + 1 == n) or (clean[i+1] in CZ_CONSONANTS)
            prev_not_vowel = (i == 0) or (clean[i-1] not in CZ_VOWELS)
            next_not_vowel = (i + 1 == n) or (clean[i+1] not in CZ_VOWELS)

            if prev_is_cons and next_is_cons and prev_not_vowel and next_not_vowel:
                syllables += 1

        i += 1

    return max(1, syllables)


def count_syllables_english(word: str) -> int:
    """
    Deterministic rule-based algorithmic syllable counter for English words.
    """
    clean = re.sub(r"[^a-zA-Z]", "", word.lower())
    if not clean:
        return 0
    if len(clean) <= 3:
        return 1

    # 1. Count vowel sequences
    vowel_groups = re.findall(r"[aeiouy]+", clean)
    count = len(vowel_groups)

    # 2. Subtract silent terminal 'e' (e.g. 'make', 'game', 'strike')
    if clean.endswith("e") and not clean.endswith(("le", "ee")):
        if count > 1:
            count -= 1

    # 3. Handle suffix adjustments
    # '-ed' where 'e' is typically unvoiced (e.g. 'walked', 'looked', but not 'needed', 'wanted')
    if clean.endswith("ed") and not clean.endswith(("ded", "ted")):
        if count > 1:
            count -= 1

    # '-es' where 'e' is unvoiced (e.g. 'games', but not 'boxes', 'dishes')
    if clean.endswith("es") and not clean.endswith(("ses", "xes", "zes", "ches", "shes")):
        if count > 1:
            count -= 1

    return max(1, count)


def split_sentences(text: str, lang: str = "en") -> List[str]:
    """Splits text into sentences, respecting abbreviations and legal statutes."""
    # Normalize clean lines
    text_clean = re.sub(r"^---[\s\S]*?---\n", "", text)
    text_clean = re.sub(r"```[\s\S]*?```", "", text_clean)
    text_clean = re.sub(r"<!--[\s\S]*?-->", "", text_clean)
    text_clean = re.sub(r"^#+.*$", "", text_clean, flags=re.MULTILINE)

    is_cz = lang in ("cs", "sk")
    abbrevs = CZ_ABBREVIATIONS if is_cz else EN_ABBREVIATIONS
    titles = CZ_TITLES if is_cz else EN_TITLES

    # Protect abbreviations by replacing periods with non-breaking token
    def protect_abbrev(match):
        token = match.group(0)
        return token.replace(".", "\x00")

    # 1. Protect titles (followed by uppercase names, e.g. Dr. Smith, Ing. Novák)
    title_pattern = r"\b(?i:" + "|".join(re.escape(t) for t in titles) + r")(?=\s+[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ])"
    protected = re.sub(title_pattern, protect_abbrev, text_clean)

    # 2. Protect non-closing abbreviations unconditionally (e.g., e.g., i.e., např., tj.)
    never_closing_pattern = r"\b(?i:" + "|".join(re.escape(a) for a in NEVER_CLOSING_ABBREVIATIONS) + r")"
    protected = re.sub(never_closing_pattern, protect_abbrev, protected)

    # 3. Protect abbreviations (followed by lowercase words, numbers, or commas)
    abbrev_pattern = r"\b(?i:" + "|".join(re.escape(a) for a in abbrevs) + r")(?=\s+[a-záčďéěíňóřšťúůýž0-9,\-])"
    protected = re.sub(abbrev_pattern, protect_abbrev, protected)

    # 3. Protect numeric decimals (e.g. 1.2 or § 1180.1)
    protected = re.sub(r"(\d+)\.(\d+)", lambda m: f"{m.group(1)}\x00{m.group(2)}", protected)

    # Split by standard sentence terminators (. ! ?)
    raw_sentences = re.split(r"[.!?]+(?:\s+|\n+|$)", protected)
    sentences = []
    for s in raw_sentences:
        restored = s.replace("\x00", ".").strip()
        # Only keep substantive sentences with at least 2 words
        words = re.findall(r"\b[a-zA-Zá-žÁ-Ž0-9_-]+\b", restored)
        if len(words) >= 2:
            sentences.append(restored)

    return sentences or [text_clean.strip()]


def calculate_readability(text: str, lang: str = "en") -> ReadabilityMetrics:
    """Calculates deterministic readability metrics tailored for English or Czech/Slovak."""
    is_cz = lang in ("cs", "sk", "czech", "slovak")
    effective_lang = "cs" if is_cz else "en"

    # Clean text of markdown formatting
    clean_text = re.sub(r"^---[\s\S]*?---\n", "", text)
    clean_text = re.sub(r"```[\s\S]*?```", "", clean_text)
    clean_text = re.sub(r"<!--[\s\S]*?-->", "", clean_text)
    clean_text = re.sub(r"[*_`#~\[\]\(\)\<\>]", " ", clean_text)

    # Words
    words = re.findall(r"\b[a-zA-Zá-žÁ-Ž0-9_-]+\b", clean_text)
    total_words = len(words) or 1

    # Sentences
    sentences = split_sentences(text, lang=effective_lang)
    total_sentences = len(sentences) or 1

    # Syllables & Characters
    total_characters = sum(len(w) for w in words)
    syllable_func = count_syllables_czech if is_cz else count_syllables_english

    total_syllables = 0
    complex_words = 0
    monosyllabic_words = 0

    complex_threshold = 4 if is_cz else 3

    for w in words:
        sylls = syllable_func(w)
        total_syllables += sylls
        if sylls == 1:
            monosyllabic_words += 1
        if sylls >= complex_threshold:
            complex_words += 1

    avg_sentence_words = total_words / total_sentences
    avg_word_syllables = total_syllables / total_words
    avg_word_characters = total_characters / total_words
    complex_word_ratio = (complex_words / total_words) * 100

    metrics = ReadabilityMetrics(
        lang=effective_lang,
        total_words=total_words,
        total_sentences=total_sentences,
        total_syllables=total_syllables,
        total_characters=total_characters,
        avg_sentence_words=avg_sentence_words,
        avg_word_syllables=avg_word_syllables,
        avg_word_characters=avg_word_characters,
        complex_words=complex_words,
        complex_word_ratio=complex_word_ratio,
    )

    if effective_lang == "en":
        # 1. Flesch Reading Ease
        fre = 206.835 - (1.015 * avg_sentence_words) - (84.6 * avg_word_syllables)
        metrics.flesch_reading_ease = max(0.0, min(100.0, fre))

        # 2. Flesch-Kincaid Grade Level
        fkgl = (0.39 * avg_sentence_words) + (11.8 * avg_word_syllables) - 15.59
        metrics.flesch_kincaid_grade = max(1.0, fkgl)

        # 3. Automated Readability Index (ARI)
        ari = 4.71 * avg_word_characters + 0.5 * avg_sentence_words - 21.43
        metrics.automated_readability_index = max(1.0, ari)

        # Interpretation
        if fre >= 90:
            metrics.interpretation = "Very Easy (Grade 5)"
        elif fre >= 80:
            metrics.interpretation = "Easy (Grade 6)"
        elif fre >= 70:
            metrics.interpretation = "Fairly Easy (Grade 7)"
        elif fre >= 60:
            metrics.interpretation = "Standard / Plain English (Grade 8–9)"
        elif fre >= 50:
            metrics.interpretation = "Fairly Difficult (High School, Grade 10–12)"
        elif fre >= 30:
            metrics.interpretation = "Difficult (College Level)"
        else:
            metrics.interpretation = "Very Difficult (Academic / Graduate)"

    else:
        # Czech / Slovak: Mistrík Index & Czech Flesch Adaptation
        monosyllable_pct = (monosyllabic_words / total_words) * 100
        # Mistrík formula: R = 50 - (L * P / 10) + S
        mistrik = 50.0 - ((avg_word_syllables * avg_sentence_words) / 10.0) + (monosyllable_pct / 3.0)
        metrics.mistrik_index = max(0.0, min(100.0, mistrik))

        # Czech-Adapted Flesch Index
        cz_flesch = 180.0 - (1.2 * avg_sentence_words) - (58.0 * avg_word_syllables)
        metrics.czech_flesch_index = max(0.0, min(100.0, cz_flesch))

        # Interpretation
        if mistrik >= 70:
            metrics.interpretation = "Velmi snadné čtení (Běžná veřejnost / Populární text)"
        elif mistrik >= 55:
            metrics.interpretation = "Dobrá srozumitelnost (Praktická příručka / Publicistika)"
        elif mistrik >= 40:
            metrics.interpretation = "Střední náročnost (Odborný článek / Monografie)"
        else:
            metrics.interpretation = "Vysoká náročnost (Právní norma / Akademická práce)"

    return metrics
