"""Run with: python -m scripts.build_index."""
from config import BASE_DIR, DATA_DIR, ARTIFACT_DIR, INDEX_DIR
from helper_lib.errors import ComponentNotImplemented
from helper_lib.retrieval import build_index


def main():
    try:
        build_index(ARTIFACT_DIR, INDEX_DIR)
    except ComponentNotImplemented as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
