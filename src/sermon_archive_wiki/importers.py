from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Iterable

import yaml

from .captions import caption_text
from .catalog import records_from_catalog
from .inference import add_deterministic_inferences, fields_from_frontmatter
from .models import SermonRecord
from .util import slugify, title_from_filename
from .youtube import records_from_youtube_metadata_file


TRANSCRIPT_EXTENSIONS = {".txt", ".md"}
CAPTION_EXTENSIONS = {".srt", ".vtt"}
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".aac", ".flac"}
IGNORED_TRANSCRIPT_STEMS = {"transcription_log", "current_batch"}


def collect_records(
    transcript_dirs: Iterable[Path] = (),
    caption_dirs: Iterable[Path] = (),
    audio_dirs: Iterable[Path] = (),
    catalog_paths: Iterable[Path] = (),
    youtube_metadata_paths: Iterable[Path] = (),
    archivist_archive_dir: Path | None = None,
) -> list[SermonRecord]:
    records: list[SermonRecord] = []
    for path in catalog_paths:
        if path.exists():
            records.extend(records_from_catalog(path))
    for directory in transcript_dirs:
        records.extend(records_from_transcript_dir(directory))
    for directory in caption_dirs:
        records.extend(records_from_caption_dir(directory))
    for directory in audio_dirs:
        records.extend(records_from_audio_dir(directory))
    for path in youtube_metadata_paths:
        if path.exists():
            records.extend(records_from_youtube_metadata_file(path))
    if archivist_archive_dir and archivist_archive_dir.exists():
        records.extend(records_from_archivist_archive(archivist_archive_dir))
    return [add_deterministic_inferences(record) for record in merge_records(records)]


def records_from_transcript_dir(directory: Path) -> list[SermonRecord]:
    if not directory.exists():
        return []
    return [
        record_from_transcript_file(path)
        for path in sorted(directory.rglob("*"))
        if path.suffix.lower() in TRANSCRIPT_EXTENSIONS and not is_ignored_transcript_file(path)
    ]


def is_ignored_transcript_file(path: Path) -> bool:
    stem = re.sub(r"[\s-]+", "_", path.stem.strip().casefold())
    return stem in IGNORED_TRANSCRIPT_STEMS or stem.startswith("batch_run_")


def record_from_transcript_file(path: Path) -> SermonRecord:
    raw = path.read_text(encoding="utf-8")
    frontmatter, body = split_frontmatter(raw)
    date, title = title_from_filename(path)
    fields = fields_from_frontmatter(frontmatter)
    header = leading_metadata(body)
    clean_body = strip_leading_metadata(body) if header else body
    title = str(fields.get("title") or header.get("title") or title)
    date = str(fields.get("date") or header.get("date") or date)
    speaker = str(fields.get("speaker") or header.get("speaker") or "")
    series = str(fields.get("series") or header.get("series") or "")
    source_files = [str(path)]
    source_url = header.get("source_url")
    if source_url:
        source_files.append(source_url)
    return SermonRecord(
        title=title,
        date=date,
        speaker=speaker,
        series=series,
        scripture_refs=list(fields.get("scripture_refs") or []),
        topics=list(fields.get("topics") or []),
        themes=list(fields.get("themes") or []),
        source_files=source_files,
        transcript_path=str(path),
        transcript_text=clean_body.strip(),
        transcript_status="provided",
        youtube_url=str(fields.get("youtube_url") or ""),
    )


def records_from_caption_dir(directory: Path) -> list[SermonRecord]:
    if not directory.exists():
        return []
    return [record_from_caption_file(path) for path in sorted(directory.rglob("*")) if path.suffix.lower() in CAPTION_EXTENSIONS]


def record_from_caption_file(path: Path) -> SermonRecord:
    date, title = title_from_filename(path)
    return SermonRecord(
        title=title,
        date=date,
        source_files=[str(path)],
        transcript_path=str(path),
        transcript_text=caption_text(path),
        transcript_status="caption-derived",
        review_flags=["Transcript text came from captions; review paragraphing and caption errors."],
        questionable_claims=["Caption-derived transcript may contain recognition errors."],
    )


def records_from_audio_dir(directory: Path) -> list[SermonRecord]:
    if not directory.exists():
        return []
    return [record_from_audio_file(path) for path in sorted(directory.rglob("*")) if path.suffix.lower() in AUDIO_EXTENSIONS]


def record_from_audio_file(path: Path) -> SermonRecord:
    date, title = title_from_filename(path)
    return SermonRecord(
        title=title,
        date=date,
        source_files=[str(path)],
        audio_files=[str(path)],
        transcript_status="missing",
        review_flags=["Audio file found; add transcript or run a separate transcription workflow."],
    )


def records_from_archivist_archive(archive_dir: Path) -> list[SermonRecord]:
    records: list[SermonRecord] = []
    for metadata_path in sorted(archive_dir.rglob("metadata.json")):
        records.append(record_from_archivist_folder(metadata_path.parent, metadata_path))
    return records


