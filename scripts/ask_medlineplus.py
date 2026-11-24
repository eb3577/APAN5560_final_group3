"""Run the Step 2 retrieval and generation pipeline locally."""

import argparse
import json

from config import RETRIEVE_TOP_K
from helper_lib.model import generate_text
from helper_lib.generator import generate_explanation
from helper_lib.schemas import ExplanationLevel
from helper_lib.reranker import rerank_passages
from helper_lib.retrieval import retrieve_passages


def answer(question: str, use_reranker: bool = False,
           level: str | None = None) -> dict:
    hits = retrieve_passages(question, RETRIEVE_TOP_K if use_reranker else 1)
    if use_reranker:
        hits = rerank_passages(question, hits, 1)
    if not hits:
        return {"status": "insufficient_sources", "answer": "", "sources": []}
    if level is not None:
        draft = generate_explanation(question, ExplanationLevel(level), hits)
        if not draft.text:
            return {"status": "insufficient_sources", "answer": "", "sources": []}
        return {
            "status": "answered", "answer": draft.text, "level": level,
            "sources": [
                {"label": f"S{i}", "chunk_id": hit.passage.chunk_id,
                 "title": hit.passage.title, "url": str(hit.passage.source_url)}
                for i, hit in enumerate(hits, start=1)
                if hit.passage.chunk_id in draft.cited_chunk_ids
            ],
        }
    passage = hits[0].passage
    text = generate_text(
        f"Passage from MedlinePlus ({passage.title}):\n{passage.text}\n\n"
        f"Question: {question}\n"
        "Answer briefly using exact words from the passage where possible. For list "
        "questions, give only the item names, without definitions or elaboration. "
        "If the passage does not answer the question, reply exactly "
        "INSUFFICIENT_EVIDENCE. Give only the answer.",
        max_new_tokens=80,
    )
    if not text or text.upper().startswith("INSUFFICIENT_EVIDENCE"):
        return {"status": "insufficient_sources", "answer": "", "sources": []}
    return {
        "status": "answered",
        "answer": f"{text} [S1]",
        "sources": [
            {"label": "S1", "chunk_id": passage.chunk_id,
             "title": passage.title, "url": str(passage.source_url)}
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--rerank", action="store_true")
    parser.add_argument("--level", choices=[level.value for level in ExplanationLevel],
                        help="Use a level-specific explanation; omit for the original Step 2 answer.")
    args = parser.parse_args()
    print(json.dumps(answer(args.question, args.rerank, args.level), indent=2, ensure_ascii=False))
