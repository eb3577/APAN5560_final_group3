"""Run with: python -m scripts.validate_data."""
from config import BASE_DIR, DATA_DIR, ARTIFACT_DIR, INDEX_DIR
from helper_lib.errors import ComponentNotImplemented
from helper_lib.data_loader import validate_artifacts


def main():
    try:
        print(validate_artifacts(DATA_DIR))
    except ComponentNotImplemented as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
