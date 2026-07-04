"""Create a compact JSON summary for the extraction run."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def counter(rows: list[dict[str, str]], field: str) -> dict[str, int]:
    values = [row.get(field, "") or "blank" for row in rows]
    return dict(Counter(values))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--articles", required=True, type=Path)
    parser.add_argument("--records", required=True, type=Path)
    parser.add_argument("--failed", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)

    articles = read_csv(args.articles)
    records = read_csv(args.records)
    failed = read_csv(args.failed)
    summary = {
        "run_id": args.run_id,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "article_count": len(articles),
        "record_count": len(records),
        "failed_count": len(failed),
        "unique_pmids_with_records": len({row.get("pmid", "") for row in records if row.get("pmid")}),
        "unique_reported_proteins": len(
            {row.get("protein_name_reported", "") for row in records if row.get("protein_name_reported")}
        ),
        "unique_reported_lipids": len(
            {row.get("lipid_name_reported", "") for row in records if row.get("lipid_name_reported")}
        ),
        "evidence_level_counts": counter(records, "evidence_level"),
        "review_status_counts": counter(records, "review_status"),
        "regulation_relationship_counts": counter(records, "regulation_relationship"),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
