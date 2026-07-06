from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import shlex
import subprocess
from typing import Any

from .models import SermonRecord
from .util import normalize_date


def fetch_youtube_records(urls: list[str], yt_dlp_command: str = "yt-dlp") -> list[SermonRecord]:
    records: list[SermonRecord] = []
    for url in urls:
        command = [*shlex.split(yt_dlp_command), "--dump-single-json", "--skip-download", "--flat-playlist", url]
        result = subprocess.run(command, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            records.append(
                SermonRecord(
                    title=url,
                    youtube_url=url,
                    transcript_status="missing",
                    review_flags=[f"Could not fetch YouTube metadata with {yt_dlp_command}: {result.stderr.strip()}"],
                    questionable_claims=["YouTube metadata could not be verified automatically."],
                )
            )
            continue
        data = json.loads(result.stdout)
        records.extend(records_from_youtube_data(data, source=url))
    return records


def records_from_youtube_metadata_file(path: Path) -> list[SermonRecord]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return records_from_youtube_data(data, source=str(path))


def records_from_youtube_data(data: Any, source: str) -> list[SermonRecord]:
    if isinstance(data, list):
        return [_record_from_item(item, source) for item in data if isinstance(item, dict)]
    if isinstance(data, dict) and isinstance(data.get("entries"), list):
        return [_record_from_item(item, source) for item in data["entries"] if isinstance(item, dict)]
    if isinstance(data, dict):
        return [_record_from_item(data, source)]
    return []


def _record_from_item(item: dict[str, Any], source: str) -> SermonRecord:
    title = str(item.get("title") or item.get("fulltitle") or item.get("id") or "Untitled YouTube Sermon")
    url = str(item.get("webpage_url") or item.get("url") or "")
    if url and url.startswith("/"):
        url = f"https://www.youtube.com{url}"
    if url and not url.startswith("http") and item.get("id"):
        url = f"https://www.youtube.com/watch?v={item['id']}"
    date = _date_from_item(item)
    return SermonRecord(
        title=title,
        date=date,
        youtube_url=url,
        youtube_id=str(item.get("id") or ""),
        duration_seconds=_duration(item),
        transcript_status="missing",
        source_files=[source],
        review_flags=["YouTube metadata imported; confirm title/date/speaker/series before relying on it."],
    )


def _date_from_item(item: dict[str, Any]) -> str:
    upload_date = str(item.get("upload_date") or "")
    if len(upload_date) == 8 and upload_date.isdigit():
        return normalize_date(upload_date)
    timestamp = item.get("timestamp")
    if isinstance(timestamp, (int, float)):
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat()
    release_timestamp = item.get("release_timestamp")
    if isinstance(release_timestamp, (int, float)):
        return datetime.fromtimestamp(release_timestamp, tz=timezone.utc).date().isoformat()
    return ""


def _duration(item: dict[str, Any]) -> int | None:
    duration = item.get("duration")
    if isinstance(duration, (int, float)):
        return int(duration)
    return None
