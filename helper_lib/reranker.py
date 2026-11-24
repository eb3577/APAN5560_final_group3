"""Rerank candidate passages with a local cross-encoder."""

from functools import lru_cache

from config import RERANKER_MODEL
from .schemas import RetrievedPassage


DEFAULT_MODEL = "cross-encoder/ms-marco-MiniLM-L6-v2"
DEFAULT_REVISION = "233902d25c440f23af6f7d6e94d2946bac0bee0a"


@lru_cache(maxsize=1)
def _load_reranker():
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    model_id = RERANKER_MODEL or DEFAULT_MODEL
    revision = DEFAULT_REVISION if model_id == DEFAULT_MODEL else None
    return (
        AutoTokenizer.from_pretrained(model_id, revision=revision),
        AutoModelForSequenceClassification.from_pretrained(
            model_id, revision=revision, use_safetensors=True,
        ).eval(),
    )


def rerank_passages(question: str, passages: list[RetrievedPassage],
                    top_k: int = 3) -> list[RetrievedPassage]:
    import torch

    if top_k < 1:
        raise ValueError("top_k must be positive.")
    if not passages:
        return []
    tokenizer, model = _load_reranker()
    texts = [f"{hit.passage.title}\n{hit.passage.text}" for hit in passages]
    inputs = tokenizer(
        [question] * len(texts), texts, padding=True,
        truncation="only_second", max_length=512, return_tensors="pt",
    )
    with torch.inference_mode():
        scores = model(**inputs).logits.squeeze(-1).tolist()
    ranked = [
        hit.model_copy(update={"rerank_score": score})
        for hit, score in zip(passages, scores)
    ]
    return sorted(ranked, key=lambda hit: hit.rerank_score, reverse=True)[:top_k]
