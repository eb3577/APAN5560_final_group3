# Personalized Health Education Assistant

APAN5560 Group 3 project: answer general health questions using MedlinePlus
sources, with simple, standard, and advanced explanations. The improved version
checks readability and revises the answer when needed.

## Setup

Use Python 3.11 or newer:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m uvicorn main:app --reload --port 8000
```

Open http://localhost:8000/docs. `/health` works; `/explain` currently returns
501 because the pipeline functions are placeholders. No model or API key is
needed to start the scaffold.

Example request for `/explain`:

```json
{"question": "What is asthma?", "level": "simple", "mode": "improved"}
```

## Where to add code

| Owner | Work | Files |
| --- | --- | --- |
| Peiqi | Existing data preparation and loading | `helper_lib/data_loader.py`, `preprocessing.py` |
| Peiqi | Embeddings, search, reranking and local LLM | `helper_lib/embeddings.py`, `retrieval.py`, `reranker.py`, `model.py` |
| Erik | Explanation levels and prompts | `helper_lib/generator.py`, `prompts/` |
| Cole / Alessio | Readability scores and revision | `helper_lib/readability.py`, `revision.py` |
| Peiqi | Baseline vs improved evaluation | `helper_lib/evaluator.py`, `evaluation/` |
| Erik | API integration and Docker | `app/health_assistant.py`, `main.py`, `Dockerfile` |
| Cole / Alessio | Report and presentation | `reports/` |

Replace the TODO placeholders with your implementation. Shared inputs and
outputs are in `helper_lib/schemas.py`; coordinate signature changes with the
people calling your functions. The optional FCNN can be added later if we use it.

## How the pieces connect

Question → retrieve passages → rerank → generate a cited explanation → check
readability → revise if needed → return the answer and sources.

- **Simple:** everyday language, no assumed medical knowledge.
- **Standard:** moderate detail, explain medical terminology.
- **Advanced:** technical wording and depth supported by the sources.

Baseline mode generates without revision. Improved mode adds the readability
feedback loop. Compare them with the same questions, levels, model and source
context. Evaluate reranking separately if measuring its effect.

Keep the explanations grounded in the passages and cite their chunk IDs.
Handle questions with insufficient sources rather than inventing an answer.
The project is for education, not diagnosis or individualized treatment advice.

## Data and configuration

See [Step 1](step-1/README.md) for MedlinePlus preparation and [Step 2](step-2/README.md)
for running the local RAG pipeline. Shared artifact locations are documented in
[data/README.md](data/README.md). Model overrides and other settings are in
`config.py` and `.env.example`. To load a local `.env` in your terminal:

```bash
set -a
source .env
set +a
```

Data, indexes, model weights and `.env` stay out of Git. `.gitkeep` files simply
retain otherwise empty folders and can go once those folders have tracked files.

## Tests and scripts

```bash
python -m pytest
python -m scripts.validate_data
python -m scripts.build_index
python -m scripts.run_evaluation
```

Tests currently cover the API shell. [Step 1](step-1/README.md) documents how
to regenerate the cleaned topics and passages. [Step 2](step-2/README.md)
documents local retrieval and generation. The evaluation script is a placeholder.

## Docker

```bash
docker build -t group3-health .
docker run --rm -p 8000:8000 group3-health
```

Once the pipeline works, mount `data/` and `models/` into `/app/data` and
`/app/models`. The image currently runs only the scaffold, not the finished RAG
system. Add model dependencies and test Docker after integration.

Before submission: test both modes at all three levels, evaluate readability
and source support, record results, finish the report/demo, and push reviewed
code. Passing the scaffold tests alone does not complete the project.
