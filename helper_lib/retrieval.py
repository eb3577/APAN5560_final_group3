"""Peiqi: build the index and retrieve source passages."""
from pathlib import Path
from .errors import ComponentNotImplemented
from .schemas import RetrievedPassage

def build_index(artifact_dir: Path, index_dir: Path) -> None:
    # TODO Peiqi: index existing vectors and retain their chunk-ID mapping.
    raise ComponentNotImplemented('Peiqi: build index from existing embeddings.')

def retrieve_passages(question: str, top_k: int=10) -> list[RetrievedPassage]:
    # TODO Peiqi: embed the question, search, and return passages best first.
    raise ComponentNotImplemented('Peiqi: implement semantic retrieval.')
