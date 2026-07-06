from __future__ import annotations

from collections import Counter

from .models import SermonRecord


def has_audio(record: SermonRecord) -> bool:
    return any(source.strip() for source in record.audio_files)


def has_transcript(record: SermonRecord) -> bool:
    return bool(record.transcript_text.strip())


def has_summary(record: SermonRecord) -> bool:
    return bool(record.generated_summary.strip())


def completeness_issues(record: SermonRecord) -> list[str]:
    issues: list[str] = []
    if not has_transcript(record):
        issues.append("Missing transcript text")
    if not has_summary(record):
        issues.append("Missing generated summary")
    if has_audio(record) and not has_transcript(record):
        issues.append("Audio present but transcript text missing")
    if has_audio(record) and not has_summary(record):
        issues.append("Audio present but generated summary missing")
    if record.transcript_status == "catalog-listed" and not has_transcript(record):
        issues.append("Catalog lists a transcript, but local transcript text was not found")
    return issues


def completeness_counts(records: list[SermonRecord]) -> Counter[str]:
    counts: Counter[str] = Counter()
    counts["sermons"] = len(records)
    for record in records:
        if has_audio(record):
            counts["with_audio"] += 1
        if has_transcript(record):
            counts["with_transcript"] += 1
        else:
            counts["missing_transcript"] += 1
        if has_summary(record):
            counts["with_summary"] += 1
        else:
            counts["missing_summary"] += 1
        if has_audio(record) and not has_transcript(record):
            counts["audio_missing_transcript"] += 1
        if has_audio(record) and not has_summary(record):
            counts["audio_missing_summary"] += 1
        if record.transcript_status == "catalog-listed" and not has_transcript(record):
            counts["catalog_listed_missing_transcript"] += 1
    return counts
