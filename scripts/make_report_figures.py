"""Generate lightweight SVG figures for the project report."""

from __future__ import annotations

import json
from pathlib import Path


COLORS = ["#2563eb", "#16a34a", "#dc2626", "#9333ea", "#ea580c", "#0891b2"]


def load_summary(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def svg_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def write_bar_chart(title: str, data: dict[str, int], output: Path) -> None:
    width = 900
    bar_h = 34
    gap = 16
    left = 260
    top = 80
    max_value = max(data.values()) if data else 1
    height = top + len(data) * (bar_h + gap) + 70
    rows = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="32" y="42" font-family="Arial, sans-serif" font-size="24" font-weight="700" fill="#111827">{svg_escape(title)}</text>',
    ]
    for idx, (label, value) in enumerate(data.items()):
        y = top + idx * (bar_h + gap)
        bar_w = int((width - left - 140) * value / max_value)
        color = COLORS[idx % len(COLORS)]
        rows.append(
            f'<text x="32" y="{y + 23}" font-family="Arial, sans-serif" font-size="16" fill="#374151">{svg_escape(label)}</text>'
        )
        rows.append(f'<rect x="{left}" y="{y}" width="{bar_w}" height="{bar_h}" rx="4" fill="{color}"/>')
        rows.append(
            f'<text x="{left + bar_w + 12}" y="{y + 23}" font-family="Arial, sans-serif" font-size="16" fill="#111827">{value}</text>'
        )
    rows.append("</svg>")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(rows), encoding="utf-8")


def write_qc_summary(summary: dict, output: Path) -> None:
    metrics = [
        ("PubMed articles", summary["article_count"]),
        ("Extracted records", summary["record_count"]),
        ("Failed records", summary["failed_count"]),
        ("Unique proteins", summary["unique_reported_proteins"]),
        ("Unique lipids", summary["unique_reported_lipids"]),
    ]
    width = 900
    height = 260
    card_w = 156
    gap = 18
    rows = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="32" y="42" font-family="Arial, sans-serif" font-size="24" font-weight="700" fill="#111827">Extraction QC Summary</text>',
    ]
    for idx, (label, value) in enumerate(metrics):
        x = 32 + idx * (card_w + gap)
        rows.append(f'<rect x="{x}" y="82" width="{card_w}" height="120" rx="8" fill="#f3f4f6" stroke="#d1d5db"/>')
        rows.append(
            f'<text x="{x + 18}" y="125" font-family="Arial, sans-serif" font-size="32" font-weight="700" fill="#111827">{value}</text>'
        )
        rows.append(
            f'<text x="{x + 18}" y="164" font-family="Arial, sans-serif" font-size="14" fill="#4b5563">{svg_escape(label)}</text>'
        )
    rows.append("</svg>")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(rows), encoding="utf-8")


def write_flowchart(output: Path) -> None:
    width = 980
    height = 360
    boxes = [
        (40, 120, "PMID list", "data/input/pmids.txt"),
        (220, 120, "PubMed fetch", "metadata + abstract"),
        (420, 120, "LLM extraction", "JSON evidence records"),
        (620, 120, "Normalize", "CSV + failed table"),
        (800, 120, "Database", "SQLite + summary"),
    ]
    rows = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#374151"/></marker></defs>',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="32" y="42" font-family="Arial, sans-serif" font-size="24" font-weight="700" fill="#111827">Workflow Data Flow</text>',
    ]
    for idx, (x, y, title, subtitle) in enumerate(boxes):
        rows.append(f'<rect x="{x}" y="{y}" width="145" height="95" rx="8" fill="#eff6ff" stroke="#60a5fa" stroke-width="2"/>')
        rows.append(f'<text x="{x + 16}" y="{y + 38}" font-family="Arial, sans-serif" font-size="17" font-weight="700" fill="#111827">{title}</text>')
        rows.append(f'<text x="{x + 16}" y="{y + 66}" font-family="Arial, sans-serif" font-size="13" fill="#4b5563">{subtitle}</text>')
        if idx < len(boxes) - 1:
            x2 = boxes[idx + 1][0]
            rows.append(f'<line x1="{x + 145}" y1="{y + 48}" x2="{x2 - 16}" y2="{y + 48}" stroke="#374151" stroke-width="2" marker-end="url(#arrow)"/>')
    rows.append('<text x="40" y="270" font-family="Arial, sans-serif" font-size="14" fill="#374151">Raw LLM responses are stored in cache/raw_llm_outputs/ for audit and reuse.</text>')
    rows.append("</svg>")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(rows), encoding="utf-8")


def main() -> None:
    summary = load_summary(Path("results/extraction_summary.json"))
    fig_dir = Path("docs/figures")
    write_flowchart(fig_dir / "workflow_flowchart.svg")
    write_qc_summary(summary, fig_dir / "extraction_qc_summary.svg")
    write_bar_chart("Evidence Level Distribution", summary["evidence_level_counts"], fig_dir / "evidence_level_counts.svg")
    write_bar_chart(
        "Regulation Relationship Distribution",
        summary["regulation_relationship_counts"],
        fig_dir / "regulation_relationship_counts.svg",
    )


if __name__ == "__main__":
    main()
