"""Revise explanations for readability while preserving facts and citations."""
from __future__ import annotations
import re
from config import BASE_DIR
from .model import generate_text
from .readability import (
    LEVEL_TARGETS,
    assess_level,
    composite_grade,
    format_grade_target,
    score_readability,
)
from .schemas import (
    AnswerDraft,
    ExplanationLevel,
    LevelAssessment,
    Passage,
    ReadabilityScores,
    RetrievedPassage,
    RevisionResult,
)

CITATION_PATTERN = re.compile(r"\[S([^\[\]]*)\]")

# Reject revisions that "pass" by collapsing into a few short sentences.
MIN_REVISION_SENTENCES = 3
MIN_LENGTH_RATIO = 0.5  # of the original draft's word count; tune after live runs


def _grade_distance(level: ExplanationLevel, scores: ReadabilityScores) -> float:
    """Distance outside the target composite grade window (0.0 if inside)."""
    grade = composite_grade(scores)
    if grade is None:
        return float("inf")
    min_grade, max_grade = LEVEL_TARGETS[level]
    if grade < min_grade:
        return round(min_grade - grade, 4)
    if max_grade is not None and grade > max_grade:
        return round(grade - max_grade, 4)
    return 0.0


def _score_rank(
    level: ExplanationLevel,
    scores: ReadabilityScores,
    assessment: LevelAssessment,
) -> tuple[float, int]:
    """Lower is better: prioritize grade closeness, then fewer unmet reasons."""
    return (_grade_distance(level, scores), len(assessment.reasons))


def _parse_and_validate_revision(
    raw_text: str,
    sources: dict[str, Passage],
) -> tuple[AnswerDraft | None, str | None]:
    """Parse [S#] citations the same way as generator.py and verify grounding."""
    text = raw_text.strip()
    if not text or text.upper().startswith("INSUFFICIENT_EVIDENCE"):
        return None, "Revision returned empty text or INSUFFICIENT_EVIDENCE; keep supported content."

    labels = CITATION_PATTERN.findall(text)
    if not labels and len(sources) == 1:
        text += "\n\nSource: [S1]"
        labels = ["1"]
    if not labels:
        valid_labels = ", ".join(f"[{label}]" for label in sources)
        return None, f"Revision dropped all source citations; retain valid labels ({valid_labels})."

    cited_ids: list[str] = []
    for number in labels:
        label = f"S{number}"
        if label not in sources:
            valid_labels = ", ".join(f"[{key}]" for key in sources)
            return None, f"Revision cited unknown source [{label}]; use only {valid_labels}."
        chunk_id = sources[label].chunk_id
        if chunk_id not in cited_ids:
            cited_ids.append(chunk_id)

    return AnswerDraft(text=text, cited_chunk_ids=cited_ids), None


def _build_revision_prompt(
    question: str,
    level: ExplanationLevel,
    draft: AnswerDraft,
    context: str,
    feedback: list[str],
) -> str:
    template = (BASE_DIR / "prompts" / "revision.txt").read_text(encoding="utf-8")
    feedback_block = "\n".join(f"- {item}" for item in feedback)
    return template.format(
        level=level.value,
        grade_target=f"grade {format_grade_target(level)}",
        question=question.strip(),
        feedback=feedback_block,
        draft=draft.text.strip(),
        context=context,
    )


def revise_explanation(
    question: str,
    level: ExplanationLevel,
    answer: AnswerDraft,
    passages: list[RetrievedPassage],
    max_attempts: int = 2,
) -> RevisionResult:
    """Score, assess, revise, and recheck sources; stop when target is met or at max_attempts."""
    resolved_level = ExplanationLevel(level)
    initial_scores = score_readability(answer.text)
    initial_assessment = assess_level(answer.text, resolved_level, initial_scores)

    if initial_assessment.meets_target is True:
        return RevisionResult(
            answer=answer,
            initial_scores=initial_scores,
            final_scores=initial_scores,
            assessment=initial_assessment,
            attempts=0,
            stop_reason="target_met_initially",
        )

    if initial_assessment.meets_target is None:
        return RevisionResult(
            answer=answer,
            initial_scores=initial_scores,
            final_scores=initial_scores,
            assessment=initial_assessment,
            attempts=0,
            stop_reason="not_assessable",
        )

    if not passages:
        return RevisionResult(
            answer=answer,
            initial_scores=initial_scores,
            final_scores=initial_scores,
            assessment=initial_assessment,
            attempts=0,
            stop_reason="no_sources_for_revision",
        )

    if max_attempts <= 0:
        return RevisionResult(
            answer=answer,
            initial_scores=initial_scores,
            final_scores=initial_scores,
            assessment=initial_assessment,
            attempts=0,
            stop_reason="max_attempts_reached",
        )

    sources = {f"S{i}": hit.passage for i, hit in enumerate(passages, start=1)}
    context = "\n\n".join(
        f"[{label}] {passage.title}\n{passage.text}"
        for label, passage in sources.items()
    )

    best_answer = answer
    best_scores = initial_scores
    best_assessment = initial_assessment
    best_rank = _score_rank(resolved_level, initial_scores, initial_assessment)
    min_sentences = min(MIN_REVISION_SENTENCES, initial_scores.sentence_count)

    current_answer = answer
    feedback = list(initial_assessment.reasons)

    for attempt in range(1, max_attempts + 1):
        prompt = _build_revision_prompt(
            question=question,
            level=resolved_level,
            draft=current_answer,
            context=context,
            feedback=feedback,
        )
        raw_revision = generate_text(prompt)
        candidate, citation_error = _parse_and_validate_revision(raw_revision, sources)

        if candidate is None:
            feedback = list(best_assessment.reasons) + [
                citation_error or "Preserve valid inline source citations."
            ]
            current_answer = best_answer
            continue

        candidate_scores = score_readability(candidate.text)

        if (
            candidate_scores.sentence_count < min_sentences
            or candidate_scores.word_count < MIN_LENGTH_RATIO * initial_scores.word_count
        ):
            feedback = list(best_assessment.reasons) + [
                "Revision was too short and likely dropped supported facts; "
                f"keep at least {min_sentences} sentences and cover the same supported points."
            ]
            current_answer = best_answer
            continue

        candidate_assessment = assess_level(candidate.text, resolved_level, candidate_scores)

        if candidate_assessment.meets_target is True:
            return RevisionResult(
                answer=candidate,
                initial_scores=initial_scores,
                final_scores=candidate_scores,
                assessment=candidate_assessment,
                attempts=attempt,
                stop_reason="target_met",
            )

        candidate_rank = _score_rank(resolved_level, candidate_scores, candidate_assessment)
        if candidate_rank <= best_rank:
            best_answer = candidate
            best_scores = candidate_scores
            best_assessment = candidate_assessment
            best_rank = candidate_rank

        current_answer = candidate
        feedback = list(candidate_assessment.reasons)

    return RevisionResult(
        answer=best_answer,
        initial_scores=initial_scores,
        final_scores=best_scores,
        assessment=best_assessment,
        attempts=max_attempts,
        stop_reason="max_attempts_reached",
    )
