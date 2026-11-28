"""API integration checks with controlled retrieval and model responses."""
import pytest
from fastapi.testclient import TestClient
import main
from app import health_assistant
from helper_lib import generator, revision
from helper_lib.schemas import Passage, RetrievedPassage

client = TestClient(main.app)

ADVANCED_CITED = (
    "Essential hypertension is a chronic cardiovascular condition characterized by "
    "persistently elevated pressure within the systemic arterial vessels over time [S1]. "
    "Primary mechanisms include endothelial dysfunction, increased sympathetic nervous "
    "activity, and impaired renal sodium regulation across multiple organ systems [S1]. "
    "Without adequate intervention, sustained hemodynamic overload promotes ventricular "
    "hypertrophy and elevates the long-term risk of stroke or kidney failure [S1]. "
    "Clinical management combines structured behavioral modification with individualized "
    "pharmacologic therapy guided by each patient's overall cardiovascular risk [S1]."
)

SIMPLE_CITED = (
    "High blood pressure happens when blood pushes too hard on artery walls [S1]. "
    "Over time, this extra force can harm your heart and kidneys [S1]. "
    "Most people do not feel sick at first, so regular checks matter [S1]. "
    "Simple daily habits and safe medicine can help keep your numbers down [S1]."
)


@pytest.fixture
def sources(monkeypatch):
    hits = [RetrievedPassage(passage=Passage(
        chunk_id='example-1', topic_id='topic-1', title='Example topic',
        text='Example source text.', source_url='https://example.org/topic',
    ), retrieval_score=0.9)]
    monkeypatch.setattr(health_assistant, 'retrieve_passages', lambda *args: hits)
    return hits


@pytest.mark.parametrize('level', ['simple', 'standard', 'advanced'])
def test_answer_and_source_mapping(monkeypatch, sources, level):
    monkeypatch.setattr(generator, 'generate_text', lambda prompt: 'Example answer.')
    response = client.post('/explain', json={'question': 'Example?', 'level': level})
    assert response.status_code == 200
    data = response.json()
    assert data['mode'] == 'baseline'
    assert data['answer']['text'].endswith('Source: [S1]')
    assert data['sources'][0]['label'] == 'S1'
    assert data['sources'][0]['source_url'] == 'https://example.org/topic'
    assert data['sources'][0]['chunk_id'] == data['answer']['cited_chunk_ids'][0]
    assert data['initial_readability'] is None and data['revision_attempts'] == 0


def test_insufficient_evidence(monkeypatch, sources):
    monkeypatch.setattr(generator, 'generate_text', lambda prompt: 'INSUFFICIENT_EVIDENCE')
    data = client.post('/explain', json={'question': 'Example?'}).json()
    assert data['status'] == 'insufficient_sources'
    assert data['sources'] == [] and data['answer']['cited_chunk_ids'] == []


def test_empty_retrieval_skips_model(monkeypatch):
    monkeypatch.setattr(health_assistant, 'retrieve_passages', lambda *args: [])
    monkeypatch.setattr(generator, 'generate_text', lambda prompt: pytest.fail('Unexpected model call'))
    assert client.post('/explain', json={'question': 'Example?'}).json()['status'] == 'insufficient_sources'


def test_invalid_citation_is_502(monkeypatch, sources):
    monkeypatch.setattr(generator, 'generate_text', lambda prompt: 'Wrong source [S9].')
    response = client.post('/explain', json={'question': 'Example?'})
    assert response.status_code == 502


def test_missing_data_is_503(monkeypatch):
    def missing(*args):
        raise FileNotFoundError('private/local/path')
    monkeypatch.setattr(health_assistant, 'retrieve_passages', missing)
    response = client.post('/explain', json={'question': 'Example?'})
    assert response.status_code == 503
    assert 'private/local/path' not in response.text


def test_improved_revises_answer(monkeypatch, sources):
    monkeypatch.setattr(generator, 'generate_text', lambda prompt: ADVANCED_CITED)
    monkeypatch.setattr(revision, 'generate_text', lambda prompt: SIMPLE_CITED)
    response = client.post(
        '/explain',
        json={'question': 'Example?', 'level': 'simple', 'mode': 'improved'},
    )
    assert response.status_code == 200
    data = response.json()
    assert data['mode'] == 'improved'
    assert data['status'] == 'answered'
    assert data['answer']['text'] == SIMPLE_CITED
    assert data['sources'][0]['label'] == 'S1'
    assert data['sources'][0]['chunk_id'] == 'example-1'
    assert data['initial_readability'] is not None
    assert data['final_readability'] is not None
    assert (
        data['final_readability']['flesch_kincaid_grade']
        < data['initial_readability']['flesch_kincaid_grade']
    )
    assert data['target_met'] is True
    assert data['revision_attempts'] == 1
    assert data['stop_reason'] == 'target_met'


def test_reranker_is_used(monkeypatch, sources):
    calls = []
    def rerank(question, hits, top_k):
        calls.append((question, hits, top_k))
        return hits
    monkeypatch.setattr(health_assistant, 'rerank_passages', rerank)
    monkeypatch.setattr(generator, 'generate_text', lambda prompt: 'Example [S1].')
    response = client.post('/explain', json={'question': 'Example?', 'rerank': True})
    assert response.status_code == 200
    assert calls == [('Example?', sources, 1)]