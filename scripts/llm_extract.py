"""Extract phospholipid-protein regulation records with an LLM API."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


def resolve_env_expr(value: str) -> str:
    match = re.fullmatch(r"\$\{([A-Za-z_][A-Za-z0-9_]*):-([^}]*)\}", value)
    if match:
        name, default = match.groups()
        return os.environ.get(name, default)
    return os.environ.get(value[1:], "") if value.startswith("$") else value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                records.append(json.loads(stripped))
    return records


def load_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def build_user_prompt(article: dict[str, Any], template: str) -> str:
    return template.format(
        pmid=article.get("pmid", ""),
        title=article.get("title", ""),
        abstract=article.get("abstract", ""),
        doi=article.get("doi", ""),
        journal=article.get("journal", ""),
        year=article.get("year", ""),
    )


def extract_json_text(content: str) -> Any:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def call_chat_completion(
    base_url: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    timeout: int,
) -> dict[str, Any]:
    url = base_url.rstrip("/") + "/chat/completions"
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def content_from_response(response: dict[str, Any]) -> str:
    return response["choices"][0]["message"]["content"]


def load_mock_response(mock_dir: Path, pmid: str) -> dict[str, Any]:
    path = mock_dir / f"{pmid}.json"
    if not path.exists():
        return {"choices": [{"message": {"content": "[]"}}], "mock_missing": str(path)}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--prompt", required=True, type=Path)
    parser.add_argument("--raw-output-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--mode", choices=["api", "mock"], default="api")
    parser.add_argument("--base-url", default="https://api.openai.com/v1")
    parser.add_argument("--api-key-env", default="LLM_API_KEY")
    parser.add_argument("--model", default="gpt-4.1-mini")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--mock-dir", type=Path, default=Path("examples/mock_llm_outputs"))
    args = parser.parse_args(argv)

    articles = read_jsonl(args.input)
    template = load_prompt(args.prompt)
    base_url = resolve_env_expr(args.base_url)
    model = resolve_env_expr(args.model)
    api_key = os.environ.get(args.api_key_env, "")
    if args.mode == "api" and not api_key:
        raise RuntimeError(f"Missing API key environment variable: {args.api_key_env}")

    system_prompt = (
        "You are a careful biomedical literature extraction assistant. "
        "Extract only information explicitly supported by the provided title and abstract."
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as out:
        for article in articles:
            pmid = str(article.get("pmid", "")).strip()
            raw_path = args.raw_output_dir / f"{pmid}.json"
            user_prompt = build_user_prompt(article, template)
            response: dict[str, Any] | None = None
            error_message = ""
            parse_status = "success"
            records: Any = []

            for attempt in range(args.max_retries + 1):
                try:
                    if args.mode == "mock":
                        response = load_mock_response(args.mock_dir, pmid)
                    else:
                        response = call_chat_completion(
                            base_url=base_url,
                            api_key=api_key,
                            model=model,
                            system_prompt=system_prompt,
                            user_prompt=user_prompt,
                            temperature=args.temperature,
                            timeout=args.timeout,
                        )
                    content = content_from_response(response)
                    records = extract_json_text(content)
                    if not isinstance(records, list):
                        raise ValueError("LLM output must be a JSON array")
                    break
                except Exception as exc:  # noqa: BLE001 - preserve API/parse errors for audit.
                    error_message = str(exc)
                    parse_status = "failed"
                    if attempt >= args.max_retries:
                        records = []
                    else:
                        time.sleep(2**attempt)

            raw_payload = {
                "pmid": pmid,
                "mode": args.mode,
                "model": model,
                "parse_status": parse_status,
                "error_message": error_message,
                "response": response,
            }
            write_json(raw_path, raw_payload)
            out.write(
                json.dumps(
                    {
                        "pmid": pmid,
                        "parse_status": parse_status,
                        "error_message": error_message,
                        "raw_output_path": str(raw_path).replace("\\", "/"),
                        "records": records,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
