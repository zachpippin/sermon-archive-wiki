from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import re

from .models import SermonRecord, merge_unique
from .inference import BIBLE_BOOKS, BIBLE_CHAPTER_COUNTS, normalize_book


@dataclass(frozen=True)
class ScriptureEntry:
    ref: str
    record: SermonRecord
    mentions: int
    primary: bool


def build_scripture_index(records: list[SermonRecord]) -> dict[str, list[ScriptureEntry]]:
    grouped: dict[str, list[ScriptureEntry]] = defaultdict(list)
    for record in records:
        primary_keys = {ref.casefold() for ref in record.scripture_refs}
        for ref in scripture_refs_for_record(record):
            grouped[ref].append(
                ScriptureEntry(
                    ref=ref,
                    record=record,
                    mentions=max(1, int(record.scripture_ref_counts.get(ref, 1))),
                    primary=ref.casefold() in primary_keys,
                )
            )
    return dict(grouped)


def scripture_refs_for_record(record: SermonRecord) -> list[str]:
    refs = merge_unique(record.scripture_refs, record.mentioned_scripture_refs)
    refs = merge_unique(refs, list(record.scripture_ref_counts))
    return prune_less_specific_refs(refs)


def scripture_entry_totals(entries: list[ScriptureEntry]) -> tuple[int, int, int]:
    sermons = len({id(entry.record) for entry in entries})
    mentions = sum(entry.mentions for entry in entries)
    primary = sum(1 for entry in entries if entry.primary)
    return sermons, mentions, primary


def scripture_role(entry: ScriptureEntry) -> str:
    return "Primary" if entry.primary else "Referenced"


def prune_less_specific_refs(refs: list[str]) -> list[str]:
    parsed = [(ref, parse_scripture_ref(ref)) for ref in refs]
    pruned: list[str] = []
    for ref, current in parsed:
        if current is None:
            pruned.append(ref)
            continue
        if any(other is not None and is_more_specific_same_area(current, other) for other_ref, other in parsed if other_ref != ref):
            continue
        pruned.append(ref)
    return pruned


def is_more_specific_same_area(current: dict[str, object], other: dict[str, object]) -> bool:
    if current["book"] != other["book"]:
        return False
    if int(other["specificity"]) <= int(current["specificity"]):
        return False
    if int(current["specificity"]) == 0:
        return True
    return ranges_overlap(
        int(current["start_chapter"]),
        int(current["end_chapter"]),
        int(other["start_chapter"]),
        int(other["end_chapter"]),
    )


def ranges_overlap(left_start: int, left_end: int, right_start: int, right_end: int) -> bool:
    return left_start <= right_end and right_start <= left_end


def parse_scripture_ref(ref: str) -> dict[str, object] | None:
    text = re.sub(r"\s+", " ", ref.strip())
    for book in sorted(BIBLE_BOOKS, key=len, reverse=True):
        canonical = normalize_book(book)
        if text.casefold() == canonical.casefold():
            return {
                "book": canonical,
                "start_chapter": 0,
                "end_chapter": 0,
                "specificity": 0,
            }
        prefix = canonical + " "
        if text.casefold().startswith(prefix.casefold()):
            rest = text[len(prefix) :].strip()
            match = re.match(r"(?P<start>\d+)(?:\s*-\s*(?P<end>\d+))?(?::(?P<verse>\d+)(?:\s*-\s*(?:(?P<end_chapter>\d+):)?(?P<verse_end>\d+))?)?$", rest)
            if not match:
                return None
            start = int(match.group("start"))
            if BIBLE_CHAPTER_COUNTS.get(canonical) == 1 and not match.group("verse"):
                return {
                    "book": canonical,
                    "start_chapter": 1,
                    "end_chapter": 1,
                    "specificity": 2,
                }
            end = int(match.group("end") or match.group("end_chapter") or start)
            specificity = 2 if match.group("verse") else 1
            return {
                "book": canonical,
                "start_chapter": start,
                "end_chapter": end,
                "specificity": specificity,
            }
    return None


def scripture_flag(ref: str, entries: list[ScriptureEntry]) -> str:
    parsed = parse_scripture_ref(ref)
    if parsed is None or int(parsed["specificity"]) == 0:
        return ""
    sermons, mentions, _primary = scripture_entry_totals(entries)
    if sermons >= 3:
        return "Frequent passage"
    if sermons >= 2 and mentions >= 2:
        return "Repeated passage"
    if mentions >= 5:
        return "Often mentioned"
    return ""


def frequent_scripture_entries(grouped: dict[str, list[ScriptureEntry]]) -> list[tuple[str, list[ScriptureEntry], str]]:
    flagged = [(ref, entries, scripture_flag(ref, entries)) for ref, entries in grouped.items()]
    flagged = [item for item in flagged if item[2]]
    return sorted(flagged, key=lambda item: (-scripture_entry_totals(item[1])[1], -scripture_entry_totals(item[1])[0], item[0].casefold()))
