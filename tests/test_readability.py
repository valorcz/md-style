"""
tests/test_readability.py
Unit tests for deterministic bilingual (English & Czech) readability scoring engine.
"""

import pytest
from core.lint.readability import (
    count_syllables_english,
    count_syllables_czech,
    split_sentences,
    calculate_readability,
)


def test_english_syllable_counting():
    assert count_syllables_english("cat") == 1
    assert count_syllables_english("simple") == 2
    assert count_syllables_english("syllable") == 3
    assert count_syllables_english("readability") == 5
    # Silent terminal e
    assert count_syllables_english("strike") == 1
    assert count_syllables_english("game") == 1
    # Exceptions (-le, -ed)
    assert count_syllables_english("little") == 2
    assert count_syllables_english("walked") == 1
    assert count_syllables_english("needed") == 2


def test_czech_syllable_counting():
    assert count_syllables_czech("pes") == 1
    assert count_syllables_czech("kočka") == 2
    assert count_syllables_czech("stavení") == 3
    assert count_syllables_czech("srozumitelnost") == 5
    # Syllabic consonants without vowels
    assert count_syllables_czech("vlk") == 1
    assert count_syllables_czech("krk") == 1
    assert count_syllables_czech("prst") == 1
    assert count_syllables_czech("čtvrtek") == 2
    assert count_syllables_czech("zmrzlina") == 3


def test_sentence_splitting_with_abbreviations():
    text_cz = "Schůze se koná v 18.00 hod. Přítomen bude např. pan Novák a kol. Další bod je na programu."
    sentences_cz = split_sentences(text_cz, lang="cs")
    assert len(sentences_cz) == 3

    text_en = "This is report no. 14. For instance, e.g. Dr. Smith analyzed sample vol. 2. The case is closed."
    sentences_en = split_sentences(text_en, lang="en")
    assert len(sentences_en) == 3


def test_english_readability_metrics():
    text = """
    The cat sat on the mat. The dog saw the cat and ran away.
    It was a sunny morning in the quiet garden.
    """
    res = calculate_readability(text, lang="en")
    assert res.lang == "en"
    assert res.flesch_reading_ease is not None
    assert res.flesch_reading_ease > 70.0  # Simple text
    assert res.flesch_kincaid_grade is not None
    assert res.flesch_kincaid_grade < 8.0


def test_czech_readability_metrics():
    text = """
    Vlastníci jednotek se sešli na řádném shromáždění. Výbor přednesl zprávu o hospodaření
    za uplynulý kalendářní rok. Všichni přítomní členové návrh rozpočtu schválili.
    """
    res = calculate_readability(text, lang="cs")
    assert res.lang == "cs"
    assert res.mistrik_index is not None
    assert res.czech_flesch_index is not None
    assert res.avg_word_syllables > 1.8  # Typical Czech word length
    assert "srozumitelnost" in res.interpretation.lower() or "snadné" in res.interpretation.lower()
