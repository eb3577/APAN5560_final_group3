"""Project paths and starting settings. Model choices are still pending."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("HEALTH_DATA_DIR", str(BASE_DIR / "data")))
ARTIFACT_DIR = DATA_DIR / "processed"
INDEX_DIR = DATA_DIR / "index"
MODEL_DIR = Path(os.getenv("HEALTH_MODEL_DIR", str(BASE_DIR / "models")))
PASSAGE_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
GENERATION_MODEL = os.getenv("GENERATION_MODEL", "")
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "")
RETRIEVE_TOP_K = 10
CONTEXT_TOP_K = 3
MAX_REVISION_ATTEMPTS = 2
