"""Readability scoring and audience-level assessment."""
from __future__ import annotations

import re

import textstat

from .schemas import ExplanationLevel, LevelAssessment, ReadabilityScores

# Target Flesch-Kincaid grade windows: (min_grade, max_grade); None = no upper cap.
LEVEL_TARGETS: dict[ExplanationLevel, tuple[float, float | None]] = {
    ExplanationLevel.SIMPLE: (4.0, 7.5),      # Plain language
    ExplanationLevel.STANDARD: (8.0, 11.5),   # Informed general adult
    ExplanationLevel.ADVANCED: (12.0, None),  # Clinical terminology (12+)
}


def format_grade_target(level: ExplanationLevel) -> str:
    """Format a level's grade target as 'min-max' or 'min+'."""
    min_grade, max_grade = LEVEL_TARGETS[level]
    if max_grade is None:
        return f"{min_grade:g}+"
    return f"{min_grade:g}-{max_grade:g}"

# Expected Dale-Chall difficult-word ratio per level (calibrated for medical prose)
TERMINOLOGY_TARGETS: dict[ExplanationLevel, tuple[float, float]] = {
    ExplanationLevel.SIMPLE: (0.00, 0.25),
    ExplanationLevel.STANDARD: (0.10, 0.38),
    ExplanationLevel.ADVANCED: (0.20, 1.00),
}

MIN_WORDS_FOR_FK = 5
MIN_SENTENCES_FOR_SMOG = 3

_CITATION_TAG_RE = re.compile(r"(?:\n*\s*Source:\s*|\s*)\[S[^\]]*\]")


def _strip_citations(text: str) -> str:
    """Remove inline [S#] and trailing 'Source: [S1]' markers before scoring prose."""
    return _CITATION_TAG_RE.sub("", text).strip()


def composite_grade(scores: ReadabilityScores) -> float | None:
    """Grade used for target decisions: Flesch-Kincaid only.

    SMOG is still computed and reported, but it is undefined for answers under
    3 sentences, so using it would change the metric between drafts.
    """
    return scores.flesch_kincaid_grade


def score_readability(text: str) -> ReadabilityScores:
    """Calculate FKGL and SMOG; return None plus notes when a metric is not applicable."""
    cleaned = _strip_citations(text)
    if not cleaned:
        return ReadabilityScores(
            flesch_kincaid_grade=None,
            smog_grade=None,
            word_count=0,
            sentence_count=0,
            notes=["Text is empty; readability scores are not applicable."],
        )

    word_count = int(textstat.lexicon_count(cleaned, removepunct=True))
    sentence_count = int(textstat.sentence_count(cleaned))
    notes: list[str] = []

    if word_count < MIN_WORDS_FOR_FK or sentence_count < 1:
        fk_grade: float | None = None
        notes.append(
            f"Text too short for Flesch-Kincaid ({word_count} words, {sentence_count} sentences)."
        )
    else:
        fk_grade = round(float(textstat.flesch_kincaid_grade(cleaned)), 2)

    if sentence_count < MIN_SENTENCES_FOR_SMOG:
        smog_grade: float | None = None
        notes.append(
            f"SMOG requires at least {MIN_SENTENCES_FOR_SMOG} sentences (found {sentence_count})."
        )
    else:
        smog_grade = round(float(textstat.smog_index(cleaned)), 2)
        if sentence_count < 30:
            notes.append(
                f"SMOG computed on {sentence_count} sentences (traditionally calibrated for 30+)."
            )

    return ReadabilityScores(
        flesch_kincaid_grade=fk_grade,
        smog_grade=smog_grade,
        word_count=word_count,
        sentence_count=sentence_count,
        notes=notes,
    )


def assess_level(
    text: str,
    level: ExplanationLevel,
    scores: ReadabilityScores,
) -> LevelAssessment:
    """Assess readability against agreed grade-level targets and terminology density."""
    try:
        resolved_level = ExplanationLevel(level)
    except ValueError:
        return LevelAssessment(
            meets_target=None,
            reasons=[f"Unknown explanation level '{level}'; not assessable."],
        )

    grade = composite_grade(scores)
    if grade is None or scores.word_count == 0:
        return LevelAssessment(
            meets_target=None,
            reasons=["Readability scores unavailable; level cannot be assessed."],
        )

    min_grade, max_grade = LEVEL_TARGETS[resolved_level]
    grade_ok = grade >= min_grade and (max_grade is None or grade <= max_grade)
    target_label = format_grade_target(resolved_level)

    cleaned = _strip_citations(text)
    difficult_ratio = round(textstat.difficult_words(cleaned) / scores.word_count, 3)
    min_term, max_term = TERMINOLOGY_TARGETS[resolved_level]
    terminology_ok = min_term <= difficult_ratio <= max_term

    meets_target = grade_ok and terminology_ok
    reasons: list[str] = []

    if max_grade is not None and grade > max_grade:
        reasons.append(
            f"Grade too high ({grade} vs target {target_label}; "
            f"FK={scores.flesch_kincaid_grade}, SMOG={scores.smog_grade}): "
            "shorten sentences and simplify phrasing."
        )
    elif grade < min_grade:
        reasons.append(
            f"Grade too low ({grade} vs target {target_label}; "
            f"FK={scores.flesch_kincaid_grade}, SMOG={scores.smog_grade}): "
            "add fuller explanation and more structured detail."
        )

    if difficult_ratio > max_term:
        reasons.append(
            f"Terminology too dense ({difficult_ratio:.1%} difficult words vs max {max_term:.0%}): "
            "replace or define medical jargon in plain words."
        )
    elif difficult_ratio < min_term:
        reasons.append(
            f"Terminology too basic ({difficult_ratio:.1%} difficult words vs min {min_term:.0%}): "
            "retain appropriate clinical terminology from the sources."
        )

    if not reasons:
        reasons.append(
            f"Meets '{resolved_level.value}' target "
            f"(grade {grade}, difficult words {difficult_ratio:.1%})."
        )

    return LevelAssessment(meets_target=meets_target, reasons=reasons)
