"""Validate PubMed article CSV and prepare JSONL input for LLM extraction."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


REQUIRED_FIELDS = ["pmid", "title", "abstract", "doi", "journal", "year"]


def read_articles(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [field for field in REQUIRED_FIELDS if field not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"Missing required columns in {path}: {', '.join(missing)}")
        articles: list[dict[str, str]] = []
        seen: set[str] = set()
        for row in reader:
            pmid = (row.get("pmid") or "").strip()
            if not pmid:
                continue
            if pmid in seen:
                continue
            seen.add(pmid)
            article = {field: (row.get(field) or "").strip() for field in REQUIRED_FIELDS}
            article["source_database"] = (row.get("source_database") or "PubMed").strip()
            articles.append(article)
    return articles


def write_jsonl(articles: list[dict[str, str]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        for article in articles:
            handle.write(json.dumps(article, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    articles = read_articles(args.input)
    if not articles:
        raise ValueError(f"No valid articles found in {args.input}")
    write_jsonl(articles, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
