"""Cole / Alessio: revise for readability while preserving facts and citations."""
from .errors import ComponentNotImplemented
from .schemas import AnswerDraft, ExplanationLevel, RetrievedPassage, RevisionResult

def revise_explanation(question: str, level: ExplanationLevel, answer: AnswerDraft, passages: list[RetrievedPassage], max_attempts: int=2) -> RevisionResult:
    # TODO Cole / Alessio: score, assess, revise, recheck sources; stop at the attempt limit.
    raise ComponentNotImplemented('Cole/Alessio: implement revision feedback loop.')
