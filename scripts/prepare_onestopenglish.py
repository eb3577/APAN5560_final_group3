"""Prepare the three documented OneStopEnglish folders for readability analysis."""

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

LEVELS = {"Ele-Txt": ("ele", "elementary"),
          "Int-Txt": ("int", "intermediate"),
          "Adv-Txt": ("adv", "advanced")}


def clean_text(text, level):
    lines = [re.sub(r"[^\S\n]+", " ", line).strip()
             for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    while lines and not lines[0]:
        lines.pop(0)
    if lines and lines[0].casefold() == level:
        lines.pop(0)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def prepare(zip_path, output_dir):
    rows = []
    skipped = Counter()
    with ZipFile(zip_path) as archive:
        names = set(archive.namelist())
        for name in sorted(names):
            path = PurePosixPath(name)
            if name.endswith("/"):
                continue
            if path.name == ".DS_Store" or "__MACOSX" in path.parts:
                skipped["metadata"] += 1
                continue
            parts = path.parts
            if (len(parts) != 3 or parts[0] != "Texts-SeparatedByReadingLevel"
                    or parts[1] not in LEVELS):
                if (len(parts) == 4 and parts[1:3] == ("Int-Txt", "Int-Txt")):
                    skipped["nested_intermediate_alternates"] += 1
                    continue
                raise ValueError(f"Unexpected archive member: {name}")
            suffix, level = LEVELS[parts[1]]
            original = re.sub(r"\(\d+\)(?=\.txt$)", "", name)
            if original != name:
                if original not in names or archive.read(name) != archive.read(original):
                    raise ValueError(f"Numbered copy differs or has no original: {name}")
                skipped["identical_numbered_copies"] += 1
                continue
            if not path.name.endswith(f"-{suffix}.txt"):
                raise ValueError(f"Unexpected article filename: {name}")
            text = clean_text(archive.read(name).decode("utf-8-sig"), level)
            if not text or "\ufffd" in text:
                raise ValueError(f"Empty or damaged text: {name}")
            rows.append({"article_id": path.name[:-len(f"-{suffix}.txt")],
                         "level": level, "text": text, "source_file": name})
    by_article = {}
    for row in rows:
        levels = by_article.setdefault(row["article_id"], set())
        if row["level"] in levels:
            raise ValueError(f"Duplicate article/level: {row['article_id']}")
        levels.add(row["level"])
    expected = {item[1] for item in LEVELS.values()}
    if not rows or any(levels != expected for levels in by_article.values()):
        raise ValueError("Each article must have exactly three reading levels.")
    rows.sort(key=lambda row: (row["article_id"], row["level"]))
    report = {"archive": str(zip_path), "articles": len(by_article), "rows": len(rows),
              "levels": dict(Counter(row["level"] for row in rows)),
              "skipped": dict(skipped),
              "selection": "Direct files in the three README-documented level folders.",
              "limitation": "Nested intermediate alternatives differ, including punctuation. "
                            "They are excluded, not merged. Source punctuation is not repaired."}
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "onestopenglish.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["article_id", "level", "text", "source_file"])
        writer.writeheader()
        writer.writerows(rows)
    (output_dir / "preparation_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip_path", type=Path)
    parser.add_argument("--output-dir", type=Path,
                        default=Path("data/readability/onestopenglish"))
    args = parser.parse_args()
    print(json.dumps(prepare(args.zip_path, args.output_dir), indent=2))
