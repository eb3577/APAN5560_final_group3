"""Split cleaned MedlinePlus summaries into source-linked passages."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


MAX_WORDS = 180


def summary_passages(summary):
    lines = []
    word_count = 0
    for raw_line in summary.splitlines():
        words = raw_line.split()
        for offset in range(0, len(words), MAX_WORDS):
            part = words[offset:offset + MAX_WORDS]
            if word_count + len(part) > MAX_WORDS:
                yield "\n".join(lines)
                lines = []
                word_count = 0
            lines.append(" ".join(part))
            word_count += len(part)
    if lines:
        yield "\n".join(lines)


def chunk_topics(input_path, output_dir):
    payload = input_path.read_bytes()
    topics = json.loads(payload)
    chunks = []
    skipped = []
    seen = set()
    for topic in topics:
        source = {key: topic[key] for key in ("title", "url")}
        topic_id = topic["id"]
        if not topic_id or topic_id in seen or not all(source.values()):
            raise ValueError(f"Duplicate ID or missing provenance for topic {topic_id!r}")
        seen.add(topic_id)
        passages = list(summary_passages(topic["summary"]))
        if not passages:
            skipped.append({"topic_id": topic_id, **source})
            continue
        if " ".join(passages).split() != topic["summary"].split():
            raise ValueError(f"Chunk text differs from source summary for {topic_id}")
        for number, passage in enumerate(passages, start=1):
            chunks.append({
                "chunk_id": f"{topic_id}-{number:03d}",
                "topic_id": topic_id,
                **source,
                "chunk_number": number,
                "word_count": len(passage.split()),
                "text": passage,
            })

    lengths = sorted(chunk["word_count"] for chunk in chunks)
    if not lengths or lengths[0] < 1 or lengths[-1] > MAX_WORDS:
        raise ValueError("Expected nonempty chunks within the word limit")
    if len({chunk["chunk_id"] for chunk in chunks}) != len(chunks):
        raise ValueError("Duplicate chunk IDs")
    counts = Counter(chunk["topic_id"] for chunk in chunks)
    report = {
        "input_file": input_path.name,
        "input_sha256": hashlib.sha256(payload).hexdigest(),
        "max_words_per_chunk": MAX_WORDS,
        "overlap_words": 0,
        "input_topics": len(topics),
        "topics_with_chunks": len(counts),
        "skipped_topics": skipped,
        "chunk_count": len(chunks),
        "words_per_chunk": {
            "min": lengths[0],
            "mean": round(sum(lengths) / len(lengths), 1),
            "max": lengths[-1],
        },
        "chunks_per_topic": dict(sorted(Counter(counts.values()).items())),
        "source_text_preserved_ignoring_whitespace": True,
        "unique_chunk_ids": True,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, data in (
        ("medlineplus_chunks_en.json", chunks),
        ("chunking_report.json", report),
    ):
        (output_dir / name).write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    print(f"Wrote {len(chunks)} chunks from {len(counts)} topics.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("topics_json", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        chunk_topics(args.topics_json, args.output_dir)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f"{exc}\n")
