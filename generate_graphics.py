"""Generate Assignment 3 SVG figures."""

from __future__ import annotations

import csv
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read_rows() -> list[dict[str, str]]:
    with (ROOT / "summary.csv").open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def chart(rows: list[dict[str, str]], key: str, title: str, ylabel: str, path: Path) -> None:
    width, height = 1200, 680
    left, top, right, bottom = 85, 65, 30, 190
    plot_w, plot_h = width - left - right, height - top - bottom
    values = [float(row[key]) for row in rows if row[key]]
    maximum = max(values) if values else 1.0
    bar_w = plot_w / max(len(values), 1)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<style>text{font-family:Arial;font-size:12px;fill:#17202a}.title{font-size:21px;font-weight:bold}.axis{stroke:#17202a;stroke-width:2}.grid{stroke:#d9e0e6}.bar{fill:#357edd}</style>',
        f'<text x="{width/2}" y="32" text-anchor="middle" class="title">{html.escape(title)}</text>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_h}" class="axis"/>',
        f'<line x1="{left}" y1="{top+plot_h}" x2="{left+plot_w}" y2="{top+plot_h}" class="axis"/>',
        f'<text x="20" y="{top+plot_h/2}" transform="rotate(-90 20 {top+plot_h/2})" text-anchor="middle">{html.escape(ylabel)}</text>',
    ]
    for i in range(6):
        fraction = i / 5
        y = top + plot_h - fraction * plot_h
        lines.append(f'<line x1="{left}" y1="{y:.2f}" x2="{left+plot_w}" y2="{y:.2f}" class="grid"/>')
        lines.append(f'<text x="{left-8}" y="{y+4:.2f}" text-anchor="end">{maximum*fraction:.2f}</text>')
    for i, row in enumerate(rows):
        value = float(row[key])
        x = left + i * bar_w + bar_w * 0.15
        bar_height = value / maximum * plot_h
        y = top + plot_h - bar_height
        label = f'{row["method"]} n={row["size"]} t={row["threads"]}'
        lines.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w*0.7:.2f}" height="{bar_height:.2f}" class="bar"><title>{html.escape(label)}: {value:.6f}</title></rect>')
        lx, ly = x + bar_w * 0.35, top + plot_h + 18
        lines.append(f'<text x="{lx:.2f}" y="{ly}" transform="rotate(62 {lx:.2f} {ly})">{html.escape(label)}</text>')
    lines.extend([
        f'<text x="{left+plot_w/2}" y="{height-18}" text-anchor="middle">Configuration</text>',
        "</svg>",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    rows = read_rows()
    chart(rows, "median_ms", "Assignment 3 runtime", "Median time (ms)", ROOT / "runtime.svg")
    chart(rows, "speedup", "Assignment 3 speedup", "Speedup relative to sequential", ROOT / "speedup.svg")
    chart(rows, "peak_memory_mib", "Assignment 3 memory", "Peak traced memory (MiB)", ROOT / "memory.svg")


if __name__ == "__main__":
    main()
