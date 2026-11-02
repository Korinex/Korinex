#!/usr/bin/env python3
"""Generate a Catppuccin-matched top-languages donut chart.

Reads public repository language bytes from the GitHub REST API and writes
dist/languages.svg. Designed to run inside GitHub Actions, but also works
locally without a token for public data (subject to API rate limits).
"""

from __future__ import annotations

import json
import math
import os
import urllib.request
from pathlib import Path

USERNAME = os.environ.get("PROFILE_USERNAME", "Korinex")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = Path(os.environ.get("LANGUAGES_OUT", "dist/languages.svg"))

# Catppuccin Mocha accents, chosen to match the terminal header.
COLORS = {
    "TypeScript": "#89b4fa",
    "Python": "#a6e3a1",
    "Jupyter Notebook": "#fab387",
    "CSS": "#cba6f7",
    "JavaScript": "#f9e2af",
    "HTML": "#f38ba8",
    "Shell": "#94e2d5",
    "C": "#89dceb",
    "C++": "#f5c2e7",
    "Java": "#eba0ac",
    "Go": "#74c7ec",
    "Rust": "#f2cdcd",
}
FALLBACK = ["#b4befe", "#94e2d5", "#f5c2e7", "#89dceb", "#eba0ac", "#74c7ec"]
BG = "#1e1e2e"
SURFACE = "#313244"
TEXT = "#cdd6f4"
SUBTLE = "#a6adc8"
MUTED = "#6c7086"


def api(url: str) -> object:
    headers = {"User-Agent": "profile-languages-chart", "Accept": "application/vnd.github+json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def collect() -> dict[str, int]:
    totals: dict[str, int] = {}
    page = 1
    while True:
        repos = api(f"https://api.github.com/users/{USERNAME}/repos?per_page=100&page={page}&type=owner")
        if not repos:
            break
        for repo in repos:
            if repo.get("fork"):
                continue
            langs = api(repo["languages_url"])
            for name, size in langs.items():
                totals[name] = totals.get(name, 0) + int(size)
        if len(repos) < 100:
            break
        page += 1
    if not totals:
        raise RuntimeError("No language data found.")
    return totals


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_svg(totals: dict[str, int]) -> str:
    items = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    top = items[:5]
    other = sum(v for _, v in items[5:])
    if other:
        top.append(("Other", other))
    total = sum(v for _, v in top) or 1

    cx, cy, r = 86, 104, 58
    circumference = 2 * math.pi * r
    offset = 0.0
    rings = []
    legend = []
    for i, (name, value) in enumerate(top):
        color = COLORS.get(name, FALLBACK[i % len(FALLBACK)])
        frac = value / total
        length = frac * circumference
        # Small gap between segments for readability.
        dash = max(length - 2, 0.5)
        rings.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="18" '
            f'stroke-dasharray="{dash:.3f} {circumference - dash:.3f}" stroke-dashoffset="{-offset:.3f}" '
            f'transform="rotate(-90 {cx} {cy})" />'
        )
        offset += length
        pct = frac * 100
        y = 52 + i * 24
        label = "Jupyter" if name == "Jupyter Notebook" else name
        legend.append(
            f'<rect x="178" y="{y - 10}" width="10" height="10" rx="2" fill="{color}" />'
            f'<text x="196" y="{y}" class="t" font-size="12.5">{esc(label)}</text>'
            f'<text x="324" y="{y}" class="t" font-size="12.5" text-anchor="end" fill="{SUBTLE}">{pct:.1f}%</text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 340 195" width="340" height="195" role="img" aria-label="Top languages across {esc(USERNAME)}'s public repositories">
  <defs>
    <style>
      .t {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; fill: {TEXT}; }}
      .m {{ font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace; }}
    </style>
  </defs>
  <rect x="1" y="1" width="338" height="193" rx="10" fill="{BG}" stroke="{SURFACE}" stroke-width="2" />
  <text x="20" y="28" class="t" font-size="15" font-weight="700">Top languages</text>
  <text x="320" y="28" class="m" font-size="10.5" fill="{MUTED}" text-anchor="end">public repos · by bytes</text>
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{SURFACE}" stroke-width="18" />
  {''.join(rings)}
  <text x="{cx}" y="{cy - 2}" class="t" font-size="18" font-weight="700" text-anchor="middle">{len(items)}</text>
  <text x="{cx}" y="{cy + 16}" class="m" font-size="10" fill="{SUBTLE}" text-anchor="middle">languages</text>
  {''.join(legend)}
</svg>'''


def main() -> None:
    totals = collect()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_svg(totals), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