def record_from_archivist_folder(folder: Path, metadata_path: Path) -> SermonRecord:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    title = str(metadata.get("title") or title_from_filename(folder)[1])
    date = str(metadata.get("upload_date") or title_from_filename(folder)[0])
    clean_path = folder / "transcript.clean.md"
    raw_path = folder / "transcript.raw.txt"
    transcript_path = clean_path if clean_path.exists() else raw_path
    transcript_text = ""
    transcript_status = "missing"
    source_files = [str(metadata_path)]
    if transcript_path.exists():
        transcript_text = strip_transcript_heading(transcript_path.read_text(encoding="utf-8")).strip()
        transcript_status = "provided"
        source_files.append(str(transcript_path))
    audio_path = folder / "audio.mp3"
    audio_files = [str(audio_path)] if audio_path.exists() else []
    if audio_files:
        source_files.extend(audio_files)
    return SermonRecord(
        title=title,
        date=date,
        youtube_url=str(metadata.get("youtube_url") or ""),
        youtube_id=str(metadata.get("youtube_id") or ""),
        duration_seconds=metadata.get("duration_seconds") if isinstance(metadata.get("duration_seconds"), int) else None,
        source_files=source_files,
        audio_files=audio_files,
        transcript_path=str(transcript_path) if transcript_path.exists() else "",
        transcript_text=transcript_text,
        transcript_status=transcript_status,
        review_flags=["Imported from church-sermon-archivist; confirm sermon metadata and review transcript cleanup."],
        extra={"archivist_folder": str(folder), "archivist_decision": metadata.get("decision", "")},
    )


def split_frontmatter(text: str) -> tuple[dict[str, object], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    frontmatter_text = text[4:end]
    body = text[end + 4 :].lstrip()
    data = yaml.safe_load(frontmatter_text) or {}
    if not isinstance(data, dict):
        return {}, body
    return data, body


def strip_transcript_heading(text: str) -> str:
    return re.sub(r"^\s*#\s*Transcript\s*", "", text, count=1, flags=re.IGNORECASE).strip()


def leading_metadata(text: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in text.splitlines()[:20]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == "---":
            break
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        normalized_key = key.strip().lower().replace(" ", "_")
        value = value.strip()
        if not value:
            continue
        if normalized_key == "title":
            metadata["title"] = value
        elif normalized_key == "author":
            metadata["speaker"] = value
        elif normalized_key in {"speaker", "series", "date"}:
            metadata[normalized_key] = value
        elif normalized_key in {"squarespace_url", "source_url", "sermon_page_url"}:
            metadata["source_url"] = value
    return metadata


def strip_leading_metadata(text: str) -> str:
    lines = text.splitlines()
    index = 0
    saw_metadata = False
    limit = min(len(lines), 30)
    while index < limit:
        stripped = lines[index].strip()
        if not stripped:
            index += 1
            continue
        if stripped == "---":
            index += 1
            break
        if ":" in stripped:
            key, _value = stripped.split(":", 1)
            normalized_key = key.strip().lower().replace(" ", "_")
            if normalized_key in {
                "title",
                "date",
                "author",
                "speaker",
                "series",
                "squarespace_url",
                "source_url",
                "sermon_page_url",
                "source",
            }:
                saw_metadata = True
                index += 1
                continue
        break
    if not saw_metadata:
        return text
    return "\n".join(lines[index:]).lstrip()


def merge_records(records: list[SermonRecord]) -> list[SermonRecord]:
    merged: dict[str, SermonRecord] = {}
    aliases: dict[str, str] = {}
    for record in records:
        keys = record_keys(record)
        existing_key = next((aliases[key] for key in keys if key in aliases), "")
        if existing_key:
            merged[existing_key].merge(record)
            for key in [*keys, *record_keys(merged[existing_key])]:
                aliases[key] = existing_key
        else:
            primary_key = keys[0]
            merged[primary_key] = record
            for key in keys:
                aliases[key] = primary_key
    return sorted(merged.values(), key=lambda item: (item.date or "9999-99-99", item.title.casefold()))


def record_key(record: SermonRecord) -> str:
    return record_keys(record)[0]


def record_keys(record: SermonRecord) -> list[str]:
    keys: list[str] = []
    if record.youtube_id:
        keys.append(f"youtube-id:{record.youtube_id}")
    if record.youtube_url:
        keys.append(f"youtube-url:{record.youtube_url}")
    if record.date and record.title:
        keys.append(f"date-title:{record.date}:{slugify(record.title)}")
        keys.append(f"year-title:{record.date[:4]}:{slugify(record.title)}")
    if record.date:
        keys.append(f"date:{record.date}")
    if record.title and not record.date:
        keys.append(f"title:{slugify(record.title)}")
    return keys or ["unknown"]
