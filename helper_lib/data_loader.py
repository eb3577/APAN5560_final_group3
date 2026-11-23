"""Peiqi: adapt the existing JSON, vectors and manifest to our shared schemas."""
from pathlib import Path
from .errors import ComponentNotImplemented
from .schemas import Passage

def load_passages(path: Path) -> list[Passage]:
    # TODO Peiqi: load chunks; preserve IDs, text, titles and URLs.
    raise ComponentNotImplemented('Peiqi: integrate existing chunk JSON loader.')

def load_embedding_artifacts(vectors_path: Path, manifest_path: Path):
    # TODO Peiqi: return (matrix, ordered_chunk_ids); verify row alignment and encoding settings.
    raise ComponentNotImplemented('Peiqi: integrate vectors and manifest mapping.')

def validate_artifacts(data_dir: Path) -> dict:
    # TODO Peiqi: check counts, unique IDs, finite vectors and source coverage.
    raise ComponentNotImplemented('Peiqi: integrate artifact validation report.')
