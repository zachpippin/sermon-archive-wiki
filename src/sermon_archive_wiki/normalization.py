from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any
import re

from .inference import BIBLE_BOOKS, infer_scripture_refs, normalize_scripture_ref_text
from .models import SermonRecord, merge_unique

BIBLE_BOOK_BY_KEY = {re.sub(r"[^a-z0-9]+", " ", book.casefold()).strip(): book for book in BIBLE_BOOKS}
SCRIPTURE_BOOK_ALIASES = {
    "1 cor": "1 Corinthians",
    "2 cor": "2 Corinthians",
    "1 thess": "1 Thessalonians",
    "2 thess": "2 Thessalonians",
    "1 tim": "1 Timothy",
    "2 tim": "2 Timothy",
    "song": "Song of Solomon",
    "song of songs": "Song of Solomon",
}


@dataclass
class NamingPassResult:
    records: list[SermonRecord]
    changes: list[dict[str, str]] = field(default_factory=list)
    warnings: list[dict[str, str]] = field(default_factory=list)


def apply_name_normalization(records: list[SermonRecord], config: dict[str, Any]) -> NamingPassResult:
    """Normalize configurable names and flag values that are not likely people."""
    normalization = config.get("normalization", {}) if isinstance(config.get("normalization"), dict) else {}
    speaker_aliases = alias_map(normalization.get("speaker_aliases", {}))
    series_aliases = alias_map(normalization.get("series_aliases", {}))
    annual_series_patterns = normalization.get("annual_series_patterns", [])
    title_series_patterns = normalization.get("title_series_patterns", [])
    infer_scripture_title_series = bool(normalization.get("infer_scripture_book_series_from_title", True))
    scripture_aliases = alias_map(normalization.get("scripture_aliases", {}))
    theme_aliases = alias_map(normalization.get("theme_aliases", {}))
    ignored_speakers = normalized_set(normalization.get("ignored_speakers", []))
    church_variants = church_name_variants(str(config.get("church", {}).get("name") or ""))

    result = NamingPassResult(records=records)
    for record in records:
        normalize_speaker(record, speaker_aliases, ignored_speakers, church_variants, result)
        normalize_series(
            record,
            series_aliases,
            annual_series_patterns,
            title_series_patterns,
            infer_scripture_title_series,
            result,
        )
        record.scripture_refs = normalize_scripture_list(record.scripture_refs, scripture_aliases, record, result)
        record.topics = normalize_name_list(record.topics, theme_aliases, "theme", record, result)
        record.themes = normalize_name_list(record.themes, theme_aliases, "theme", record, result)

    result.warnings.extend(find_near_duplicate_warnings(records, "speaker", [record.speaker for record in records if record.speaker]))
    result.warnings.extend(find_near_duplicate_warnings(records, "series", [record.series for record in records if record.series]))
    return result


def normalize_speaker(
    record: SermonRecord,
    aliases: dict[str, str],
    ignored_speakers: set[str],
    church_variants: set[str],
    result: NamingPassResult,
) -> None:
    original = record.speaker
    cleaned = normalized_value(original)
    if original and cleaned != original:
        add_change(result, "speaker", original, cleaned, "trimmed/collapsed whitespace", record)
    if not cleaned:
        record.speaker = ""
        return

    scripture_refs = infer_scripture_refs(cleaned)
    if scripture_refs and scripture_like_value(cleaned, scripture_refs):
        record.scripture_refs = merge_unique(record.scripture_refs, scripture_refs)
        record.speaker = ""
        reason = "speaker field looked like a scripture reference"
        record.review_flags.append("Speaker field contained a scripture reference; confirm the missing speaker.")
        add_change(result, "speaker", cleaned, "", reason, record)
        add_warning(result, "speaker", cleaned, reason, record)
        return

    if normalized_key(cleaned) in ignored_speakers or looks_like_church_speaker(cleaned, church_variants):
        record.speaker = ""
        reason = "speaker field looked like a church, team, or organization instead of a person"
        record.review_flags.append("Speaker value looked like a church/team label; confirm the preacher.")
        add_change(result, "speaker", cleaned, "", reason, record)
        add_warning(result, "speaker", cleaned, reason, record)
        return

    record.speaker = apply_alias(cleaned, aliases, "speaker", record, result)


