"""Normalize LLM extraction JSON into a stable tabular schema."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


OUTPUT_FIELDS = [
    "record_id",
    "run_id",
    "pmid",
    "protein_name_reported",
    "protein_name_standard",
    "gene_symbol",
    "uniprot_id",
    "organism",
    "protein_type",
    "physiological_function",
    "lipid_name_reported",
    "lipid_name_standard",
    "lipid_class",
    "headgroup",
    "phosphorylation_position",
    "acyl_chain_if_reported",
    "regulation_relationship",
    "direct_or_indirect",
    "effect_direction",
    "functional_effect",
    "mechanism_summary",
    "cellular_context",
    "membrane_compartment",
    "site_resolution_level",
    "binding_domain",
    "residue_reported",
    "lipid_moiety_bound",
    "lipid_headgroup_detail",
    "mutation_tested",
    "mutation_effect",
    "membrane_localization_type",
    "subcellular_location",
    "lipid_dependency",
    "localization_evidence",
    "disease_name",
    "is_lipid_regulation_related",
    "figure_or_table",
    "original_evidence_sentence",
    "experimental_method",
    "quantitative_value",
    "evidence_level",
    "review_status",
    "llm_confidence",
    "ambiguity_flag",
    "curator_note",
    "created_at",
]

CONTROLLED_VALUES = {
    "regulation_relationship": {
        "direct_binding",
        "membrane_recruitment",
        "activation",
        "inhibition",
        "gating",
        "conformational_change",
        "stabilization",
        "complex_assembly",
        "membrane_partitioning",
        "membrane_property_mediated",
        "binding_only",
        "unknown",
    },
    "direct_or_indirect": {"direct", "indirect", "unclear", "unknown"},
    "effect_direction": {
        "activation",
        "inhibition",
        "recruitment",
        "stabilization",
        "destabilization",
        "gating",
        "binding_only",
        "unknown",
    },
    "site_resolution_level": {
        "atomic_structure",
        "mutagenesis_supported",
        "domain_level",
        "lipid_species_only",
        "predicted",
        "unknown",
    },
    "membrane_localization_type": {
        "integral_transmembrane",
        "peripheral_lipid_binding",
        "lipid_binding_domain_mediated",
        "lipidation_mediated",
        "electrostatic_patch_mediated",
        "amphipathic_helix_mediated",
        "raft_partitioning",
        "unknown",
    },
    "evidence_level": {"A", "B", "C", "D", "E", "unknown"},
    "review_status": {"pending", "reviewed", "rejected"},
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def clean_scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return " ".join(str(value).split())


def normalize_controlled(field: str, value: Any) -> str:
    text = clean_scalar(value)
    if not text:
        return "unknown" if "unknown" in CONTROLLED_VALUES[field] else ""
    if field == "evidence_level":
        upper = text.strip().upper()
        return upper if upper in CONTROLLED_VALUES[field] else "unknown"
    normalized = text.strip().lower().replace(" ", "_").replace("-", "_")
    return normalized if normalized in CONTROLLED_VALUES[field] else "unknown"


def normalize_boolish(value: Any) -> str:
    text = clean_scalar(value).lower()
    if text in {"true", "yes", "y", "1"}:
        return "true"
    if text in {"false", "no", "n", "0"}:
        return "false"
    if text in {"unknown", "unclear", ""}:
        return "unknown"
    return "unknown"


def normalize_record(raw: dict[str, Any], run_id: str, pmid: str, index: int) -> dict[str, str]:
    created_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    row = {field: "" for field in OUTPUT_FIELDS}
    row.update(
        {
            "record_id": f"REC{index:06d}",
            "run_id": run_id,
            "pmid": pmid,
            "created_at": created_at,
            "review_status": "pending",
        }
    )
    for field in OUTPUT_FIELDS:
        if field in {"record_id", "run_id", "pmid", "created_at"}:
            continue
        if field in CONTROLLED_VALUES:
            row[field] = normalize_controlled(field, raw.get(field))
        elif field == "is_lipid_regulation_related":
            row[field] = normalize_boolish(raw.get(field))
        else:
            row[field] = clean_scalar(raw.get(field))

    if not row["original_evidence_sentence"]:
        row["ambiguity_flag"] = "missing_evidence_sentence"
    elif not row["ambiguity_flag"]:
        row["ambiguity_flag"] = "false"
    if not row["llm_confidence"]:
        row["llm_confidence"] = "unknown"
    return row


def normalize_rows(raw_rows: list[dict[str, Any]], run_id: str) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    normalized: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []
    record_index = 1
    for raw_row in raw_rows:
        pmid = clean_scalar(raw_row.get("pmid"))
        if raw_row.get("parse_status") != "success":
            failed.append(
                {
                    "pmid": pmid,
                    "stage": "llm_extract",
                    "error_message": clean_scalar(raw_row.get("error_message")),
                    "raw_output_path": clean_scalar(raw_row.get("raw_output_path")),
                }
            )
            continue
        records = raw_row.get("records") or []
        if not isinstance(records, list):
            failed.append(
                {
                    "pmid": pmid,
                    "stage": "normalize_records",
                    "error_message": "records is not a list",
                    "raw_output_path": clean_scalar(raw_row.get("raw_output_path")),
                }
            )
            continue
        for record in records:
            if not isinstance(record, dict):
                failed.append(
                    {
                        "pmid": pmid,
                        "stage": "normalize_records",
                        "error_message": "record is not an object",
                        "raw_output_path": clean_scalar(raw_row.get("raw_output_path")),
                    }
                )
                continue
            normalized.append(normalize_record(record, run_id, pmid, record_index))
            record_index += 1
    return normalized, failed


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--failed-output", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)

    raw_rows = read_jsonl(args.input)
    normalized, failed = normalize_rows(raw_rows, run_id=args.run_id)
    write_csv(args.output, OUTPUT_FIELDS, normalized)
    write_csv(args.failed_output, ["pmid", "stage", "error_message", "raw_output_path"], failed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
