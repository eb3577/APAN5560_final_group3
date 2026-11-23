"""Peiqi: encode questions to match the existing BGE-small 384D passage vectors."""
from .errors import ComponentNotImplemented

def embed_query(question: str) -> list[float]:
    # TODO Peiqi: load the compatible encoder; match normalization and query instructions.
    raise ComponentNotImplemented('Peiqi: implement compatible query embeddings.')