def normalize_series(
    record: SermonRecord,
    aliases: dict[str, str],
    annual_patterns: object,
    title_patterns: object,
    infer_scripture_title_series: bool,
    result: NamingPassResult,
) -> None:
    original = record.series
    cleaned = normalized_value(original)
    if original and cleaned != original:
        add_change(result, "series", original, cleaned, "trimmed/collapsed whitespace", record)
    cleaned = apply_alias(cleaned, aliases, "series", record, result) if cleaned else ""

    annual = infer_annual_series(record, annual_patterns)
    if annual:
        inferred, reason, override_existing = annual
        if not cleaned:
            assign_series(record, inferred)
            add_change(result, "series", "", inferred, reason, record)
            return
        if cleaned != inferred and normalized_key(cleaned) == normalized_key(inferred):
            assign_series(record, inferred)
            add_change(result, "series", cleaned, inferred, reason, record)
            return
        if cleaned != inferred and override_existing:
            assign_series(record, inferred)
            append_review_flag(record, f"Series was corrected from {cleaned} to {inferred}; confirm during review.")
            add_change(result, "series", cleaned, inferred, reason, record)
            return

    configured = infer_configured_title_series(record, title_patterns)
    if configured:
        inferred, reason, override_existing = configured
        if not cleaned:
            assign_series(record, inferred)
            add_change(result, "series", "", inferred, reason, record)
            return
        if cleaned != inferred and normalized_key(cleaned) == normalized_key(inferred):
            assign_series(record, inferred)
            add_change(result, "series", cleaned, inferred, reason, record)
            return
        if cleaned != inferred and override_existing:
            assign_series(record, inferred)
            append_review_flag(record, f"Series was corrected from {cleaned} to {inferred}; confirm during review.")
            add_change(result, "series", cleaned, inferred, reason, record)
            return

    if not cleaned and infer_scripture_title_series:
        inferred = infer_scripture_book_series_from_title(record.title)
        if inferred:
            assign_series(record, inferred)
            add_change(result, "series", "", inferred, "inferred Bible-book series from title", record)
            return

    assign_series(record, cleaned)


def infer_annual_series(record: SermonRecord, raw_patterns: object) -> tuple[str, str, bool] | None:
    for pattern in annual_series_patterns(raw_patterns):
        title_series = annual_series_from_text(
            record.title,
            record.date,
            pattern,
            require_week=bool(pattern.get("require_week", True)),
        )
        if title_series:
            return title_series, "annual series inferred from title/date", bool(pattern.get("override_existing", False))

        series_value = annual_series_from_text(record.series, record.date, pattern, require_week=False)
        if series_value:
            return series_value, "annual series normalized from series/date", True
    return None


def annual_series_patterns(raw_patterns: object) -> list[dict[str, object]]:
    if not isinstance(raw_patterns, list):
        return []
    patterns: list[dict[str, object]] = []
    for raw in raw_patterns:
        if isinstance(raw, str):
            canonical = normalized_value(raw)
            if canonical:
                patterns.append(
                    {
                        "canonical": f"{canonical} {{year}}",
                        "aliases": [canonical],
                        "require_week": True,
                        "override_existing": False,
                    }
                )
            continue
        if not isinstance(raw, dict):
            continue
        canonical = normalized_value(raw.get("canonical") or raw.get("series") or raw.get("name") or "")
        aliases = raw.get("aliases", [])
        if isinstance(aliases, str):
            aliases = [aliases]
        if not isinstance(aliases, list):
            aliases = []
        alias_values = [normalized_value(alias) for alias in aliases if normalized_value(alias)]
        if not canonical or not alias_values:
            continue
        patterns.append(
            {
                "canonical": canonical,
                "aliases": alias_values,
                "require_week": bool(raw.get("require_week", True)),
                "override_existing": bool(raw.get("override_existing", False)),
            }
        )
    return patterns


