import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from normalize_records import normalize_rows  # noqa: E402


def test_normalize_rows_accepts_successful_empty_record_list():
    rows = [{"pmid": "123", "parse_status": "success", "records": []}]

    normalized, failed = normalize_rows(rows, run_id="run_v1")

    assert normalized == []
    assert failed == []


def test_normalize_rows_converts_controlled_values_and_defaults():
    rows = [
        {
            "pmid": "123",
            "parse_status": "success",
            "records": [
                {
                    "protein_name_reported": "KCNQ1",
                    "lipid_name_reported": "PIP2",
                    "regulation_relationship": "Direct binding",
                    "direct_or_indirect": "direct",
                    "effect_direction": "activation",
                    "original_evidence_sentence": "PIP2 is required for channel activity.",
                    "review_status": "pending",
                }
            ],
        }
    ]

    normalized, failed = normalize_rows(rows, run_id="run_v1")

    assert failed == []
    assert normalized[0]["record_id"] == "REC000001"
    assert normalized[0]["run_id"] == "run_v1"
    assert normalized[0]["pmid"] == "123"
    assert normalized[0]["regulation_relationship"] == "direct_binding"
    assert normalized[0]["review_status"] == "pending"
    assert normalized[0]["ambiguity_flag"] == "false"


def test_normalize_rows_flags_failed_llm_parse():
    rows = [
        {
            "pmid": "123",
            "parse_status": "failed",
            "error_message": "invalid json",
            "raw_output_path": "results/raw_llm_outputs/123.json",
        }
    ]

    normalized, failed = normalize_rows(rows, run_id="run_v1")

    assert normalized == []
    assert failed[0]["stage"] == "llm_extract"
    assert failed[0]["error_message"] == "invalid json"
