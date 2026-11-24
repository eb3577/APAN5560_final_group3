"""Connect the API to retrieval and level-specific explanation generation."""
from config import RETRIEVE_TOP_K
from helper_lib.errors import ComponentNotImplemented, ResourceUnavailable
from helper_lib.generator import generate_explanation
from helper_lib.retrieval import retrieve_passages
from helper_lib.reranker import rerank_passages
from helper_lib.schemas import (
    AnswerDraft, CitedSource, ExplainRequest, ExplainResponse, PipelineMode,
)


def explain(request: ExplainRequest) -> ExplainResponse:
    if request.mode == PipelineMode.IMPROVED:
        # Connect the readability/revision helper when that component is ready.
        raise ComponentNotImplemented(
            "Readability revision is not implemented yet. Use mode 'baseline'.")
    try:
        hits = retrieve_passages(request.question, RETRIEVE_TOP_K if request.rerank else 1)
        if request.rerank and hits:
            hits = rerank_passages(request.question, hits, 1)
        draft = generate_explanation(request.question, request.level, hits)
    except (OSError, ImportError) as exc:
        raise ResourceUnavailable(
            "Required data, index, model, or dependency is unavailable. "
            "Check the server setup.") from exc
    if not draft.text:
        return ExplainResponse(
            answer=AnswerDraft(text="The available sources do not provide enough information "
                             "to answer this question."),
            sources=[], level=request.level, mode=request.mode,
            status="insufficient_sources", stop_reason="insufficient_evidence",
        )
    sources = [
        CitedSource(**hit.passage.model_dump(), label=f"S{i}")
        for i, hit in enumerate(hits, start=1)
        if hit.passage.chunk_id in draft.cited_chunk_ids
    ]
    return ExplainResponse(
        answer=draft, sources=sources, level=request.level, mode=request.mode,
        status="answered", stop_reason="baseline_complete",
    )
