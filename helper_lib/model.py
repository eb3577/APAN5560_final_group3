"""Peiqi: shared adapter for a local pretrained language model."""
from .errors import ComponentNotImplemented

def generate_text(prompt: str, max_new_tokens: int=512) -> str:
    # TODO Peiqi: load/cache the chosen model; return generated text without the prompt.
    raise ComponentNotImplemented('Peiqi: select and connect local generation model.')
