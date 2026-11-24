"""Run with: python -m scripts.validate_data."""

import json

from config import ARTIFACT_DIR
from helper_lib.data_loader import validate_artifacts


if __name__ == "__main__":
    print(json.dumps(validate_artifacts(ARTIFACT_DIR), indent=2))
