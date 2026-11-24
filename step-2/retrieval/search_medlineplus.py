"""Run exact cosine retrieval over the existing MedlinePlus embeddings."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer


QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


def search(project, questions, top_k, data_dir=None):
    desktop_layout = (project / "Step Two").is_dir()
    embedding_dir = data_dir if data_dir is not None else project / (
        "Step Two" if desktop_layout else "Embedding"
    )
    report = json.loads((embedding_dir / "embedding_report.json").read_bytes())
    manifest = json.loads((embedding_dir / "embedding_manifest.json").read_bytes())
    vectors = np.load(embedding_dir / "medlineplus_embeddings.npy", allow_pickle=False)
    phase_one = "Step One" if desktop_layout else "phase1"
    chunk_file = project / phase_one / "chunking/medlineplus_chunks_en.json"
    if data_dir is not None:
        chunk_file = data_dir / chunk_file.name
    payload = chunk_file.read_bytes()
    if hashlib.sha256(payload).hexdigest() != report["input_sha256"]:
        raise ValueError("Chunk file does not match the saved embeddings.")
    chunks = {chunk["chunk_id"]: chunk for chunk in json.loads(payload)}
    if (vectors.shape != tuple(report["vector_shape"])
            or len(chunks) != len(manifest) or len(manifest) != len(vectors)
            or {item["chunk_id"] for item in manifest} != chunks.keys()
            or any(item["row"] != row for row, item in enumerate(manifest))):
        raise ValueError("Vector rows do not match the chunk manifest.")

    torch.set_num_threads(4)
    options = {"revision": report["model_revision"]}
    tokenizer = AutoTokenizer.from_pretrained(report["model"], **options)
    model = AutoModel.from_pretrained(
        report["model"], use_safetensors=True, **options,
    ).eval()
    inputs = tokenizer(
        [QUERY_PREFIX + question for question in questions], padding=True, return_tensors="pt",
    )
    if inputs["input_ids"].shape[1] > report["model_token_limit"]:
        raise ValueError("Question exceeds the model's token limit.")
    with torch.inference_mode():
        pooled = model(**inputs).last_hidden_state[:, 0]
        queries = torch.nn.functional.normalize(pooled, dim=1).numpy()

    results = []
    for question, scores in zip(questions, queries @ vectors.T):
        rows = np.argsort(-scores, kind="stable")[:top_k]
        matches = []
        for rank, row in enumerate(rows, start=1):
            chunk = chunks[manifest[row]["chunk_id"]]
            matches.append({
                "rank": rank,
                "cosine_similarity": round(float(scores[row]), 6),
                **{key: chunk[key] for key in ("chunk_id", "topic_id", "title", "url", "text")},
            })
        results.append({"question": question, "matches": matches})
    return {"model": report["model"], "query_prefix": QUERY_PREFIX, "results": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, help="Folder containing all processed artifacts")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("questions", nargs="+")
    args = parser.parse_args()
    if args.top_k < 1 or any(not question.strip() for question in args.questions):
        parser.error("Provide nonempty questions and a positive top-k.")
    print(json.dumps(search(args.project, args.questions, args.top_k, args.data_dir), ensure_ascii=False, indent=2))
