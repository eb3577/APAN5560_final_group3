"""Encode search queries using the saved passage model revision."""

from functools import lru_cache
import json

from config import ARTIFACT_DIR, PASSAGE_EMBEDDING_MODEL


QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


@lru_cache(maxsize=1)
def _load_encoder(model_id, revision):
    import torch
    from transformers import AutoModel, AutoTokenizer

    torch.set_num_threads(4)
    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
    model = AutoModel.from_pretrained(
        model_id, revision=revision, use_safetensors=True,
    ).eval()
    return tokenizer, model


def embed_query(question: str) -> list[float]:
    import torch

    if not question.strip():
        raise ValueError("Provide a nonempty question.")
    report = json.loads((ARTIFACT_DIR / "embedding_report.json").read_bytes())
    if (report["model"] != PASSAGE_EMBEDDING_MODEL
            or report["pooling"] != "CLS" or report["normalization"] != "L2"):
        raise ValueError("Embedding report uses an incompatible model or encoding.")
    tokenizer, model = _load_encoder(report["model"], report["model_revision"])
    inputs = tokenizer(QUERY_PREFIX + question, return_tensors="pt", verbose=False)
    if inputs["input_ids"].shape[1] > report["model_token_limit"]:
        raise ValueError("Question exceeds the embedding model's token limit.")
    with torch.inference_mode():
        pooled = model(**inputs).last_hidden_state[:, 0]
        return torch.nn.functional.normalize(pooled, dim=1)[0].tolist()
