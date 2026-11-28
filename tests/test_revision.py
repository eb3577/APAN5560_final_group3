"""Unit tests for the readability revision feedback loop."""
import pytest

from helper_lib.revision import revise_explanation
from helper_lib.schemas import (
    AnswerDraft,
    ExplanationLevel,
    Passage,
    RetrievedPassage,
)

SIMPLE_CITED = (
    "High blood pressure happens when blood pushes too hard on artery walls [S1]. "
    "Over time, this extra force can harm your heart and kidneys [S1]. "
    "Most people do not feel sick at first, so regular checks matter [S1]. "
    "Simple daily habits and safe medicine can help keep your numbers down [S1]."
)

STANDARD_CITED = (
    "High blood pressure occurs when arterial pressure remains elevated over an "
    "extended period, placing steady strain on blood vessels [S1]. "
    "Because symptoms are uncommon early on, routine clinical screening is essential "
    "for identifying elevated readings before organ injury develops [S1]. "
    "Consistent lifestyle adjustments such as reducing sodium intake and regular "
    "exercise often help lower readings alongside prescribed treatment [S1]. "
    "Patients should discuss target blood pressure goals and medication options "
    "directly with their primary care clinician [S1]."
)

ADVANCED_CITED = (
    "Essential hypertension is a chronic cardiovascular condition characterized by "
    "persistently elevated pressure within the systemic arterial vessels over time [S1]. "
    "Primary mechanisms include endothelial dysfunction, increased sympathetic nervous "
    "activity, and impaired renal sodium regulation across multiple organ systems [S1]. "
    "Without adequate intervention, sustained hemodynamic overload promotes ventricular "
    "hypertrophy and elevates the long-term risk of stroke or kidney failure [S1]. "
    "Clinical management combines structured behavioral modification with individualized "
    "pharmacologic therapy guided by each patient's overall cardiovascular risk [S1]."
)


def _make_passage(chunk_id: str, title: str = "High Blood Pressure") -> RetrievedPassage:
    return RetrievedPassage(
        passage=Passage(
            chunk_id=chunk_id,
            topic_id="htn",
            title=title,
            text="High blood pressure strains arteries and increases heart and kidney risk.",
            source_url="https://medlineplus.gov/highbloodpressure.html",
        ),
        retrieval_score=0.91,
    )


def test_revise_stops_immediately_when_target_met_initially(monkeypatch):
    def fail_if_called(_prompt: str) -> str:
        raise AssertionError("generate_text should not be called when target is already met")

    monkeypatch.setattr("helper_lib.revision.generate_text", fail_if_called)

    draft = AnswerDraft(text=SIMPLE_CITED, cited_chunk_ids=["chunk-1"])
    result = revise_explanation(
        question="What is high blood pressure?",
        level=ExplanationLevel.SIMPLE,
        answer=draft,
        passages=[_make_passage("chunk-1")],
    )

    assert result.attempts == 0
    assert result.stop_reason == "target_met_initially"
    assert result.assessment.meets_target is True
    assert result.answer == draft


def test_revise_returns_not_assessable_for_short_draft(monkeypatch):
    monkeypatch.setattr(
        "helper_lib.revision.generate_text",
        lambda _prompt: (_ for _ in ()).throw(AssertionError("should not call LLM")),
    )

    draft = AnswerDraft(text="Too short.", cited_chunk_ids=["chunk-1"])
    result = revise_explanation(
        question="What is high blood pressure?",
        level=ExplanationLevel.SIMPLE,
        answer=draft,
        passages=[_make_passage("chunk-1")],
    )

    assert result.attempts == 0
    assert result.stop_reason == "not_assessable"
    assert result.assessment.meets_target is None


def test_revise_returns_no_sources_when_passages_empty():
    draft = AnswerDraft(text=ADVANCED_CITED, cited_chunk_ids=["chunk-1"])
    result = revise_explanation(
        question="What is high blood pressure?",
        level=ExplanationLevel.SIMPLE,
        answer=draft,
        passages=[],
    )

    assert result.attempts == 0
    assert result.stop_reason == "no_sources_for_revision"


def test_revise_succeeds_on_first_attempt(monkeypatch):
    captured_prompts: list[str] = []

    def fake_generate(prompt: str) -> str:
        captured_prompts.append(prompt)
        return SIMPLE_CITED

    monkeypatch.setattr("helper_lib.revision.generate_text", fake_generate)

    draft = AnswerDraft(text=ADVANCED_CITED, cited_chunk_ids=["chunk-1"])
    result = revise_explanation(
        question="What is high blood pressure?",
        level=ExplanationLevel.SIMPLE,
        answer=draft,
        passages=[_make_passage("chunk-1")],
        max_attempts=2,
    )

    assert len(captured_prompts) == 1
    assert "Grade too high" in captured_prompts[0]
    assert result.attempts == 1
    assert result.stop_reason == "target_met"
    assert result.assessment.meets_target is True
    assert result.answer.cited_chunk_ids == ["chunk-1"]
    assert result.final_scores.flesch_kincaid_grade < result.initial_scores.flesch_kincaid_grade


