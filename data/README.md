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

## OneStopEnglish preparation

Run from the repository root (no extra dependencies):

```sh
python scripts/prepare_onestopenglish.py /path/to/Texts-SeparatedByReadingLevel.zip
```

Outputs `data/readability/onestopenglish/onestopenglish.csv` and
`preparation_report.json`. The CSV contains article_id, level, text, and
source_file; the supplied archive produces 189 articles / 567 rows.
The original ZIP is unchanged and generated data remains ignored by Git.

Use the three direct level folders described in the corpus README. Numbered
advanced copies are skipped only after verifying identical bytes. The nested
intermediate folder contains differing alternatives and is excluded. Some
alternatives preserve punctuation absent from the selected files; this may
affect readability scores. Cleaning removes standalone leading level labels
and tidies whitespace, preserving remaining punctuation and line breaks.

Use this corpus for readability analysis, not medical retrieval. Keep all
versions of an article together if creating training/test splits. The corpus
levels are not validated medical-expertise labels.

Source: Vajjala, S. and Lučić, I. (2018). *OneStopEnglish corpus: A new corpus
for automatic readability assessment and text simplification*. BEA, 297–304.
https://aclanthology.org/W18-0535/
Corpus: https://github.com/nishkalavallabhi/OneStopEnglishCorpus
License stated in the supplied README: Creative Commons Attribution-ShareAlike
4.0 (https://creativecommons.org/licenses/by-sa/4.0/). Local preparation changes
are described above; retain attribution and license when sharing derived data.
