"""Build a local FAISS index and retrieve MedlinePlus passages."""

import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import NamedTemporaryFile

from config import ARTIFACT_DIR, INDEX_DIR
from .data_loader import load_embedding_artifacts, load_passages, validate_artifacts
from .embeddings import embed_query
from .schemas import RetrievedPassage


INDEX_FILENAME = "medlineplus.faiss"


def _load_vectors(artifact_dir):
    return load_embedding_artifacts(
        artifact_dir / "medlineplus_embeddings.npy",
        artifact_dir / "embedding_manifest.json",
    )


def build_index(artifact_dir: Path, index_dir: Path) -> None:
    import faiss

    validate_artifacts(artifact_dir)
    matrix, _ = _load_vectors(artifact_dir)
    index = faiss.IndexFlatIP(matrix.shape[1])
    index.add(matrix)

    index_dir.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=index_dir, suffix=".faiss", delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        faiss.write_index(index, str(temporary_path))
        temporary_path.replace(index_dir / INDEX_FILENAME)
    finally:
        temporary_path.unlink(missing_ok=True)


def retrieve_passages(question: str, top_k: int = 10) -> list[RetrievedPassage]:
    if top_k < 1:
        raise ValueError("top_k must be positive.")
    validate_artifacts(ARTIFACT_DIR)
    passages = load_passages(ARTIFACT_DIR / "medlineplus_chunks_en.json")
    path = INDEX_DIR / INDEX_FILENAME
    if not path.is_file():
        raise FileNotFoundError("Build the index first with python -m scripts.build_index.")
    # FAISS and PyTorch wheels can load conflicting OpenMP runtimes on macOS.
    # Keep index search in a worker that imports FAISS without importing PyTorch.
    result = subprocess.run(
        [sys.executable, "-m", "helper_lib.faiss_search", str(path),
         str(ARTIFACT_DIR / "medlineplus_embeddings.npy"), str(min(top_k, len(passages)))],
        input=json.dumps(embed_query(question)), capture_output=True, text=True,
        env={**os.environ, "TOKENIZERS_PARALLELISM": "false"},
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "FAISS worker failed.")
    return [
        RetrievedPassage(passage=passages[row], retrieval_score=score)
        for score, row in json.loads(result.stdout)
    ]
