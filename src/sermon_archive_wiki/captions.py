from __future__ import annotations

from pathlib import Path
import re


TIMESTAMP_RE = re.compile(
    r"^\d{1,2}:\d{2}:\d{2}[,.]\d{3}\s+-->\s+\d{1,2}:\d{2}:\d{2}[,.]\d{3}"
)


def caption_text(path: Path) -> str:
    """Convert SRT/VTT captions into readable deterministic text."""
    lines: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.upper() == "WEBVTT":
            continue
        if line.isdigit():
            continue
        if TIMESTAMP_RE.match(line):
            continue
        if line.startswith(("NOTE", "STYLE", "REGION")):
            continue
        line = re.sub(r"<[^>]+>", "", line)
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(_dedupe_adjacent(lines)).strip()


def _dedupe_adjacent(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    previous = ""
    for line in lines:
        if line == previous:
            continue
        cleaned.append(line)
        previous = line
    return cleaned