def test_revise_rejects_dropped_or_unknown_citations_and_retries(monkeypatch):
    # Two passages so the single-source [S1] fallback does not apply.
    passages = [_make_passage("chunk-1"), _make_passage("chunk-2", title="Blood Pressure Care")]
    prompts_seen: list[str] = []
    responses = iter([
        SIMPLE_CITED.replace("[S1]", "[S99]"),  # Attempt 1: unknown citation
        SIMPLE_CITED,                           # Attempt 2: valid citation
    ])

    def fake_generate(prompt: str) -> str:
        prompts_seen.append(prompt)
        return next(responses)

    monkeypatch.setattr("helper_lib.revision.generate_text", fake_generate)

    draft = AnswerDraft(text=ADVANCED_CITED, cited_chunk_ids=["chunk-1"])
    result = revise_explanation(
        question="What is high blood pressure?",
        level=ExplanationLevel.SIMPLE,
        answer=draft,
        passages=passages,
        max_attempts=2,
    )

    assert result.attempts == 2
    assert result.stop_reason == "target_met"
    assert result.answer.cited_chunk_ids == ["chunk-1"]
    assert "unknown source [S99]" in prompts_seen[1]


def test_revise_applies_single_source_citation_fallback(monkeypatch):
    uncited_simple = SIMPLE_CITED.replace(" [S1]", "")
    monkeypatch.setattr("helper_lib.revision.generate_text", lambda _prompt: uncited_simple)

    draft = AnswerDraft(text=ADVANCED_CITED, cited_chunk_ids=["chunk-1"])
    result = revise_explanation(
        question="What is high blood pressure?",
        level=ExplanationLevel.SIMPLE,
        answer=draft,
        passages=[_make_passage("chunk-1")],
        max_attempts=1,
    )

    assert result.attempts == 1
    assert result.stop_reason == "target_met"
    assert "[S1]" in result.answer.text
    assert result.answer.cited_chunk_ids == ["chunk-1"]


def test_revise_keeps_closest_grounded_draft_when_max_attempts_reached(monkeypatch):
    responses = iter([
        STANDARD_CITED,  # Attempt 1: closer to SIMPLE than ADVANCED_CITED, still above target
        ADVANCED_CITED,  # Attempt 2: regresses back to high grade
    ])
    monkeypatch.setattr("helper_lib.revision.generate_text", lambda _prompt: next(responses))

    draft = AnswerDraft(text=ADVANCED_CITED, cited_chunk_ids=["chunk-1"])
    result = revise_explanation(
        question="What is high blood pressure?",
        level=ExplanationLevel.SIMPLE,
        answer=draft,
        passages=[_make_passage("chunk-1")],
        max_attempts=2,
    )

    assert result.attempts == 2
    assert result.stop_reason == "max_attempts_reached"
    assert result.assessment.meets_target is False
    assert result.answer.text == STANDARD_CITED


def test_revise_falls_back_to_original_if_all_revisions_break_citations(monkeypatch):
    passages = [_make_passage("chunk-1"), _make_passage("chunk-2")]
    monkeypatch.setattr(
        "helper_lib.revision.generate_text",
        lambda _prompt: "Plain answer with no citations at all.",
    )

    draft = AnswerDraft(text=ADVANCED_CITED, cited_chunk_ids=["chunk-1"])
    result = revise_explanation(
        question="What is high blood pressure?",
        level=ExplanationLevel.SIMPLE,
        answer=draft,
        passages=passages,
        max_attempts=2,
    )

    assert result.attempts == 2
    assert result.stop_reason == "max_attempts_reached"
    assert result.answer == draft


def test_revise_rejects_collapsed_revision_and_retries(monkeypatch):
    """A 2-sentence revision with valid citations must not win by shrinking the text."""
    collapsed = "High blood pressure harms the heart [S1]. Check it often [S1]."
    prompts_seen: list[str] = []

    def fake_generate(prompt: str) -> str:
        prompts_seen.append(prompt)
        return collapsed

    monkeypatch.setattr("helper_lib.revision.generate_text", fake_generate)

    draft = AnswerDraft(text=ADVANCED_CITED, cited_chunk_ids=["chunk-1"])
    result = revise_explanation(
        question="What is high blood pressure?",
        level=ExplanationLevel.SIMPLE,
        answer=draft,
        passages=[_make_passage("chunk-1")],
        max_attempts=2,
    )

    assert len(prompts_seen) == 2
    assert "too short" in prompts_seen[1]
    assert result.attempts == 2
    assert result.stop_reason == "max_attempts_reached"
    assert result.answer == draft
