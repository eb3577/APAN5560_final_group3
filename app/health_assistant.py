"""Erik: connect retrieval, generation and readability helpers."""
from helper_lib.errors import ComponentNotImplemented
from helper_lib.schemas import ExplainRequest, ExplainResponse


def explain(request: ExplainRequest) -> ExplainResponse:
    # TODO Erik: retrieve -> rerank -> generate -> score -> revise (improved only).
    # Handle insufficient sources; resolve citations and return ExplainResponse.
    raise ComponentNotImplemented("Explanation pipeline is scaffolded but not implemented.")
