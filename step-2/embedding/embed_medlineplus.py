"""Encode cleaned MedlinePlus passages as normalized English text embeddings."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer


MODEL_ID = "BAAI/bge-small-en-v1.5"
MODEL_REVISION = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
DIMENSIONS = 384
BATCH_SIZE = 24


def read_chunks(path):
    payload = path.read_bytes()
    chunks = json.loads(payload)
    ids = [chunk["chunk_id"] for chunk in chunks]
    if not ids or len(set(ids)) != len(ids) or not all(ids):
        raise ValueError("Input must contain nonempty, unique chunk IDs.")
    if any(not chunk["text"].strip() for chunk in chunks):
        raise ValueError("Input contains an empty passage.")
    return chunks, hashlib.sha256(payload).hexdigest()


def encode(chunks, revision):
    torch.set_num_threads(4)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision=revision)
    model = AutoModel.from_pretrained(
        MODEL_ID, revision=revision, use_safetensors=True,
    ).eval()
    model_limit = min(tokenizer.model_max_length, model.config.max_position_embeddings)
    texts = [f'{chunk["title"]}\n{chunk["text"]}' for chunk in chunks]
    token_lengths = [
        len(ids) for ids in tokenizer(
            texts, truncation=False, verbose=False, return_attention_mask=False,
        )["input_ids"]
    ]
    if max(token_lengths) > model_limit:
        raise ValueError(f"A passage exceeds the model limit of {model_limit} tokens.")

    # Similar lengths in a batch reduce padding. Restore source order in the matrix.
    order = sorted(range(len(texts)), key=token_lengths.__getitem__)
    vectors = np.empty((len(texts), DIMENSIONS), dtype=np.float32)
    with torch.inference_mode():
        for start in range(0, len(texts), BATCH_SIZE):
            indices = order[start:start + BATCH_SIZE]
            inputs = tokenizer(
                [texts[index] for index in indices], padding=True, return_tensors="pt",
            )
            pooled = model(**inputs).last_hidden_state[:, 0]
            vectors[indices] = torch.nn.functional.normalize(pooled, p=2, dim=1).numpy()
            if start % (BATCH_SIZE * 20) == 0:
                print(f"Encoded {start + len(indices)}/{len(texts)} passages.", flush=True)
    if not np.isfinite(vectors).all() or not np.allclose(
        np.linalg.norm(vectors, axis=1), 1.0, atol=1e-6,
    ):
        raise ValueError("Expected finite unit-length vectors.")
    return vectors, max(token_lengths), model_limit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chunks_json", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--revision", default=MODEL_REVISION, help="Hugging Face model commit SHA")
    args = parser.parse_args()

    chunks, digest = read_chunks(args.chunks_json)
    revision = args.revision
    print(f"Loading {MODEL_ID} at {revision}.", flush=True)
    vectors, max_tokens, model_limit = encode(chunks, revision)
    mapping = [
        {"row": row, **{key: chunk[key] for key in ("chunk_id", "topic_id", "title", "url")}}
        for row, chunk in enumerate(chunks)
    ]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    np.save(args.output_dir / "medlineplus_embeddings.npy", vectors, allow_pickle=False)
    report = {
        "model": MODEL_ID,
        "model_revision": revision,
        "input_file": args.chunks_json.name,
        "input_sha256": digest,
        "input_format": "title + newline + passage text",
        "input_chunks": len(chunks),
        "vector_shape": list(vectors.shape),
        "dtype": str(vectors.dtype),
        "pooling": "CLS",
        "normalization": "L2",
        "model_token_limit": model_limit,
        "max_input_tokens": max_tokens,
        "truncated_passages": 0,
        "all_vectors_finite": True,
        "all_vectors_unit_length": True,
        "unique_chunk_ids": True,
    }
    for name, data in (
        ("embedding_manifest.json", mapping),
        ("embedding_report.json", report),
    ):
        (args.output_dir / name).write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
    print(f"Saved {vectors.shape[0]} vectors with {vectors.shape[1]} dimensions.")


if __name__ == "__main__":
    main()
