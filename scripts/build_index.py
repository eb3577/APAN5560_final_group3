"""Run with: python -m scripts.build_index."""

from config import ARTIFACT_DIR, INDEX_DIR
from helper_lib.retrieval import build_index


if __name__ == "__main__":
    build_index(ARTIFACT_DIR, INDEX_DIR)
