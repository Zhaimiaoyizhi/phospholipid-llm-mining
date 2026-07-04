# Phospholipid LLM Literature Mining Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible Snakemake MVP that downloads PubMed article metadata/abstracts from PMID seeds, extracts phospholipid-regulated protein records with a real OpenAI-compatible LLM API, normalizes records, and writes CSV/SQLite results.

**Architecture:** PubMed E-utilities is the raw literature data source. Snakemake orchestrates acquisition, LLM extraction, normalization, database creation, and summary reporting. The LLM is constrained to title/abstract evidence and all raw responses are retained for audit.

**Tech Stack:** Conda, Python, Snakemake, requests, python-dotenv, pandas, SQLite, pytest.

---

### Task 1: Project Skeleton

**Files:**
- Create: `environment.yml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `config/config.yaml`
- Create: `data/input/pmids.txt`

- [x] Create a minimal Conda environment with Snakemake, Python packages, and test tools.
- [x] Create configuration for PubMed, LLM API, paths, retries, and prompt version.
- [x] Seed the MVP with a small PMID list selected from PubMed searches on phosphoinositide/protein regulation terms.

### Task 2: Workflow Scripts

**Files:**
- Create: `scripts/fetch_pubmed.py`
- Create: `scripts/prepare_inputs.py`
- Create: `scripts/llm_extract.py`
- Create: `scripts/normalize_records.py`
- Create: `scripts/build_database.py`
- Create: `scripts/make_summary.py`

- [ ] Fetch article metadata and abstracts from PubMed E-utilities.
- [ ] Validate and convert article CSV to JSONL.
- [ ] Call an OpenAI-compatible chat completion endpoint and save raw outputs.
- [ ] Normalize JSON records into a stable CSV schema.
- [ ] Build SQLite tables for articles, extraction runs, records, and raw output audit.
- [ ] Generate run-level summary JSON.

### Task 3: Prompt, Schema, and Workflow

**Files:**
- Create: `prompts/extraction_prompt.md`
- Create: `schema/database_schema.md`
- Create: `Snakefile`

- [ ] Define conservative extraction instructions: faithful to title/abstract only, no invented IDs, JSON only.
- [ ] Document the MVP SQLite schema.
- [ ] Wire scripts into Snakemake rules from raw PMID seeds to final results.

### Task 4: Tests and Documentation

**Files:**
- Create: `tests/test_normalize_records.py`
- Create: `README.md`

- [ ] Add focused tests for JSON extraction and normalization behavior.
- [ ] Document Conda setup, API environment variables, workflow commands, and outputs.
- [ ] Verify `pytest` and at least a dry-run of `snakemake` pass.
