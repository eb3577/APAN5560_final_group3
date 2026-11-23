"""Peiqi: paired baseline/improved comparison using the same levels and context."""
from pathlib import Path
from .errors import ComponentNotImplemented

def run_evaluation(questions_path: Path, results_dir: Path) -> None:
    # TODO Peiqi: run held-out questions; save outputs, metrics and source-support reviews.
    raise ComponentNotImplemented('Peiqi: implement evaluation and comparison.')
