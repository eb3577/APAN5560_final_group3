# Step 1 · MedlinePlus data preparation

The October 28, 2026 [MedlinePlus Health Topics XML snapshot](https://medlineplus.gov/xml.html) contains 2,033 topics. The cleaner exports 1,017 English topics to CSV and JSON with source links and metadata. The chunker splits the 1,016 nonempty summaries into 2,546 passages of at most 180 words. The Hepatitis C record has no summary in this snapshot.

Run from the repository root with Python 3.11. Replace the XML filename with its local path if needed.

```sh
python step-1/clean_medlineplus.py mplus_topics_2026-10-28.xml --output-dir data/processed
python step-1/chunking/chunk_medlineplus.py data/processed/medlineplus_topics_en.json --output-dir data/processed
```

The checked-in reports document counts, missingness, chunk length and data provenance. The processed datasets can be generated with the commands above or obtained from the team’s shared Drive.
