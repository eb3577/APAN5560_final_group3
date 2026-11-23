# Evaluation — Peiqi

Add reviewed test questions to `questions.jsonl` with a question ID, question,
reference answer/source, dataset and split. Keep test answers out of retrieval
and inspect overlap. OneStopEnglish is for readability, not medical evidence.

Compare baseline and improved answers for the same questions, levels and source
context. Record model/settings, retrieved IDs, both answers, readability scores,
revision attempts and latency. `result_template.json` is a starting format.

Review source support, relevance, clarity and audience fit. For revisions, also
check that the meaning and citations are preserved. Agree on a scoring scale
before evaluating, and report failures as well as successes. Use null with a
reason for unavailable metrics; readability scores alone do not prove accuracy.

Save local outputs under `results/`; put the final findings in the report.
