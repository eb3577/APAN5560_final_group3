"""Run with: python -m scripts.prepare_data."""
from config import BASE_DIR, DATA_DIR, ARTIFACT_DIR, INDEX_DIR
from helper_lib.errors import ComponentNotImplemented
from helper_lib.preprocessing import prepare_data


def main():
    try:
        prepare_data(DATA_DIR / "raw", ARTIFACT_DIR)
    except ComponentNotImplemented as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
