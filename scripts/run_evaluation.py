"""Run with: python -m scripts.run_evaluation."""
from config import BASE_DIR, DATA_DIR, ARTIFACT_DIR, INDEX_DIR
from helper_lib.errors import ComponentNotImplemented
from helper_lib.evaluator import run_evaluation


def main():
    try:
        run_evaluation(BASE_DIR / "evaluation" / "questions.jsonl", BASE_DIR / "evaluation" / "results")
    except ComponentNotImplemented as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
