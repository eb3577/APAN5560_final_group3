# Personalized Health Education Assistant


## Run the API

From the repository root, with the project environment installed:

```sh
source .venv/bin/activate
python -m uvicorn main:app --reload --port 8000
```

Open http://127.0.0.1:8000/docs and try `POST /explain`:

```json
{
  "question": "What are common symptoms of asthma?",
  "level": "simple",
  "mode": "baseline",
  "rerank": false
}
```

Levels are `simple`, `standard`, and `advanced`. Baseline uses the level prompt
without readability revision. Set `rerank` to true to use Peiqi's reranker.
The response includes source labels, titles, and `source_url` links. A source
reference identifies supplied evidence; it does not verify each generated claim.
Model answer quality is still under review.

Improved mode returns 501 until the readability/revision component is ready.
Missing resources return 503, invalid generated citations return 502, and invalid
requests return 422. `/health` reports server liveness, not model readiness.
