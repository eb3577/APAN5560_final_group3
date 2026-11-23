# Step 2 · Basic MedlinePlus RAG

Use Python 3.11. The first run downloads the models. The commands below run
from the repository root.

```sh
python -m pip install -e '.[retrieval]'
python -m scripts.validate_data
python -m scripts.build_index
python -m scripts.ask_medlineplus "What are common symptoms of asthma?"
```

Before validation, place the four shared files in `data/processed/`:
`medlineplus_chunks_en.json`, `medlineplus_embeddings.npy`,
`embedding_manifest.json`, and `embedding_report.json`. To regenerate
embeddings after Step 1, run:

```sh
python step-2/embedding/embed_medlineplus.py data/processed/medlineplus_chunks_en.json --output-dir data/processed
```

The pipeline encodes questions with the passage model revision recorded in the
embedding report, searches the 2,546 normalized vectors using FAISS
`IndexFlatIP`, and passes the highest-ranked passage to a local Qwen model. Add
`--rerank` to retrieve ten candidates and select the best passage with the
MiniLM cross-encoder. The JSON answer cites the passage supplied to the model.
Assess factual support against the cited text when reviewing the results.

`retrieval/baseline_results.json` records the original NumPy search results.
`retrieval/faiss_validation.json` records the five-question FAISS comparison.
The checked-in verification files describe a small exploratory test.
`retrieval/reranking_comparison.json` records candidate order before and after
reranking. The general diabetes comparison passage moved from third to second.
