"""Scaffold checks only; these do NOT establish retrieval or answer quality."""
from fastapi.testclient import TestClient
import main
from helper_lib.errors import ResourceUnavailable
from helper_lib.schemas import Passage

client = TestClient(main.app)


def test_health_is_honest_about_readiness():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["pipeline_ready"] is False


def test_placeholder_for_every_level_and_mode():
    for level in ("simple", "standard", "advanced"):
        for mode in ("baseline", "improved"):
            response = client.post("/explain", json={
                "question": "What does this health term mean?",
                "level": level, "mode": mode,
            })
            assert response.status_code == 501
            assert "not implemented" in response.json()["detail"]


def test_invalid_requests_are_rejected():
    for payload in ({"question": "   "}, {"question": "x", "level": "doctor"},
                    {"question": "x", "mode": "unknown"}):
        assert client.post("/explain", json=payload).status_code == 422


def test_resource_error_is_reported(monkeypatch):
    def missing(request):
        raise ResourceUnavailable("Local model weights are missing.")
    monkeypatch.setattr(main, "explain", missing)
    response = client.post("/explain", json={"question": "Example question"})
    assert response.status_code == 503


def test_docs_include_endpoint():
    schema = client.get("/openapi.json").json()
    assert "/explain" in schema["paths"]
    assert client.get("/docs").status_code == 200


def test_nonmedical_fixture_matches_passage_contract():
    from pathlib import Path
    text = (Path(__file__).parent / "fixtures" / "passage.json").read_text()
    passage = Passage.model_validate_json(text)
    assert passage.chunk_id == "fixture-only-001"
