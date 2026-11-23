# Step 2 · Embeddings and baseline retrieval

The embedding script encodes title plus passage text with a pinned revision of BAAI/bge-small-en-v1.5. It writes 2,546 normalized 384-dimensional vectors, a row-to-chunk manifest and a validation report.

```sh
python -m pip install -r step-2/embedding/requirements.txt
python step-2/embedding/embed_medlineplus.py data/processed/medlineplus_chunks_en.json --output-dir data/processed
python step-2/retrieval/search_medlineplus.py --project . --data-dir data/processed "What are common symptoms of asthma?"
```

Use Python 3.11. First use requires downloading the model. If the team’s shared artifacts are already available, put the chunk JSON, embeddings, manifest and embedding report in `data/processed/` and run only the search command.

`retrieval/baseline_results.json` records the top five cosine matches for five exploratory questions. A manual check found a directly relevant passage in the top five for all five. The first passage comparing both diabetes types ranked third. This is a retrieval baseline for integration and reranking experiments.
