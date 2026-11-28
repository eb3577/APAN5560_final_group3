"""Connect the API to retrieval and level-specific explanation generation."""
from config import RETRIEVE_TOP_K
from helper_lib.errors import ResourceUnavailable
from helper_lib.generator import generate_explanation
from helper_lib.reranker import rerank_passages
from helper_lib.retrieval import retrieve_passages
from helper_lib.revision import revise_explanation
from helper_lib.schemas import (
    AnswerDraft,
    CitedSource,
    ExplainRequest,
    ExplainResponse,
    PipelineMode,
)


def explain(request: ExplainRequest) -> ExplainResponse:
    try:
        hits = retrieve_passages(request.question, RETRIEVE_TOP_K if request.rerank else 1)
        if request.rerank and hits:
            hits = rerank_passages(request.question, hits, 1)
        draft = generate_explanation(request.question, request.level, hits)
    except (OSError, ImportError) as exc:
        raise ResourceUnavailable(
            "Required data, index, model, or dependency is unavailable. "
            "Check the server setup."
        ) from exc

    if not draft.text:
        return ExplainResponse(
            answer=AnswerDraft(
                text="The available sources do not provide enough information "
                "to answer this question."
            ),
            sources=[],
            level=request.level,
            mode=request.mode,
            status="insufficient_sources",
            stop_reason="insufficient_evidence",
        )

    initial_readability = None
    final_readability = None
    target_met = None
    revision_attempts = 0
    stop_reason = "baseline_complete"

    if request.mode == PipelineMode.IMPROVED:
        try:
            result = revise_explanation(
                question=request.question,
                level=request.level,
                answer=draft,
                passages=hits,
            )
        except (OSError, ImportError) as exc:
            raise ResourceUnavailable(
                "Required data, index, model, or dependency is unavailable. "
                "Check the server setup."
            ) from exc
        draft = result.answer
        initial_readability = result.initial_scores
        final_readability = result.final_scores
        target_met = result.assessment.meets_target
        revision_attempts = result.attempts
        stop_reason = result.stop_reason

    sources = [
        CitedSource(**hit.passage.model_dump(), label=f"S{i}")
        for i, hit in enumerate(hits, start=1)
        if hit.passage.chunk_id in draft.cited_chunk_ids
    ]
    return ExplainResponse(
        answer=draft,
        sources=sources,
        level=request.level,
        mode=request.mode,
        status="answered",
        initial_readability=initial_readability,
        final_readability=final_readability,
        target_met=target_met,
        revision_attempts=revision_attempts,
        stop_reason=stop_reason,
    )