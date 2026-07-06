from __future__ import annotations

import json
import shlex
import subprocess
from typing import Any

from .models import SermonRecord, merge_unique


def apply_external_summary(records: list[SermonRecord], command: str, timeout_seconds: int = 180) -> list[SermonRecord]:
    if not command.strip():
        return records
    return [_summarize_record(record, command, timeout_seconds) for record in records]


def _summarize_record(record: SermonRecord, command: str, timeout_seconds: int) -> SermonRecord:
    if not record.transcript_text.strip():
        record.review_flags.append("Summary pass skipped because no transcript text is available.")
        return record
    payload = {
        "task": "sermon_archive_wiki_summary",
        "instructions": [
            "Return a concise pastor-review summary for cross-reference purposes.",
            "Do not make canonical claims.",
            "Mark uncertain claims in questionable_claims.",
            "Prefer JSON with summary, themes, topics, related_sermons, questionable_claims.",
        ],
        "sermon": {
            "title": record.title,
            "date": record.date,
            "speaker": record.speaker,
            "series": record.series,
            "scripture_refs": record.scripture_refs,
            "mentioned_scripture_refs": record.mentioned_scripture_refs,
            "transcript": record.transcript_text,
        },
    }
    result = subprocess.run(
        shlex.split(command),
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
    )
    if result.returncode != 0:
        record.review_flags.append(f"External summary command failed: {result.stderr.strip()}")
        record.questionable_claims.append("Summary command failed; no generated summary was trusted.")
        return record

    stdout = result.stdout.strip()
    if not stdout:
        record.review_flags.append("External summary command returned no output.")
        return record

    parsed: dict[str, Any] | None = None
    try:
        loaded = json.loads(stdout)
        if isinstance(loaded, dict):
            parsed = loaded
    except json.JSONDecodeError:
        parsed = None

    if parsed is None:
        record.generated_summary = stdout
    else:
        record.generated_summary = str(parsed.get("summary") or parsed.get("generated_summary") or "").strip()
        record.themes = merge_unique(record.themes, _as_list(parsed.get("themes")))
        record.topics = merge_unique(record.topics, _as_list(parsed.get("topics")))
        record.related_sermons = merge_unique(record.related_sermons, _as_list(parsed.get("related_sermons")))
        record.questionable_claims = merge_unique(record.questionable_claims, _as_list(parsed.get("questionable_claims")))
    record.summary_status = "ai_generated_review_required"
    record.summary_source = "external_command"
    record.review_flags.append("AI-generated summary/themes were added by external command; review before relying on them.")
    return record


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []
