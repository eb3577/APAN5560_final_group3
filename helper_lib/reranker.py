"""Peiqi (confirm ownership): rerank retrieved passages before generation."""
from .errors import ComponentNotImplemented
from .schemas import RetrievedPassage

def rerank_passages(question: str, passages: list[RetrievedPassage], top_k: int=3) -> list[RetrievedPassage]:
    # TODO Peiqi: rank question/passage pairs; preserve IDs and fill rerank_score.
    raise ComponentNotImplemented('Peiqi: implement passage reranking.')
