"""Check prompt selection and source mapping without downloading a model."""

import pytest
from helper_lib import generator
from helper_lib.schemas import Passage, RetrievedPassage


@pytest.fixture
def passages():
    return [RetrievedPassage(passage=Passage(
        chunk_id=f"chunk-{i}", topic_id=f"topic-{i}", title=f"Example {i}",
        text=f"Source text {i}.", source_url=f"https://example.org/{i}",
    ), retrieval_score=0.9) for i in (1, 2)]


@pytest.mark.parametrize("level,phrase", [
    ("simple", "no medical background"),
    ("standard", "moderate detail"),
    ("advanced", "medically knowledgeable"),
])
def test_prompt_and_citation_mapping(monkeypatch, passages, level, phrase):
    def generate(prompt):
        assert phrase in prompt
        assert "Example question?" in prompt
        assert "[S1] Example 1\nSource text 1." in prompt
        assert "[S2] Example 2\nSource text 2." in prompt
        return "Second source [S2]. First source [S1]. Again [S2]."
    monkeypatch.setattr(generator, "generate_text", generate)
    result = generator.generate_explanation("Example question?", level, passages)
    assert result.cited_chunk_ids == ["chunk-2", "chunk-1"]


@pytest.mark.parametrize("output", ["", "INSUFFICIENT_EVIDENCE", "INSUFFICIENT_EVIDENCE."])
def test_insufficient_evidence(monkeypatch, passages, output):
    monkeypatch.setattr(generator, "generate_text", lambda prompt: output)
    result = generator.generate_explanation("Example?", "simple", passages)
    assert result.text == ""
    assert result.cited_chunk_ids == []


@pytest.mark.parametrize("output", ["Uncited answer.", "Unknown [S3].", "Malformed [S1, S2]."])
def test_invalid_citations(monkeypatch, passages, output):
    monkeypatch.setattr(generator, "generate_text", lambda prompt: output)
    with pytest.raises(ValueError):
        generator.generate_explanation("Example?", "simple", passages)


def test_no_passages_skips_model(monkeypatch):
    def unexpected(prompt):
        pytest.fail("Model should not run without sources")
    monkeypatch.setattr(generator, "generate_text", unexpected)
    assert generator.generate_explanation("Example?", "simple", []).text == ""


def test_single_source_reference_added(monkeypatch, passages):
    monkeypatch.setattr(generator, "generate_text", lambda prompt: "Example answer.")
    result = generator.generate_explanation("Example?", "simple", passages[:1])
    assert result.text == "Example answer.\n\nSource: [S1]"
    assert result.cited_chunk_ids == ["chunk-1"]


def test_existing_single_source_citation_not_duplicated(monkeypatch, passages):
    monkeypatch.setattr(generator, "generate_text", lambda prompt: "Example [S1].")
    result = generator.generate_explanation("Example?", "simple", passages[:1])
    assert result.text == "Example [S1]."


def test_single_source_unknown_label_rejected(monkeypatch, passages):
    monkeypatch.setattr(generator, "generate_text", lambda prompt: "Example [S2].")
    with pytest.raises(ValueError):
        generator.generate_explanation("Example?", "simple", passages[:1])


def test_single_source_insufficient_evidence_has_no_citation(monkeypatch, passages):
    monkeypatch.setattr(generator, "generate_text", lambda prompt: "INSUFFICIENT_EVIDENCE")
    result = generator.generate_explanation("Example?", "simple", passages[:1])
    assert result.text == "" and result.cited_chunk_ids == []
