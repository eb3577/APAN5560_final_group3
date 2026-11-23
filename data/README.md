# Data

Peiqi: place the existing artifacts in these folders and adapt their field names
in `helper_lib/data_loader.py`. No need to regenerate completed work.

| Folder | Contents |
| --- | --- |
| `raw/` | Original MedlinePlus XML, if retained |
| `processed/` | `medlineplus_topics_en.json`, `medlineplus_chunks_en.json`, `medlineplus_embeddings.npy`, `embedding_manifest.json` |
| `index/` | Search index and passage-ID mapping |
| `evaluation/medquad/` | Medical Q&A for evaluation |
| `readability/onestopenglish/` | Reading-level analysis data |

Reported counts: 1,017 English topics, 2,546 passages from 1,016 topics, and
384-dimensional embeddings from `BAAI/bge-small-en-v1.5`. Hepatitis C has no
summary passages. Confirm counts and vector-to-chunk alignment when loading.
Keep source IDs, titles and URLs. Match query encoding to the original embedding
settings. Keep evaluation answers out of the retrieval index.

Bulk data is ignored by Git. Record the shared download location and artifact
versions here once available.
