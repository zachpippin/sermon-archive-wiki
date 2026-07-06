from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import shutil
from typing import Iterable


DATE_TITLE_RE = re.compile(r"(?P<date>\d{4}-\d{2}-\d{2})[_ -]+(?P<title>.+)")


def now_stamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"['\u2019]", "", value)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "untitled"


def title_from_filename(path: Path) -> tuple[str, str]:
    stem = path.stem.strip()
    match = DATE_TITLE_RE.match(stem)
    if match:
        date = match.group("date")
        title = match.group("title")
    else:
        date = ""
        title = stem
    title = title.replace("_", " ").replace("-", " ")
    title = re.sub(r"\s+", " ", title).strip()
    return date, smart_title(title)


def normalize_date(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if re.match(r"^\d{4}-\d{2}-\d{2}$", text):
        return text
    for fmt in ("%m/%d/%y", "%m/%d/%Y", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return text


def smart_title(value: str) -> str:
    value = value.strip()
    if not value:
        return "Untitled Sermon"
    if any(char.islower() for char in value):
        return value
    return value.title()


def split_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    parts = re.split(r"\s*(?:;|\|)\s*", text)
    if len(parts) == 1:
        parts = re.split(r"\s*,\s*", text)
    return [part.strip() for part in parts if part.strip()]


def relative_display(path: Path, base: Path | None = None) -> str:
    try:
        if base:
            return str(path.resolve().relative_to(base.resolve()))
    except ValueError:
        pass
    return str(path)


def resolve_executable(name: str) -> str | None:
    return shutil.which(name)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def media_uri(source: str) -> str:
    """Return a browser-friendly URI for a URL or local media path."""
    text = source.strip()
    if text.startswith(("http://", "https://", "file://")):
        return text
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    try:
        return path.resolve().as_uri()
    except ValueError:
        return text


def wikilink(target: str, label: str | None = None) -> str:
    target = clean_wikilink_part(target)
    label = clean_wikilink_part(label or "")
    if label and label != target:
        return f"[[{target}|{label}]]"
    return f"[[{target}]]"


def clean_wikilink_part(value: str) -> str:
    text = value.strip().replace("|", " ")
    return re.sub(r"\s+", " ", text).strip()


def page_stem(date: str, title: str) -> str:
    if date:
        return f"{date} - {safe_filename(title)}"
    return safe_filename(title)


def safe_filename(value: str) -> str:
    value = re.sub(r"[/\\:*?\"<>|#\[\]^]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value or "Untitled Sermon"


def markdown_table_row(values: Iterable[object]) -> str:
    escaped = [str(value).replace("|", "\\|").replace("\n", " ") for value in values]
    return "| " + " | ".join(escaped) + " |"
