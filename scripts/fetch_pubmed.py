"""Fetch article metadata and abstracts from PubMed E-utilities."""

from __future__ import annotations

import argparse
import csv
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


EUTILS_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def read_pmids(path: Path) -> list[str]:
    pmids: list[str] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not stripped.isdigit():
            raise ValueError(f"Invalid PMID in {path}: {stripped!r}")
        pmids.append(stripped)
    return list(dict.fromkeys(pmids))


def text_or_empty(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return " ".join("".join(node.itertext()).split())


def first_text(article: ET.Element, path: str) -> str:
    return text_or_empty(article.find(path))


def get_doi(article: ET.Element) -> str:
    for article_id in article.findall(".//ArticleId"):
        if article_id.attrib.get("IdType") == "doi":
            return text_or_empty(article_id)
    return ""


def get_abstract(article: ET.Element) -> str:
    parts = []
    for node in article.findall(".//Abstract/AbstractText"):
        label = node.attrib.get("Label")
        text = text_or_empty(node)
        if not text:
            continue
        parts.append(f"{label}: {text}" if label else text)
    return " ".join(parts)


def get_year(article: ET.Element) -> str:
    return (
        first_text(article, ".//JournalIssue/PubDate/Year")
        or first_text(article, ".//JournalIssue/PubDate/MedlineDate")[:4]
        or first_text(article, ".//ArticleDate/Year")
    )


def parse_pubmed_xml(xml_text: str) -> list[dict[str, str]]:
    root = ET.fromstring(xml_text)
    rows: list[dict[str, str]] = []
    for article in root.findall(".//PubmedArticle"):
        pmid = first_text(article, ".//MedlineCitation/PMID")
        rows.append(
            {
                "pmid": pmid,
                "title": first_text(article, ".//ArticleTitle"),
                "abstract": get_abstract(article),
                "doi": get_doi(article),
                "journal": first_text(article, ".//Journal/Title"),
                "year": get_year(article),
                "source_database": "PubMed",
            }
        )
    return rows


def fetch_batch(pmids: list[str], email: str, tool: str, timeout: int) -> str:
    query = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
        "tool": tool,
    }
    if email:
        query["email"] = email
    url = EUTILS_EFETCH + "?" + urllib.parse.urlencode(query)
    with urlopen(url, timeout=timeout) as response:
        return response.read().decode("utf-8")


def fetch_records(
    pmids: list[str],
    email: str,
    tool: str,
    batch_size: int,
    timeout: int,
) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for start in range(0, len(pmids), batch_size):
        batch = pmids[start : start + batch_size]
        try:
            xml_text = fetch_batch(batch, email=email, tool=tool, timeout=timeout)
        except URLError as exc:
            raise RuntimeError(f"Failed to fetch PubMed batch {batch}: {exc}") from exc
        records.extend(parse_pubmed_xml(xml_text))
        time.sleep(0.34)
    return records


def write_csv(rows: list[dict[str, str]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = ["pmid", "title", "abstract", "doi", "journal", "year", "source_database"]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pmids", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--email", default="")
    parser.add_argument("--tool", default="phospholipid-llm-mining")
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args(argv)

    pmids = read_pmids(args.pmids)
    if not pmids:
        raise ValueError(f"No PMIDs found in {args.pmids}")
    rows = fetch_records(
        pmids,
        email=args.email,
        tool=args.tool,
        batch_size=args.batch_size,
        timeout=args.timeout,
    )
    found = {row["pmid"] for row in rows if row.get("pmid")}
    missing = [pmid for pmid in pmids if pmid not in found]
    if missing:
        print(f"Warning: PubMed did not return PMIDs: {', '.join(missing)}", file=sys.stderr)
    write_csv(rows, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
