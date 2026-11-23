"""Shared inputs/outputs. Coordinate field changes; adapt source data in the loader."""
from enum import Enum
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExplanationLevel(str, Enum):
    SIMPLE = "simple"
    STANDARD = "standard"
    ADVANCED = "advanced"


class PipelineMode(str, Enum):
    BASELINE = "baseline"
    IMPROVED = "improved"


class Passage(Contract):
    chunk_id: str
    topic_id: str
    title: str
    text: str
    source_url: HttpUrl


class RetrievedPassage(Contract):
    passage: Passage
    retrieval_score: float
    rerank_score: float | None = None


class AnswerDraft(Contract):
    text: str
    cited_chunk_ids: list[str] = Field(default_factory=list)


class ReadabilityScores(Contract):
    flesch_kincaid_grade: float | None = None
    smog_grade: float | None = None
    word_count: int = Field(ge=0)
    sentence_count: int = Field(ge=0)
    notes: list[str] = Field(default_factory=list)


class LevelAssessment(Contract):
    meets_target: bool | None = None
    reasons: list[str] = Field(default_factory=list)


class RevisionResult(Contract):
    answer: AnswerDraft
    initial_scores: ReadabilityScores
    final_scores: ReadabilityScores
    assessment: LevelAssessment
    attempts: int = Field(ge=0)
    stop_reason: str


class ExplainRequest(Contract):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    question: str = Field(min_length=1, max_length=2000)
    level: ExplanationLevel = ExplanationLevel.STANDARD
    mode: PipelineMode = PipelineMode.IMPROVED


class ExplainResponse(Contract):
    answer: AnswerDraft
    sources: list[Passage]
    level: ExplanationLevel
    mode: PipelineMode
    status: Literal["answered", "insufficient_sources", "out_of_scope"]
    initial_readability: ReadabilityScores | None = None
    final_readability: ReadabilityScores | None = None
    target_met: bool | None = None
    revision_attempts: int = Field(default=0, ge=0)
    stop_reason: str
