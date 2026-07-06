from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


RESOLVED_BY_TRANSCRIPT_FLAGS = {
    "Audio file found; add transcript or run a separate transcription workflow.",
    "Catalog says a transcript exists, but no local transcript file/text was provided.",
    "HTML transcript file did not contain extractable transcript text.",
}


@dataclass
class SermonRecord:
    title: str
    date: str = ""
    speaker: str = ""
    series: str = ""
    scripture_refs: list[str] = field(default_factory=list)
    mentioned_scripture_refs: list[str] = field(default_factory=list)
    scripture_ref_counts: dict[str, int] = field(default_factory=dict)
    topics: list[str] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)
    related_sermons: list[str] = field(default_factory=list)
    source_files: list[str] = field(default_factory=list)
    audio_files: list[str] = field(default_factory=list)
    transcript_path: str = ""
    transcript_text: str = ""
    transcript_status: str = "missing"
    youtube_url: str = ""
    youtube_id: str = ""
    duration_seconds: int | None = None
    status: str = "draft"
    review_status: str = "draft"
    generated_summary: str = ""
    summary_status: str = "none"
    summary_source: str = ""
    questionable_claims: list[str] = field(default_factory=list)
    review_flags: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def merge(self, other: "SermonRecord") -> "SermonRecord":
        """Merge another record for the same sermon into this one."""
        for field_name in (
            "title",
            "date",
            "speaker",
            "series",
            "transcript_path",
            "youtube_url",
            "youtube_id",
            "generated_summary",
            "summary_status",
            "summary_source",
        ):
            if not getattr(self, field_name) and getattr(other, field_name):
                setattr(self, field_name, getattr(other, field_name))

        if self.duration_seconds is None and other.duration_seconds is not None:
            self.duration_seconds = other.duration_seconds

        if not self.transcript_text and other.transcript_text:
            self.transcript_text = other.transcript_text
            self.transcript_status = other.transcript_status
        elif self.transcript_status == "missing" and other.transcript_status != "missing":
            self.transcript_status = other.transcript_status

        self.scripture_refs = merge_unique(self.scripture_refs, other.scripture_refs)
        self.mentioned_scripture_refs = merge_unique(self.mentioned_scripture_refs, other.mentioned_scripture_refs)
        for ref, count in other.scripture_ref_counts.items():
            self.scripture_ref_counts[ref] = self.scripture_ref_counts.get(ref, 0) + count
        self.topics = merge_unique(self.topics, other.topics)
        self.themes = merge_unique(self.themes, other.themes)
        self.related_sermons = merge_unique(self.related_sermons, other.related_sermons)
        self.source_files = merge_unique(self.source_files, other.source_files)
        self.audio_files = merge_unique(self.audio_files, other.audio_files)
        self.questionable_claims = merge_unique(self.questionable_claims, other.questionable_claims)
        self.review_flags = merge_unique(self.review_flags, other.review_flags)
        if self.transcript_text.strip():
            self.review_flags = [flag for flag in self.review_flags if flag not in RESOLVED_BY_TRANSCRIPT_FLAGS]
        self.extra.update({key: value for key, value in other.extra.items() if value not in ("", None, [], {})})
        return self


def merge_unique(left: list[str], right: list[str]) -> list[str]:
    seen: set[str] = set()
    values: list[str] = []
    for value in [*left, *right]:
        normalized = str(value).strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        values.append(normalized)
    return values
