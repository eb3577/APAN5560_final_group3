"""Load and validate the MedlinePlus retrieval artifacts."""

import hashlib
import json
from pathlib import Path

from .schemas import Passage


def load_passages(path: Path) -> list[Passage]:
    chunks = json.loads(path.read_bytes())
    passages = []
    seen = set()
    for chunk in chunks:
        passage = Passage(
            chunk_id=chunk["chunk_id"], topic_id=chunk["topic_id"],
            title=chunk["title"], text=chunk["text"], source_url=chunk["url"],
        )
        if not all(value.strip() for value in (
            passage.chunk_id, passage.topic_id, passage.title, passage.text,
        )):
            raise ValueError("Passages require IDs, a title and text.")
        if passage.chunk_id in seen:
            raise ValueError(f"Duplicate passage ID: {passage.chunk_id}")
        seen.add(passage.chunk_id)
        passages.append(passage)
    if not passages:
        raise ValueError("The chunk file contains no passages.")
    return passages


def load_embedding_artifacts(vectors_path: Path, manifest_path: Path):
    # Keep NumPy optional when starting the API without retrieval.
    import numpy as np

    matrix = np.load(vectors_path, allow_pickle=False)
    manifest = json.loads(manifest_path.read_bytes())
    if matrix.ndim != 2 or matrix.shape[1] != 384 or matrix.dtype != np.float32:
        raise ValueError("Expected a float32 embedding matrix with 384 columns.")
    if not len(matrix) or len(matrix) != len(manifest):
        raise ValueError("Embedding count does not match the manifest.")
    if not np.isfinite(matrix).all() or not np.allclose(
        np.linalg.norm(matrix, axis=1), 1.0, atol=1e-6, rtol=0,
    ):
        raise ValueError("Expected finite unit-length embeddings.")
    ids = []
    for row, item in enumerate(manifest):
        if item["row"] != row or not item["chunk_id"].strip():
            raise ValueError(f"Invalid manifest entry for embedding row {row}.")
        ids.append(item["chunk_id"])
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate chunk ID in the embedding manifest.")
    return matrix, ids


def validate_artifacts(data_dir: Path) -> dict:
    chunk_path = data_dir / "medlineplus_chunks_en.json"
    manifest_path = data_dir / "embedding_manifest.json"
    report = json.loads((data_dir / "embedding_report.json").read_bytes())
    checksum = hashlib.sha256(chunk_path.read_bytes()).hexdigest()
    if checksum != report["input_sha256"]:
        raise ValueError("Chunks do not match the embedding report checksum.")
    passages = load_passages(chunk_path)
    matrix, ids = load_embedding_artifacts(
        data_dir / "medlineplus_embeddings.npy", manifest_path,
    )
    if (ids != [passage.chunk_id for passage in passages]
            or list(matrix.shape) != report["vector_shape"]
            or len(passages) != report["input_chunks"]):
        raise ValueError("Chunk order or embedding shape does not match the saved artifacts.")
    for passage, item in zip(passages, json.loads(manifest_path.read_bytes())):
        if (passage.topic_id, passage.title, str(passage.source_url)) != (
            item["topic_id"], item["title"], item["url"],
        ):
            raise ValueError(f"Source metadata mismatch for {passage.chunk_id}.")
    return {
        "passages": len(passages),
        "topics": len({passage.topic_id for passage in passages}),
        "vector_shape": list(matrix.shape),
        "input_sha256": checksum,
        "model": report["model"],
        "model_revision": report["model_revision"],
        "source_mapping_verified": True,
    }
