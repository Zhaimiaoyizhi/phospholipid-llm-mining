"""Build the MVP SQLite database from workflow outputs."""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from normalize_records import OUTPUT_FIELDS


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def create_tables(conn: sqlite3.Connection, record_fields: list[str]) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS articles;
        DROP TABLE IF EXISTS extraction_runs;
        DROP TABLE IF EXISTS phospholipid_protein_records;
        DROP TABLE IF EXISTS llm_raw_outputs;

        CREATE TABLE articles (
            pmid TEXT PRIMARY KEY,
            title TEXT,
            abstract TEXT,
            doi TEXT,
            journal TEXT,
            year TEXT,
            source_database TEXT
        );

        CREATE TABLE extraction_runs (
            run_id TEXT PRIMARY KEY,
            run_time TEXT,
            llm_provider TEXT,
            llm_model TEXT,
            prompt_version TEXT,
            temperature REAL,
            mode TEXT
        );

        CREATE TABLE llm_raw_outputs (
            run_id TEXT,
            pmid TEXT,
            raw_output_path TEXT,
            parse_status TEXT,
            error_message TEXT,
            PRIMARY KEY (run_id, pmid)
        );
        """
    )
    columns = ",\n            ".join(f"{field} TEXT" for field in record_fields)
    conn.execute(
        f"""
        CREATE TABLE phospholipid_protein_records (
            {columns},
            PRIMARY KEY (record_id)
        );
        """
    )


def insert_articles(conn: sqlite3.Connection, rows: list[dict[str, str]]) -> None:
    fields = ["pmid", "title", "abstract", "doi", "journal", "year", "source_database"]
    conn.executemany(
        f"INSERT INTO articles ({', '.join(fields)}) VALUES ({', '.join('?' for _ in fields)})",
        [tuple(row.get(field, "") for field in fields) for row in rows],
    )


def insert_run(
    conn: sqlite3.Connection,
    run_id: str,
    provider: str,
    model: str,
    prompt_version: str,
    temperature: float,
    mode: str,
) -> None:
    conn.execute(
        """
        INSERT INTO extraction_runs
        (run_id, run_time, llm_provider, llm_model, prompt_version, temperature, mode)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            datetime.now(UTC).replace(microsecond=0).isoformat(),
            provider,
            model,
            prompt_version,
            temperature,
            mode,
        ),
    )


def insert_records(conn: sqlite3.Connection, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    fields = list(rows[0].keys())
    placeholders = ", ".join("?" for _ in fields)
    conn.executemany(
        f"INSERT INTO phospholipid_protein_records ({', '.join(fields)}) VALUES ({placeholders})",
        [tuple(row.get(field, "") for field in fields) for row in rows],
    )


def insert_raw_outputs(conn: sqlite3.Connection, run_id: str, rows: list[dict[str, Any]]) -> None:
    conn.executemany(
        """
        INSERT INTO llm_raw_outputs
        (run_id, pmid, raw_output_path, parse_status, error_message)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (
                run_id,
                str(row.get("pmid", "")),
                str(row.get("raw_output_path", "")),
                str(row.get("parse_status", "")),
                str(row.get("error_message", "")),
            )
            for row in rows
        ],
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--articles", required=True, type=Path)
    parser.add_argument("--records", required=True, type=Path)
    parser.add_argument("--raw-llm", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--provider", default="openai_compatible")
    parser.add_argument("--model", default="")
    parser.add_argument("--prompt-version", default="")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--mode", default="api")
    args = parser.parse_args(argv)

    articles = read_csv(args.articles)
    records = read_csv(args.records)
    raw_rows = read_jsonl(args.raw_llm)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        args.output.unlink()
    with sqlite3.connect(args.output) as conn:
        create_tables(conn, list(records[0].keys()) if records else OUTPUT_FIELDS)
        insert_articles(conn, articles)
        insert_run(
            conn,
            run_id=args.run_id,
            provider=args.provider,
            model=args.model,
            prompt_version=args.prompt_version,
            temperature=args.temperature,
            mode=args.mode,
        )
        insert_records(conn, records)
        insert_raw_outputs(conn, args.run_id, raw_rows)
        conn.commit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
