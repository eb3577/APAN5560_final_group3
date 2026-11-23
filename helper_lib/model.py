"""Generate text with a local instruction-tuned language model."""

from functools import lru_cache

from config import GENERATION_MODEL


DEFAULT_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
DEFAULT_REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"


@lru_cache(maxsize=1)
def _load_model():
    from transformers import AutoModelForCausalLM, AutoTokenizer

    model_id = GENERATION_MODEL or DEFAULT_MODEL
    revision = DEFAULT_REVISION if model_id == DEFAULT_MODEL else None
    return (
        AutoTokenizer.from_pretrained(model_id, revision=revision),
        AutoModelForCausalLM.from_pretrained(
            model_id, revision=revision, use_safetensors=True,
        ).eval(),
    )


def generate_text(prompt: str, max_new_tokens: int = 512) -> str:
    import torch

    if not prompt.strip() or max_new_tokens < 1:
        raise ValueError("Provide a prompt and a positive generation limit.")
    tokenizer, model = _load_model()
    inputs = tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}], add_generation_prompt=True,
        tokenize=True, return_dict=True, return_tensors="pt",
    )
    with torch.inference_mode():
        output = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    return tokenizer.decode(
        output[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True,
    ).strip()
