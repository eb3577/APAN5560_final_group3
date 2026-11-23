"""Erik: create cited explanations using prompts/ and model.generate_text."""
from .errors import ComponentNotImplemented
from .schemas import AnswerDraft, ExplanationLevel, RetrievedPassage

def generate_explanation(question: str, level: ExplanationLevel, passages: list[RetrievedPassage]) -> AnswerDraft:
    # TODO Erik: assemble context/prompt, generate, and validate citations against supplied passages.
    raise ComponentNotImplemented('Erik: implement cited, level-specific generation.')
