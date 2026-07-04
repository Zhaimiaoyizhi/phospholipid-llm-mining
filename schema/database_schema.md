# MVP Database Schema

This project builds a SQLite database at `results/phospholipid_protein.sqlite`.

## `articles`

Raw literature metadata downloaded from PubMed.

| Column | Meaning |
| --- | --- |
| `pmid` | PubMed identifier, primary key |
| `title` | Article title |
| `abstract` | PubMed abstract text |
| `doi` | DOI if present in PubMed metadata |
| `journal` | Journal title |
| `year` | Publication year |
| `source_database` | Literature database source, currently `PubMed` |

## `extraction_runs`

One row per extraction run.

| Column | Meaning |
| --- | --- |
| `run_id` | Workflow run identifier |
| `run_time` | UTC creation time |
| `llm_provider` | LLM API family |
| `llm_model` | Model name |
| `prompt_version` | Prompt/schema version |
| `temperature` | LLM temperature |
| `mode` | `api` or `mock` |

## `phospholipid_protein_records`

Core wide table for extracted evidence records. The field set follows the workbook `受磷脂调控蛋白质数据库_字段设计清单_v0.4_记录模板与说明.xlsx`, with MVP emphasis on title/abstract-supported extraction.

Important principles:

- `*_reported` fields preserve source wording.
- Standard identifiers such as `uniprot_id` are blank unless explicitly stated.
- `original_evidence_sentence` is required for audit; missing evidence is flagged by `ambiguity_flag`.
- `review_status` defaults to `pending` because LLM output requires human curation.

## `llm_raw_outputs`

Audit index for raw LLM responses.

| Column | Meaning |
| --- | --- |
| `run_id` | Workflow run identifier |
| `pmid` | PubMed identifier |
| `raw_output_path` | Saved raw response path |
| `parse_status` | `success` or `failed` |
| `error_message` | API or parsing error text |
