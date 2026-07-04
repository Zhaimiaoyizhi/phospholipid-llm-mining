import os

configfile: "config/config.yaml"

RUN_ID = config["project"]["name"] + "_" + config["project"]["prompt_version"]
PATHS = config["paths"]
LLM = config["llm"]
PUBMED = config["pubmed"]

rule all:
    input:
        PATHS["summary_json"],
        PATHS["sqlite_db"],
        PATHS["normalized_csv"],
        PATHS["failed_csv"]

rule fetch_pubmed:
    input:
        pmids=PATHS["pmids"]
    output:
        articles=PATHS["articles_csv"]
    shell:
        """
        python scripts/fetch_pubmed.py \
          --pmids {input.pmids} \
          --output {output.articles} \
          --email "{PUBMED[email]}" \
          --tool "{PUBMED[tool]}" \
          --batch-size {PUBMED[batch_size]} \
          --timeout {PUBMED[timeout_seconds]}
        """

rule prepare_inputs:
    input:
        articles=PATHS["articles_csv"]
    output:
        prepared=PATHS["prepared_articles"]
    shell:
        """
        python scripts/prepare_inputs.py \
          --input {input.articles} \
          --output {output.prepared}
        """

rule llm_extract:
    input:
        prepared=PATHS["prepared_articles"],
        prompt="prompts/extraction_prompt.md"
    output:
        llm_raw=PATHS["llm_raw_jsonl"]
    params:
        raw_dir=PATHS["raw_llm_dir"],
        base_url=os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1"),
        model=os.environ.get("LLM_MODEL", "gpt-4.1-mini"),
        mode=LLM["mode"],
        api_key_env=LLM["api_key_env"],
        temperature=LLM["temperature"],
        max_retries=LLM["max_retries"],
        timeout=LLM["timeout_seconds"],
        mock_dir=LLM["mock_dir"]
    shell:
        """
        python scripts/llm_extract.py \
          --input {input.prepared} \
          --prompt {input.prompt} \
          --raw-output-dir {params.raw_dir} \
          --output {output.llm_raw} \
          --mode {params.mode} \
          --base-url "{params.base_url}" \
          --api-key-env {params.api_key_env} \
          --model "{params.model}" \
          --temperature {params.temperature} \
          --max-retries {params.max_retries} \
          --timeout {params.timeout} \
          --mock-dir {params.mock_dir}
        """

rule normalize_records:
    input:
        llm_raw=PATHS["llm_raw_jsonl"]
    output:
        records=PATHS["normalized_csv"],
        failed=PATHS["failed_csv"]
    shell:
        """
        python scripts/normalize_records.py \
          --input {input.llm_raw} \
          --output {output.records} \
          --failed-output {output.failed} \
          --run-id {RUN_ID}
        """

rule build_database:
    input:
        articles=PATHS["articles_csv"],
        records=PATHS["normalized_csv"],
        raw_llm=PATHS["llm_raw_jsonl"]
    output:
        sqlite_db=PATHS["sqlite_db"]
    params:
        provider=LLM["provider"],
        model=os.environ.get("LLM_MODEL", "gpt-4.1-mini"),
        prompt_version=config["project"]["prompt_version"],
        temperature=LLM["temperature"],
        mode=LLM["mode"]
    shell:
        """
        python scripts/build_database.py \
          --articles {input.articles} \
          --records {input.records} \
          --raw-llm {input.raw_llm} \
          --output {output.sqlite_db} \
          --run-id {RUN_ID} \
          --provider {params.provider} \
          --model "{params.model}" \
          --prompt-version {params.prompt_version} \
          --temperature {params.temperature} \
          --mode {params.mode}
        """

rule make_summary:
    input:
        articles=PATHS["articles_csv"],
        records=PATHS["normalized_csv"],
        failed=PATHS["failed_csv"],
        sqlite_db=PATHS["sqlite_db"]
    output:
        summary=PATHS["summary_json"]
    shell:
        """
        python scripts/make_summary.py \
          --articles {input.articles} \
          --records {input.records} \
          --failed {input.failed} \
          --output {output.summary} \
          --run-id {RUN_ID}
        """
