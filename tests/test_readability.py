"""Unit tests for readability scoring and audience-level assessment."""
import pytest

from helper_lib.readability import (
    LEVEL_TARGETS,
    assess_level,
    composite_grade,
    format_grade_target,
    score_readability,
)
from helper_lib.schemas import ExplanationLevel, ReadabilityScores

SIMPLE_TEXT = (
    "High blood pressure happens when blood pushes too hard on artery walls. "
    "Over time, this extra force can harm your heart and kidneys. "
    "Most people do not feel sick at first, so regular checks matter. "
    "Simple daily habits and safe medicine can help keep your numbers down."
)

ADVANCED_TEXT = (
    "Essential hypertension is a chronic cardiovascular condition characterized by "
    "persistently elevated pressure within the systemic arterial vessels over time. "
    "Primary mechanisms include endothelial dysfunction, increased sympathetic nervous "
    "activity, and impaired renal sodium regulation across multiple organ systems. "
    "Without adequate intervention, sustained hemodynamic overload promotes ventricular "
    "hypertrophy and elevates the long-term risk of stroke or kidney failure. "
    "Clinical management combines structured behavioral modification with individualized "
    "pharmacologic therapy guided by each patient's overall cardiovascular risk."
)


def test_score_readability_empty_text():
    scores = score_readability("   ")
    assert scores.flesch_kincaid_grade is None
    assert scores.smog_grade is None
    assert scores.word_count == 0
    assert scores.sentence_count == 0
    assert scores.notes


def test_score_readability_too_short_for_fk_and_smog():
    scores = score_readability("Drink water.")
    assert scores.flesch_kincaid_grade is None
    assert scores.smog_grade is None
    assert scores.word_count == 2
    assert any("Flesch-Kincaid" in note for note in scores.notes)
    assert any("SMOG" in note for note in scores.notes)


def test_score_readability_under_three_sentences_skips_smog():
    text = (
        "High blood pressure makes the heart work harder over time. "
        "Regular checkups help catch it early."
    )
    scores = score_readability(text)
    assert scores.flesch_kincaid_grade is not None
    assert scores.smog_grade is None
    assert scores.sentence_count == 2
    assert any("SMOG requires at least 3 sentences" in note for note in scores.notes)


def test_score_readability_computes_both_metrics_and_notes_short_smog_sample():
    scores = score_readability(SIMPLE_TEXT)
    assert scores.flesch_kincaid_grade is not None
    assert scores.smog_grade is not None
    assert scores.word_count >= 40
    assert scores.sentence_count == 4
    assert any("30+" in note for note in scores.notes)


def test_composite_grade_combinations():
    both = ReadabilityScores(
        flesch_kincaid_grade=6.0, smog_grade=8.0, word_count=40, sentence_count=4
    )
    fk_only = ReadabilityScores(
        flesch_kincaid_grade=7.2, smog_grade=None, word_count=15, sentence_count=2
    )
    smog_only = ReadabilityScores(
        flesch_kincaid_grade=None, smog_grade=8.0, word_count=40, sentence_count=4
    )
    neither = ReadabilityScores(
        flesch_kincaid_grade=None, smog_grade=None, word_count=2, sentence_count=1
    )

    # Target decisions use Flesch-Kincaid only, so SMOG never changes the grade.
    assert composite_grade(both) == 6.0
    assert composite_grade(fk_only) == 7.2
    assert composite_grade(smog_only) is None
    assert composite_grade(neither) is None


def test_assess_level_unassessable_when_scores_missing():
    empty_scores = score_readability("")
    assessment = assess_level("", ExplanationLevel.SIMPLE, empty_scores)
    assert assessment.meets_target is None
    assert assessment.reasons


def test_assess_level_simple_text_passes_simple_and_fails_advanced():
    scores = score_readability(SIMPLE_TEXT)

    simple_check = assess_level(SIMPLE_TEXT, ExplanationLevel.SIMPLE, scores)
    assert simple_check.meets_target is True

    advanced_check = assess_level(SIMPLE_TEXT, ExplanationLevel.ADVANCED, scores)
    assert advanced_check.meets_target is False
    assert any("Grade too low" in reason for reason in advanced_check.reasons)


def test_assess_level_advanced_text_passes_advanced_and_fails_simple():
    scores = score_readability(ADVANCED_TEXT)

    advanced_check = assess_level(ADVANCED_TEXT, ExplanationLevel.ADVANCED, scores)
    assert advanced_check.meets_target is True

    simple_check = assess_level(ADVANCED_TEXT, ExplanationLevel.SIMPLE, scores)
    assert simple_check.meets_target is False
    assert any("Grade too high" in reason for reason in simple_check.reasons)


def test_assess_level_accepts_string_level_value():
    scores = score_readability(SIMPLE_TEXT)
    assessment = assess_level(SIMPLE_TEXT, "simple", scores)
    assert assessment.meets_target is True


@pytest.mark.parametrize(
    ("level", "grade", "expected_fragment"),
    [
        (ExplanationLevel.SIMPLE, 10.5, "Grade too high"),
        (ExplanationLevel.STANDARD, 5.0, "Grade too low"),
        (ExplanationLevel.STANDARD, 14.0, "Grade too high"),
        (ExplanationLevel.ADVANCED, 8.0, "Grade too low"),
    ],
)
def test_assess_level_boundary_feedback(level, grade, expected_fragment):
    synthetic_scores = ReadabilityScores(
        flesch_kincaid_grade=grade,
        smog_grade=grade,
        word_count=50,
        sentence_count=4,
    )
    assessment = assess_level(SIMPLE_TEXT, level, synthetic_scores)
    assert assessment.meets_target is False
    assert any(expected_fragment in reason for reason in assessment.reasons)
    assert any(format_grade_target(level) in reason for reason in assessment.reasons)
