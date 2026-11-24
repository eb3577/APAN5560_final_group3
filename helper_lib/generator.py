"""Generate source-cited explanations at the requested reading level."""

import re

from config import BASE_DIR
from .model import generate_text
from .errors import InvalidGeneratedAnswer
from .schemas import AnswerDraft, ExplanationLevel, RetrievedPassage


def generate_explanation(question: str, level: ExplanationLevel,
                         passages: list[RetrievedPassage]) -> AnswerDraft:
    """Return an empty draft for insufficient evidence; reject invalid citations."""
    if not question.strip():
        raise ValueError("Provide a nonempty question.")
    level = ExplanationLevel(level)
    if not passages:
        return AnswerDraft(text="")

    sources = {f"S{i}": hit.passage for i, hit in enumerate(passages, start=1)}
    context = "\n\n".join(
        f"[{label}] {passage.title}\n{passage.text}"
        for label, passage in sources.items()
    )
    template = (BASE_DIR / "prompts" / f"{level.value}.txt").read_text(encoding="utf-8")
    text = generate_text(template.format(question=question.strip(), context=context)).strip()
    if not text or text.upper().startswith("INSUFFICIENT_EVIDENCE"):
        return AnswerDraft(text="")

    labels = re.findall(r"\[S([^\[\]]*)\]", text)
    if not labels and len(sources) == 1:
        # Match the Step 2 pipeline: attribute the sole supplied passage.
        # This identifies the context used, not proof of factual support.
        text += "\n\nSource: [S1]"
        labels = ["1"]
    if not labels:
        raise InvalidGeneratedAnswer("Generated explanation has no source citations.")
    cited_ids = []
    for number in labels:
        label = f"S{number}"
        if label not in sources:
            raise InvalidGeneratedAnswer(f"Generated explanation cites an unknown source: [{label}].")
        chunk_id = sources[label].chunk_id
        if chunk_id not in cited_ids:
            cited_ids.append(chunk_id)
    return AnswerDraft(text=text, cited_chunk_ids=cited_ids)