def annual_series_from_text(text: str, date: str, pattern: dict[str, object], require_week: bool) -> str:
    key = normalized_key(text)
    if not key:
        return ""
    if require_week and "week" not in key.split():
        return ""
    for alias in pattern.get("aliases", []):
        alias_key = normalized_key(alias)
        if not alias_key or not annual_alias_present(key, alias_key):
            continue
        year = annual_year(key, alias_key) or date_year(date)
        if not year:
            continue
        canonical = str(pattern.get("canonical") or "").strip()
        return canonical.replace("{year}", year).strip()
    return ""


def annual_alias_present(key: str, alias_key: str) -> bool:
    return bool(re.search(rf"(?:^|\s){re.escape(alias_key)}(?:$|\s|\d{{2,4}})", key))


def annual_year(key: str, alias_key: str) -> str:
    full_year = re.search(r"\b(19\d{2}|20\d{2})\b", key)
    if full_year:
        return full_year.group(1)
    short_year = re.search(rf"(?:^|\s){re.escape(alias_key)}\s*(\d{{2}})(?:$|\s)", key)
    if short_year:
        return f"20{short_year.group(1)}"
    return ""


def date_year(date: str) -> str:
    match = re.match(r"^(\d{4})-\d{2}-\d{2}$", date or "")
    return match.group(1) if match else ""


def infer_configured_title_series(record: SermonRecord, raw_patterns: object) -> tuple[str, str, bool] | None:
    if not isinstance(raw_patterns, list):
        return None
    for raw in raw_patterns:
        if not isinstance(raw, dict):
            continue
        pattern = str(raw.get("pattern") or "").strip()
        series = normalized_value(raw.get("series") or "")
        if not pattern or not series:
            continue
        try:
            matched = re.search(pattern, record.title, flags=re.IGNORECASE)
        except re.error:
            continue
        if matched:
            return series, "series inferred from title pattern", bool(raw.get("override_existing", False))
    return None


def infer_scripture_book_series_from_title(title: str) -> str:
    title_key = normalized_key(title)
    if not title_key:
        return ""
    refs = infer_scripture_refs(title, max_refs=1, include_book_only=True)
    if not refs:
        return ""
    book = scripture_book_from_ref(refs[0])
    if not book:
        return ""
    book_key = normalized_key(book)
    if title_key == book_key or title_key.startswith(f"{book_key} "):
        return book
    return ""


def scripture_book_from_ref(ref: str) -> str:
    ref_key = normalized_key(ref)
    for book in sorted({book for book in BIBLE_BOOKS if book != "Psalms"}, key=len, reverse=True):
        book_key = normalized_key(book)
        if ref_key == book_key or ref_key.startswith(f"{book_key} "):
            return book
    return ""


def append_review_flag(record: SermonRecord, message: str) -> None:
    if message not in record.review_flags:
        record.review_flags.append(message)


def assign_series(record: SermonRecord, series: str) -> None:
    record.series = series
    if series:
        record.review_flags = [flag for flag in record.review_flags if flag != "Add or confirm series."]


def normalize_name_list(
    values: list[str],
    aliases: dict[str, str],
    scope: str,
    record: SermonRecord,
    result: NamingPassResult,
) -> list[str]:
    normalized: list[str] = []
    for value in values:
        cleaned = normalized_value(value)
        if not cleaned:
            continue
        normalized.append(apply_alias(cleaned, aliases, scope, record, result))
    return merge_unique([], normalized)


def normalize_scripture_list(
    values: list[str],
    aliases: dict[str, str],
    record: SermonRecord,
    result: NamingPassResult,
) -> list[str]:
    normalized: list[str] = []
    for value in values:
        cleaned = apply_alias(normalized_value(value), aliases, "scripture", record, result)
        if not cleaned:
            continue
        scripture = normalize_scripture_ref(cleaned)
        if scripture:
            if scripture != cleaned:
                add_change(result, "scripture", cleaned, scripture, "normalized Bible book name", record)
            normalized.append(scripture)
            continue
        reason = "scripture field did not look like a Bible reference"
        add_change(result, "scripture", cleaned, "", reason, record)
        add_warning(result, "scripture", cleaned, reason, record)
    return merge_unique([], normalized)


