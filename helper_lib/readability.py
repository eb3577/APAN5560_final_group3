"""Cole / Alessio: readability scores and agreed audience-level targets."""
from .errors import ComponentNotImplemented
from .schemas import ExplanationLevel, LevelAssessment, ReadabilityScores

def score_readability(text: str) -> ReadabilityScores:
    # TODO Cole / Alessio: calculate FK and SMOG; return None plus a note when not applicable.
    raise ComponentNotImplemented('Cole/Alessio: implement readability metrics.')

def assess_level(text: str, level: ExplanationLevel, scores: ReadabilityScores) -> LevelAssessment:
    # TODO Cole / Alessio: assess agreed targets and terminology; None means not assessable.
    raise ComponentNotImplemented('Cole/Alessio: define and assess level targets.')
