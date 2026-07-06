from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import yaml

from .models import SermonRecord
from .util import normalize_date, split_list


def records_from_catalog(path: Path) -> list[SermonRecord]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return records_from_csv(path)
    if suffix in {".yml", ".yaml"}:
        return records_from_yaml(path)
    raise ValueError(f"Unsupported catalog format: {path}")


def records_from_csv(path: Path) -> list[SermonRecord]:
    records: list[SermonRecord] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            records.append(record_from_mapping(row, path))
    return records


def records_from_yaml(path: Path) -> list[SermonRecord]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        return []
    if isinstance(data, dict):
        items = data.get("sermons", [])
    elif isinstance(data, list):
        items = data
    else:
        raise ValueError(f"{path} must contain a list or a mapping with sermons.")
    if not isinstance(items, list):
        raise ValueError(f"{path} sermons must be a list.")
    return [record_from_mapping(item, path) for item in items if isinstance(item, dict)]


def record_from_mapping(row: dict[str, Any], source: Path) -> SermonRecord:
    title = str(row.get("title") or row.get("name") or "Untitled Sermon").strip()
    transcript_path = str(row.get("transcript_path") or row.get("transcript") or row.get("source_file") or "").strip()
    audio_path = str(row.get("audio_path") or row.get("audio") or row.get("mp3_url") or "").strip()
    youtube_url = str(row.get("youtube_url") or row.get("url") or "").strip()
    sermon_page_url = str(row.get("permalink") or row.get("sermon_page_url") or "").strip()
    source_files = [str(source)]
    if transcript_path:
        source_files.append(transcript_path)
    if sermon_page_url:
        source_files.append(sermon_page_url)
    duration_seconds = duration_from_row(row)
    return SermonRecord(
        title=title,
        date=normalize_date(row.get("date") or row.get("preached_on") or row.get("upload_date") or ""),
        speaker=str(row.get("speaker") or row.get("preacher") or "").strip(),
        series=str(row.get("series") or "").strip(),
        scripture_refs=split_list(row.get("scripture_refs") or row.get("scripture") or row.get("scripture_ref")),
        topics=split_list(row.get("topics")),
        themes=split_list(row.get("themes")),
        related_sermons=split_list(row.get("related_sermons")),
        source_files=source_files,
        audio_files=[audio_path] if audio_path else [],
        transcript_path=transcript_path,
        youtube_url=youtube_url,
        duration_seconds=duration_seconds,
        transcript_status="catalog-only",
        extra={"catalog_path": str(source), "sermon_page_url": sermon_page_url},
    )


def duration_from_row(row: dict[str, Any]) -> int | None:
    raw_seconds = row.get("duration_seconds")
    if raw_seconds not in (None, ""):
        try:
            return int(float(raw_seconds))
        except (TypeError, ValueError):
            return None
    raw_minutes = row.get("duration_min")
    if raw_minutes not in (None, ""):
        try:
            return int(float(raw_minutes) * 60)
        except (TypeError, ValueError):
            return None
    return None
