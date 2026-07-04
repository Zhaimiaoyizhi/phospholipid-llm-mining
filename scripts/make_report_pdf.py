"""Render the Markdown project report to PDF using a local Chromium browser."""

from __future__ import annotations

import argparse
import html
import re
import subprocess
import sys
from pathlib import Path


CHROME_CANDIDATES = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
]


def inline_markdown(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', escaped)
    return escaped


def render_table(lines: list[str]) -> str:
    rows = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if all(set(cell) <= {"-", ":", " "} for cell in cells):
            continue
        rows.append(cells)
    if not rows:
        return ""
    head = "".join(f"<th>{inline_markdown(cell)}</th>" for cell in rows[0])
    body_rows = []
    for row in rows[1:]:
        body_rows.append("<tr>" + "".join(f"<td>{inline_markdown(cell)}</td>" for cell in row) + "</tr>")
    return "<table><thead><tr>" + head + "</tr></thead><tbody>" + "".join(body_rows) + "</tbody></table>"


def markdown_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    out: list[str] = []
    paragraph: list[str] = []
    code_block: list[str] | None = None
    code_lang = ""
    table_block: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            out.append("<p>" + inline_markdown(" ".join(paragraph)) + "</p>")
            paragraph = []

    def flush_table() -> None:
        nonlocal table_block
        if table_block:
            flush_paragraph()
            out.append(render_table(table_block))
            table_block = []

    for line in lines:
        stripped = line.strip()
        if code_block is not None:
            if stripped.startswith("```"):
                out.append(
                    f'<pre><code class="language-{html.escape(code_lang)}">'
                    + html.escape("\n".join(code_block))
                    + "</code></pre>"
                )
                code_block = None
                code_lang = ""
            else:
                code_block.append(line)
            continue

        if stripped.startswith("```"):
            flush_table()
            flush_paragraph()
            code_lang = stripped[3:].strip()
            code_block = []
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            table_block.append(line)
            continue
        flush_table()

        if not stripped:
            flush_paragraph()
            continue

        image = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", stripped)
        if image:
            flush_paragraph()
            alt, src = image.groups()
            out.append(
                '<figure class="report-figure">'
                f'<img src="{html.escape(src)}" alt="{html.escape(alt)}">'
                "</figure>"
            )
            continue

        heading = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            out.append(f"<h{level}>{inline_markdown(heading.group(2))}</h{level}>")
            continue

        bullet = re.match(r"^[-*]\s+(.*)$", stripped)
        if bullet:
            flush_paragraph()
            out.append(f"<ul><li>{inline_markdown(bullet.group(1))}</li></ul>")
            continue

        paragraph.append(stripped)

    flush_table()
    flush_paragraph()
    return "\n".join(out)


def wrap_html(body: str, title: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <style>
    @page {{ size: A4; margin: 22mm 19mm; }}
    * {{ box-sizing: border-box; }}
    body {{
      font-family: "Microsoft YaHei", "SimSun", "Noto Sans CJK SC", Arial, sans-serif;
      color: #111827;
      line-height: 1.72;
      font-size: 11.2pt;
    }}
    h1, h2, h3, h4 {{ line-height: 1.35; color: #0f172a; page-break-after: avoid; }}
    h1 {{ font-size: 22pt; margin: 0 0 14pt; text-align: center; }}
    h2 {{ font-size: 16pt; margin: 22pt 0 8pt; border-bottom: 1px solid #cbd5e1; padding-bottom: 4pt; }}
    h3 {{ font-size: 13pt; margin: 16pt 0 6pt; }}
    p {{ margin: 0 0 8pt; text-align: justify; }}
    a {{ color: #1d4ed8; text-decoration: none; }}
    code {{ font-family: Consolas, "Courier New", monospace; background: #f1f5f9; padding: 1px 3px; border-radius: 3px; }}
    pre {{ background: #f8fafc; border: 1px solid #cbd5e1; padding: 9pt; white-space: pre-wrap; font-size: 9pt; page-break-inside: avoid; }}
    table {{ width: 100%; border-collapse: collapse; margin: 8pt 0 12pt; font-size: 10pt; page-break-inside: avoid; }}
    th, td {{ border: 1px solid #cbd5e1; padding: 5pt 6pt; vertical-align: top; }}
    th {{ background: #e2e8f0; text-align: left; }}
    figure.report-figure {{ margin: 10pt auto 8pt; text-align: center; page-break-inside: avoid; }}
    figure.report-figure img {{ max-width: 100%; max-height: 155mm; }}
    ul {{ margin: 0 0 8pt 18pt; }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""


def find_browser(explicit: str | None) -> Path:
    if explicit:
        browser = Path(explicit)
        if browser.exists():
            return browser
        raise FileNotFoundError(f"Browser executable not found: {browser}")
    for candidate in CHROME_CANDIDATES:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Chrome or Edge executable was not found.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="docs/project_report.md")
    parser.add_argument("--html-output", default="docs/project_report.html")
    parser.add_argument("--pdf-output", default="docs/project_report.pdf")
    parser.add_argument("--browser")
    args = parser.parse_args()

    md_path = Path(args.input).resolve()
    html_path = Path(args.html_output).resolve()
    pdf_path = Path(args.pdf_output).resolve()

    markdown = md_path.read_text(encoding="utf-8")
    first_heading = next((line.strip("# ").strip() for line in markdown.splitlines() if line.startswith("# ")), md_path.stem)
    body = markdown_to_html(markdown)
    html_path.write_text(wrap_html(body, first_heading), encoding="utf-8")

    browser = find_browser(args.browser)
    command = [
        str(browser),
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        html_path.as_uri(),
    ]
    result = subprocess.run(command, check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        return result.returncode
    print(f"Wrote {pdf_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