def apply_alias(
    value: str,
    aliases: dict[str, str],
    scope: str,
    record: SermonRecord,
    result: NamingPassResult,
) -> str:
    replacement = aliases.get(normalized_key(value), value)
    if replacement != value:
        add_change(result, scope, value, replacement, "configured alias", record)
    return replacement


def alias_map(raw: object) -> dict[str, str]:
    aliases: dict[str, str] = {}
    if not isinstance(raw, dict):
        return aliases
    for key, value in raw.items():
        if isinstance(value, list):
            canonical = normalized_value(key)
            aliases[normalized_key(canonical)] = canonical
            for alias in value:
                alias_text = normalized_value(alias)
                if alias_text:
                    aliases[normalized_key(alias_text)] = canonical
        else:
            alias_text = normalized_value(key)
            canonical = normalized_value(value)
            if alias_text and canonical:
                aliases[normalized_key(alias_text)] = canonical
                aliases[normalized_key(canonical)] = canonical
    return aliases


def normalized_value(value: object) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def normalized_key(value: object) -> str:
    text = normalized_value(value).casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalized_set(values: object) -> set[str]:
    if not isinstance(values, list):
        return set()
    return {normalized_key(value) for value in values if normalized_key(value)}


def church_name_variants(church_name: str) -> set[str]:
    name = normalized_key(church_name)
    if not name:
        return set()
    variants = {name}
    without_church = re.sub(r"\b(church|of|the)\b", " ", name)
    without_church = re.sub(r"\s+", " ", without_church).strip()
    if without_church:
        variants.add(without_church)
    return variants


def looks_like_church_speaker(value: str, church_variants: set[str]) -> bool:
    key = normalized_key(value)
    if not key:
        return False
    if key in church_variants:
        return True
    org_terms = {"church", "team", "staff", "pastoral team", "ministry", "ministries"}
    has_org_term = any(term in key for term in org_terms)
    return has_org_term and any(variant and variant in key for variant in church_variants)


def scripture_like_value(value: str, refs: list[str]) -> bool:
    key = normalized_key(value)
    return any(normalized_key(ref) == key for ref in refs)


def normalize_scripture_ref(value: str) -> str:
    return normalize_scripture_ref_text(value)


def find_near_duplicate_warnings(records: list[SermonRecord], scope: str, values: list[str]) -> list[dict[str, str]]:
    counts = Counter(values)
    names = sorted(counts, key=lambda item: item.casefold())
    warnings: list[dict[str, str]] = []
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            if not might_be_duplicate(left, right):
                continue
            warnings.append(
                {
                    "scope": scope,
                    "value": left,
                    "replacement": right,
                    "reason": f"possible duplicate ({counts[left]} vs {counts[right]} sermons)",
                    "sermon": "",
                    "date": "",
                }
            )
    return warnings


def might_be_duplicate(left: str, right: str) -> bool:
    left_key = normalized_key(left)
    right_key = normalized_key(right)
    if not left_key or not right_key or left_key == right_key:
        return False
    left_parts = left_key.split()
    right_parts = right_key.split()
    if len(left_parts) >= 2 and len(right_parts) >= 2 and left_parts[0] == right_parts[0]:
        return SequenceMatcher(None, left_parts[-1], right_parts[-1]).ratio() >= 0.78
    return SequenceMatcher(None, left_key, right_key).ratio() >= 0.92


def add_change(
    result: NamingPassResult,
    scope: str,
    value: str,
    replacement: str,
    reason: str,
    record: SermonRecord,
) -> None:
    result.changes.append(change_row(scope, value, replacement, reason, record))


def add_warning(
    result: NamingPassResult,
    scope: str,
    value: str,
    reason: str,
    record: SermonRecord,
) -> None:
    result.warnings.append(change_row(scope, value, "", reason, record))


def change_row(scope: str, value: str, replacement: str, reason: str, record: SermonRecord) -> dict[str, str]:
    return {
        "scope": scope,
        "value": value,
        "replacement": replacement,
        "reason": reason,
        "sermon": record.title,
        "date": record.date,
    }
