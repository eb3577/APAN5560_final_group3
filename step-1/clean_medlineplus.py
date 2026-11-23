"""Export English health topics from a local MedlinePlus XML snapshot."""

import argparse
from collections import Counter
import csv
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET


SOURCE = "https://medlineplus.gov/xml.html"
BLOCKS = {"p", "div", "section", "br", "ul", "ol", "li", "table", "tr",
          "blockquote", "h1", "h2", "h3", "h4", "h5", "h6"}
MARKUP = re.compile(r"</?[A-Za-z][\w:-]*(?:\s[^<>]*?)?\s*/?>|<!--")


class SummaryParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = None

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden = tag
        elif not self.hidden:
            if tag in BLOCKS:
                self.parts.append("\n- " if tag == "li" else "\n")
            elif tag in {"td", "th"}:
                self.parts.append(" ")
            elif tag == "img":
                self.parts.append(dict(attrs).get("alt") or "")

    def handle_endtag(self, tag):
        if tag == self.hidden:
            self.hidden = None
        elif not self.hidden and tag in BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(re.sub(r"\s+", " ", data))

    def clean_text(self):
        lines = (" ".join(line.split()) for line in "".join(self.parts).splitlines())
        return "\n".join(line for line in lines if line)


def text_inside(element):
    return " ".join("".join(element.itertext()).split())


def metadata(elements):
    return [{"title": text_inside(item), **item.attrib} for item in elements]


def extract(topic):
    parser = SummaryParser()
    summary = topic.find("full-summary")
    if summary is not None:
        fragment = (summary.text or "") + "".join(
            ET.tostring(child, encoding="unicode") for child in summary
        )
        parser.feed(fragment)
        parser.close()
    return {
        "id": topic.get("id", "").strip(),
        "title": topic.get("title", "").strip(),
        "url": topic.get("url", "").strip(),
        "language": topic.get("language", ""),
        "summary": parser.clean_text(),
        "meta_description": topic.get("meta-desc", "").strip(),
        "date_created": topic.get("date-created", "").strip(),
        "also_called": [text_inside(item) for item in topic.findall("also-called")],
        "see_references": [text_inside(item) for item in topic.findall("see-reference")],
        "groups": metadata(topic.findall("group")),
        "related_topics": metadata(topic.findall("related-topic")),
        "mesh_headings": [
            {"descriptor": metadata(item.findall("descriptor")),
             "qualifiers": metadata(item.findall("qualifier"))}
            for item in topic.findall("mesh-heading")
        ],
        "primary_institutes": metadata(topic.findall("primary-institute")),
        "source": "MedlinePlus.gov",
    }


def duplicate_groups(rows, field):
    groups = {}
    for row in rows:
        if row[field]:
            groups.setdefault(row[field].casefold(), []).append(row["id"])
    return [ids for ids in groups.values() if len(ids) > 1]


def valid_topic_url(url):
    try:
        parsed = urlsplit(url)
        return (parsed.scheme == "https" and parsed.netloc == "medlineplus.gov"
                and parsed.path.endswith(".html") and not parsed.query
                and not parsed.fragment and not any(char.isspace() for char in url))
    except ValueError:
        return False


def clean(input_path, output_dir):
    payload = input_path.read_bytes()
    root = ET.fromstring(payload)
    if root.tag != "health-topics":
        raise ValueError("Expected a MedlinePlus health-topics XML file.")
    topics = root.findall("health-topic")
    languages = Counter(topic.get("language") or "(missing)" for topic in topics)
    rows = [extract(topic) for topic in topics if topic.get("language") == "English"]
    if not rows:
        raise ValueError("No English health topics found.")

    missing = {field: sum(not row[field] for row in rows) for field in rows[0]}
    duplicates = {
        field: duplicate_groups(rows, field) for field in ("id", "title", "url", "summary")
    }
    bad_urls = [row["id"] for row in rows if not valid_topic_url(row["url"])]
    markup_ids = [row["id"] for row in rows if MARKUP.search(row["summary"])]
    declared = root.get("total")
    checks = {
        "xml_count_matches": declared is None or int(declared) == len(topics),
        "required_fields_present": not any(missing[key] for key in ("id", "title", "url")),
        "unique_ids_and_urls": not (duplicates["id"] or duplicates["url"]),
        "canonical_topic_urls": not bad_urls,
        "no_summary_html_tags": not markup_ids,
    }
    report = {
        "input_file": input_path.name,
        "input_sha256": hashlib.sha256(payload).hexdigest(),
        "source": SOURCE,
        "xml_date_generated": root.get("date-generated"),
        "xml_declared_topics": int(declared) if declared is not None else None,
        "xml_topics": len(topics),
        "languages": dict(sorted(languages.items())),
        "exported_topics": len(rows),
        "excluded_topics": len(topics) - len(rows),
        "missing_by_field": missing,
        "missing_summary_topics": [
            {key: row[key] for key in ("id", "title", "url")}
            for row in rows if not row["summary"]
        ],
        "duplicate_topic_ids_by_field": duplicates,
        "invalid_topic_url_ids": bad_urls,
        "residual_html_topic_ids": markup_ids,
        "topic_url_validation": "Local URL format and uniqueness checks.",
        "checks": checks,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "validation_report.json", report)
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Validation failed: " + ", ".join(failed))

    write_json(output_dir / "medlineplus_topics_en.json", rows)
    with (output_dir / "medlineplus_topics_en.csv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(
            {key: json.dumps(value, ensure_ascii=False) if isinstance(value, list) else value
             for key, value in row.items()}
            for row in rows
        )
    print(f"Exported {len(rows)} English topics ({missing['summary']} missing summaries).")


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("xml", type=Path, help="Path to the downloaded Health Topics XML")
    cli.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    args = cli.parse_args()
    try:
        clean(args.xml, args.output_dir)
    except (ValueError, OSError, ET.ParseError) as exc:
        cli.exit(1, f"{exc}\n")
