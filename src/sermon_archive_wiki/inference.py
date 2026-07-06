from __future__ import annotations

from collections import Counter
import re

from .models import SermonRecord, merge_unique
from .util import split_list

try:
    import pythonbible as bible
except ImportError:  # pragma: no cover - dependency is declared, fallback keeps parsing usable.
    bible = None


def _book_key(value: str) -> str:
    text = value.strip().casefold().replace(".", "")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _alias_pattern(alias_key: str, allow_period: bool = False) -> str:
    suffix = r"\.?" if allow_period else ""
    return r"\s+".join(re.escape(part) for part in alias_key.split()) + suffix


BIBLE_BOOKS = [
    "Genesis",
    "Exodus",
    "Leviticus",
    "Numbers",
    "Deuteronomy",
    "Joshua",
    "Judges",
    "Ruth",
    "1 Samuel",
    "2 Samuel",
    "1 Kings",
    "2 Kings",
    "1 Chronicles",
    "2 Chronicles",
    "Ezra",
    "Nehemiah",
    "Esther",
    "Job",
    "Psalm",
    "Psalms",
    "Proverbs",
    "Ecclesiastes",
    "Song of Solomon",
    "Isaiah",
    "Jeremiah",
    "Lamentations",
    "Ezekiel",
    "Daniel",
    "Hosea",
    "Joel",
    "Amos",
    "Obadiah",
    "Jonah",
    "Micah",
    "Nahum",
    "Habakkuk",
    "Zephaniah",
    "Haggai",
    "Zechariah",
    "Malachi",
    "Matthew",
    "Mark",
    "Luke",
    "John",
    "Acts",
    "Romans",
    "1 Corinthians",
    "2 Corinthians",
    "Galatians",
    "Ephesians",
    "Philippians",
    "Colossians",
    "1 Thessalonians",
    "2 Thessalonians",
    "1 Timothy",
    "2 Timothy",
    "Titus",
    "Philemon",
    "Hebrews",
    "James",
    "1 Peter",
    "2 Peter",
    "1 John",
    "2 John",
    "3 John",
    "Jude",
    "Revelation",
]


BIBLE_CHAPTER_COUNTS = {
    "Genesis": 50,
    "Exodus": 40,
    "Leviticus": 27,
    "Numbers": 36,
    "Deuteronomy": 34,
    "Joshua": 24,
    "Judges": 21,
    "Ruth": 4,
    "1 Samuel": 31,
    "2 Samuel": 24,
    "1 Kings": 22,
    "2 Kings": 25,
    "1 Chronicles": 29,
    "2 Chronicles": 36,
    "Ezra": 10,
    "Nehemiah": 13,
    "Esther": 10,
    "Job": 42,
    "Psalm": 150,
    "Psalms": 150,
    "Proverbs": 31,
    "Ecclesiastes": 12,
    "Song of Solomon": 8,
    "Isaiah": 66,
    "Jeremiah": 52,
    "Lamentations": 5,
    "Ezekiel": 48,
    "Daniel": 12,
    "Hosea": 14,
    "Joel": 3,
    "Amos": 9,
    "Obadiah": 1,
    "Jonah": 4,
    "Micah": 7,
    "Nahum": 3,
    "Habakkuk": 3,
    "Zephaniah": 3,
    "Haggai": 2,
    "Zechariah": 14,
    "Malachi": 4,
    "Matthew": 28,
    "Mark": 16,
    "Luke": 24,
    "John": 21,
    "Acts": 28,
    "Romans": 16,
    "1 Corinthians": 16,
    "2 Corinthians": 13,
    "Galatians": 6,
    "Ephesians": 6,
    "Philippians": 4,
    "Colossians": 4,
    "1 Thessalonians": 5,
    "2 Thessalonians": 3,
    "1 Timothy": 6,
    "2 Timothy": 4,
    "Titus": 3,
    "Philemon": 1,
    "Hebrews": 13,
    "James": 5,
    "1 Peter": 5,
    "2 Peter": 3,
    "1 John": 5,
    "2 John": 1,
    "3 John": 1,
    "Jude": 1,
    "Revelation": 22,
}
SINGLE_CHAPTER_VERSE_COUNTS = {
    "Obadiah": 21,
    "Philemon": 25,
    "2 John": 13,
    "3 John": 15,
    "Jude": 25,
}
PYTHONBIBLE_BOOKS = {
    "Genesis": "GENESIS",
    "Exodus": "EXODUS",
    "Leviticus": "LEVITICUS",
    "Numbers": "NUMBERS",
    "Deuteronomy": "DEUTERONOMY",
    "Joshua": "JOSHUA",
    "Judges": "JUDGES",
    "Ruth": "RUTH",
    "1 Samuel": "SAMUEL_1",
    "2 Samuel": "SAMUEL_2",
    "1 Kings": "KINGS_1",
    "2 Kings": "KINGS_2",
    "1 Chronicles": "CHRONICLES_1",
    "2 Chronicles": "CHRONICLES_2",
    "Ezra": "EZRA",
    "Nehemiah": "NEHEMIAH",
    "Esther": "ESTHER",
    "Job": "JOB",
    "Psalm": "PSALMS",
    "Psalms": "PSALMS",
    "Proverbs": "PROVERBS",
    "Ecclesiastes": "ECCLESIASTES",
    "Song of Solomon": "SONG_OF_SONGS",
    "Isaiah": "ISAIAH",
    "Jeremiah": "JEREMIAH",
    "Lamentations": "LAMENTATIONS",
    "Ezekiel": "EZEKIEL",
    "Daniel": "DANIEL",
    "Hosea": "HOSEA",
    "Joel": "JOEL",
    "Amos": "AMOS",
    "Obadiah": "OBADIAH",
    "Jonah": "JONAH",
    "Micah": "MICAH",
    "Nahum": "NAHUM",
    "Habakkuk": "HABAKKUK",
    "Zephaniah": "ZEPHANIAH",
    "Haggai": "HAGGAI",
    "Zechariah": "ZECHARIAH",
    "Malachi": "MALACHI",
    "Matthew": "MATTHEW",
    "Mark": "MARK",
    "Luke": "LUKE",
    "John": "JOHN",
    "Acts": "ACTS",
    "Romans": "ROMANS",
    "1 Corinthians": "CORINTHIANS_1",
    "2 Corinthians": "CORINTHIANS_2",
    "Galatians": "GALATIANS",
    "Ephesians": "EPHESIANS",
    "Philippians": "PHILIPPIANS",
    "Colossians": "COLOSSIANS",
    "1 Thessalonians": "THESSALONIANS_1",
    "2 Thessalonians": "THESSALONIANS_2",
    "1 Timothy": "TIMOTHY_1",
    "2 Timothy": "TIMOTHY_2",
    "Titus": "TITUS",
    "Philemon": "PHILEMON",
    "Hebrews": "HEBREWS",
    "James": "JAMES",
    "1 Peter": "PETER_1",
    "2 Peter": "PETER_2",
    "1 John": "JOHN_1",
    "2 John": "JOHN_2",
    "3 John": "JOHN_3",
    "Jude": "JUDE",
    "Revelation": "REVELATION",
}


BOOK_ALIASES: dict[str, list[str]] = {
    "Genesis": ["Gen"],
    "Exodus": ["Exod", "Ex"],
    "Leviticus": ["Lev"],
    "Numbers": ["Num"],
    "Deuteronomy": ["Deut"],
    "Joshua": ["Josh"],
    "Judges": ["Judg"],
    "Ruth": [],
    "1 Samuel": ["1 Sam", "First Samuel"],
    "2 Samuel": ["2 Sam", "Second Samuel"],
    "1 Kings": ["First Kings"],
    "2 Kings": ["Second Kings"],
    "1 Chronicles": ["1 Chron", "First Chronicles"],
    "2 Chronicles": ["2 Chron", "Second Chronicles"],
    "Ezra": [],
    "Nehemiah": ["Neh"],
    "Esther": ["Esth"],
    "Job": [],
    "Psalm": ["Psalms", "Ps", "Psa"],
    "Proverbs": ["Prov"],
    "Ecclesiastes": ["Eccl", "Eccles"],
    "Song of Solomon": ["Song", "Song of Songs"],
    "Isaiah": ["Isa"],
    "Jeremiah": ["Jer"],
    "Lamentations": ["Lam"],
    "Ezekiel": ["Ezek"],
    "Daniel": ["Dan"],
    "Hosea": ["Hos"],
    "Joel": [],
    "Amos": [],
    "Obadiah": ["Obad"],
    "Jonah": [],
    "Micah": ["Mic"],
    "Nahum": ["Nah"],
    "Habakkuk": ["Hab"],
    "Zephaniah": ["Zeph"],
    "Haggai": ["Hag"],
    "Zechariah": ["Zech"],
    "Malachi": ["Mal"],
    "Matthew": ["Matt", "Mt"],
    "Mark": ["Mk"],
    "Luke": ["Lk"],
    "John": ["Jn"],
    "Acts": [],
    "Romans": ["Rom"],
    "1 Corinthians": ["1 Cor", "First Corinthians"],
    "2 Corinthians": ["2 Cor", "Second Corinthians"],
    "Galatians": ["Gal"],
    "Ephesians": ["Eph"],
    "Philippians": ["Phil"],
    "Colossians": ["Col"],
    "1 Thessalonians": ["1 Thess", "First Thessalonians"],
    "2 Thessalonians": ["2 Thess", "Second Thessalonians"],
    "1 Timothy": ["1 Tim", "First Timothy"],
    "2 Timothy": ["2 Tim", "Second Timothy"],
    "Titus": [],
    "Philemon": ["Philem"],
    "Hebrews": ["Heb"],
    "James": ["Jas"],
    "1 Peter": ["1 Pet", "First Peter"],
    "2 Peter": ["2 Pet", "Second Peter"],
    "1 John": ["First John"],
    "2 John": ["Second John"],
    "3 John": ["Third John"],
    "Jude": [],
    "Revelation": ["Rev"],
}

BOOK_LOOKUP: dict[str, str] = {}
for _canonical in BIBLE_BOOKS:
    BOOK_LOOKUP[_book_key(_canonical)] = "Psalm" if _canonical == "Psalms" else _canonical
for _canonical, _aliases in BOOK_ALIASES.items():
    BOOK_LOOKUP[_book_key(_canonical)] = _canonical
    for _alias in _aliases:
        BOOK_LOOKUP[_book_key(_alias)] = _canonical

CANONICAL_BOOK_KEYS = {_book_key(book) for book in BIBLE_BOOKS}
BOOK_PATTERN = "|".join(
    _alias_pattern(alias, allow_period=alias not in CANONICAL_BOOK_KEYS)
    for alias in sorted(BOOK_LOOKUP, key=lambda item: (len(item), item), reverse=True)
)
NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
}
NUMBER_PATTERN = r"\d{1,3}(?!\d)|" + "|".join(NUMBER_WORDS)
SCRIPTURE_RE = re.compile(
    rf"(?<![A-Za-z0-9])(?P<book>{BOOK_PATTERN})(?![A-Za-z0-9])"
    rf"(?P<tail>\s+(?:(?:chapters?|ch\.?)\s+)?(?P<chapter>{NUMBER_PATTERN})"
    rf"(?:(?P<sep>\s*[:\-\u2013]\s*)(?P<range_start>{NUMBER_PATTERN})"
    rf"(?:\s*[\-\u2013]\s*(?P<range_end>{NUMBER_PATTERN})(?::(?P<range_end_verse>{NUMBER_PATTERN}))?)?)?"
    rf"(?:\s*,?\s*(?:verse|verses)\s+(?P<verse>{NUMBER_PATTERN})"
    rf"(?:\s*[\-\u2013]\s*(?P<verse_end>{NUMBER_PATTERN}))?)?)?",
    re.IGNORECASE,
)
CONTEXT_CHAPTER_RE = re.compile(
    rf"\b(?:chapters?|ch\.?)\s+(?P<chapter>{NUMBER_PATTERN})(?::(?P<verse>{NUMBER_PATTERN}))?"
    rf"(?:\s*[\-\u2013]\s*(?P<end_chapter>{NUMBER_PATTERN})(?::(?P<end_verse>{NUMBER_PATTERN}))?)?",
    re.IGNORECASE,
)
CONTEXT_VERSE_RE = re.compile(
    rf"\b(?:verse|verses)\s+(?P<verse>{NUMBER_PATTERN})(?:\s*[\-\u2013]\s*(?P<verse_end>{NUMBER_PATTERN}))?",
    re.IGNORECASE,
)


def add_deterministic_inferences(record: SermonRecord) -> SermonRecord:
    if not record.scripture_refs:
        refs = infer_primary_scripture_refs(record)
        if refs:
            record.scripture_refs = refs
            append_unique(record.questionable_claims, "Scripture reference was inferred from the title/transcript and should be reviewed.")
            append_unique(record.review_flags, "Review inferred scripture reference.")

    add_scripture_concordance(record)

    if not record.speaker:
        append_unique(record.review_flags, "Add or confirm speaker.")
    if not record.series:
        append_unique(record.review_flags, "Add or confirm series.")
    if record.transcript_status == "missing":
        append_unique(record.review_flags, "Transcript missing; page is metadata-only until a transcript is added.")
    return record


def infer_primary_scripture_refs(record: SermonRecord) -> list[str]:
    refs: list[str] = []
    refs = merge_unique(refs, extract_scripture_refs(record.series, include_book_only=True))
    refs = merge_unique(refs, extract_scripture_refs(record.title, include_book_only=True))
    refs = merge_unique(refs, extract_primary_transcript_refs(record.transcript_text[:5000]))
    return prefer_specific_primary_refs(refs)[:8]


def add_scripture_concordance(record: SermonRecord) -> None:
    """Populate transcript-wide Scripture references without changing the primary refs."""
    text_parts = [
        record.series,
        record.title,
        " ".join(record.scripture_refs),
        record.transcript_text,
    ]
    refs = extract_scripture_refs("\n".join(part for part in text_parts if part), include_book_only=True)
    refs = merge_unique(record.scripture_refs, refs)
    counts = Counter(extract_scripture_refs("\n".join(part for part in text_parts if part), include_book_only=True))
    for ref in record.scripture_refs:
        counts[ref] = max(counts.get(ref, 0), 1)
    record.mentioned_scripture_refs = refs
    record.scripture_ref_counts = {ref: counts.get(ref, 1) for ref in refs}


def infer_scripture_refs(text: str, max_refs: int | None = 5, include_book_only: bool = False) -> list[str]:
    return dedupe_refs(extract_scripture_refs(text, include_book_only=include_book_only), max_refs=max_refs)


def extract_scripture_refs(text: str, include_book_only: bool = False) -> list[str]:
    refs: list[str] = []
    if not text:
        return refs
    for match in SCRIPTURE_RE.finditer(text):
        ref = scripture_ref_from_match(match, text, include_book_only=include_book_only)
        if ref:
            refs.append(ref)
    refs.extend(extract_contextual_scripture_refs(text))
    return refs


def extract_primary_transcript_refs(text: str) -> list[str]:
    refs: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", text):
        lowered = sentence.casefold()
        if re.search(r"\b(next week|next month|later|eventually|in a few weeks)\b", lowered):
            continue
        if not re.search(
            r"\b(turn(?:ing)?|open(?: up)?|flip(?:ping)?|we(?:'re| are| will be| are going to be)\s+(?:going to be\s+)?in|our (?:text|passage)|today(?: we)?(?:'re| are)?\s+(?:in|looking at)|this morning(?: we)?(?:'re| are)?\s+(?:in|looking at))\b",
            lowered,
        ):
            continue
        refs = merge_unique(refs, extract_scripture_refs(sentence, include_book_only=True))
    return refs


def dedupe_refs(input_refs: list[str], max_refs: int | None = None) -> list[str]:
    refs: list[str] = []
    seen: set[str] = set()
    for ref in input_refs:
        if ref.casefold() in seen:
            continue
        seen.add(ref.casefold())
        refs.append(ref)
        if max_refs is not None and len(refs) >= max_refs:
            break
    return refs


def prefer_specific_primary_refs(refs: list[str]) -> list[str]:
    pruned: list[str] = []
    for ref in refs:
        book = book_only_ref(ref)
        if book and any(other.casefold().startswith(f"{book.casefold()} ") for other in refs):
            continue
        pruned.append(ref)
    return pruned


def book_only_ref(ref: str) -> str:
    canonical = normalize_book(ref)
    if ref.casefold() == canonical.casefold() and canonical in BIBLE_CHAPTER_COUNTS:
        return canonical
    return ""


def normalize_book(book: str) -> str:
    return BOOK_LOOKUP.get(_book_key(book), re.sub(r"\s+", " ", book.strip()).title())


def normalize_scripture_ref_text(value: str) -> str:
    refs = extract_scripture_refs(value, include_book_only=True)
    return refs[0] if refs else ""


def scripture_ref_from_match(match: re.Match[str], text: str, include_book_only: bool) -> str:
    book = normalize_book(match.group("book"))
    chapter = number_value(match.group("chapter") or "")
    if not chapter:
        if include_book_only and allows_book_only_reference(text, match):
            return book
        return ""
    verse = number_value(match.group("verse") or "")
    range_start = number_value(match.group("range_start") or "")
    range_end = number_value(match.group("range_end") or "")
    range_end_verse = number_value(match.group("range_end_verse") or "")
    verse_end = number_value(match.group("verse_end") or "")
    if not valid_chapter(book, chapter):
        return single_chapter_verse_ref(book, chapter, range_start)

    ref = f"{book} {chapter}"
    if verse:
        if not valid_verse_range(book, chapter, verse, chapter, verse_end or verse):
            return ""
        ref += f":{verse}"
        if verse_end:
            ref += f"-{verse_end}"
    elif range_start:
        separator = match.group("sep") or ""
        if range_end_verse and valid_chapter(book, range_end):
            if not valid_verse_range(book, chapter, range_start, range_end, range_end_verse):
                return ""
            ref += f":{range_start}-{range_end}:{range_end_verse}"
        elif ":" in separator or looks_like_sanitized_verse_range(match.group("tail") or ""):
            if not valid_verse_range(book, chapter, range_start, chapter, range_end or range_start):
                return ""
            ref += f":{range_start}"
            if range_end:
                ref += f"-{range_end}"
        elif single_chapter_book(book):
            ref = f"{book} {chapter}-{range_start}"
        else:
            if not valid_chapter(book, range_start):
                return ""
            ref += f"-{range_start}"
    return ref


def extract_contextual_scripture_refs(text: str) -> list[str]:
    refs: list[str] = []
    current_book = ""
    current_chapter = ""
    for segment in re.split(r"(?<=[.!?])\s+|\n+", text):
        if not segment.strip():
            continue
        explicit_matches = list(SCRIPTURE_RE.finditer(segment))
        explicit_spans = [match.span() for match in explicit_matches]
        for match in explicit_matches:
            book = normalize_book(match.group("book"))
            chapter = number_value(match.group("chapter") or "")
            if chapter and valid_chapter(book, chapter):
                current_book = book
                current_chapter = chapter
                nearby = contextual_verse_ref(segment, match.end(), book, chapter)
                if nearby:
                    refs.append(nearby)
            elif include_contextual_book(segment, match):
                current_book = book
                current_chapter = ""

        if current_book:
            for match in CONTEXT_CHAPTER_RE.finditer(segment):
                if overlaps_any(match.span(), explicit_spans):
                    continue
                chapter = number_value(match.group("chapter") or "")
                if not chapter or not valid_chapter(current_book, chapter):
                    continue
                verse = number_value(match.group("verse") or "")
                end_chapter = number_value(match.group("end_chapter") or "")
                end_verse = number_value(match.group("end_verse") or "")
                current_chapter = chapter
                if (
                    verse
                    and end_chapter
                    and end_verse
                    and valid_verse_range(current_book, chapter, verse, end_chapter, end_verse)
                ):
                    refs.append(f"{current_book} {chapter}:{verse}-{end_chapter}:{end_verse}")
                elif verse and valid_verse_range(current_book, chapter, verse, chapter, verse):
                    refs.append(f"{current_book} {chapter}:{verse}")
                elif end_chapter and valid_chapter(current_book, end_chapter):
                    refs.append(f"{current_book} {chapter}-{end_chapter}")
                else:
                    refs.append(f"{current_book} {chapter}")

        if current_book and current_chapter:
            for match in CONTEXT_VERSE_RE.finditer(segment):
                if overlaps_any(match.span(), explicit_spans):
                    continue
                verse = number_value(match.group("verse") or "")
                verse_end = number_value(match.group("verse_end") or "")
                if not verse or not valid_verse_range(current_book, current_chapter, verse, current_chapter, verse_end or verse):
                    continue
                ref = f"{current_book} {current_chapter}:{verse}"
                if verse_end:
                    ref += f"-{verse_end}"
                refs.append(ref)
    return refs


def contextual_verse_ref(segment: str, start: int, book: str, chapter: str) -> str:
    window = segment[start : start + 120]
    match = CONTEXT_VERSE_RE.search(window)
    if not match:
        return ""
    verse = number_value(match.group("verse") or "")
    verse_end = number_value(match.group("verse_end") or "")
    if not verse or not valid_verse_range(book, chapter, verse, chapter, verse_end or verse):
        return ""
    ref = f"{book} {chapter}:{verse}"
    if verse_end:
        ref += f"-{verse_end}"
    return ref


def include_contextual_book(segment: str, match: re.Match[str]) -> bool:
    return allows_book_only_reference(segment, match)


def valid_chapter(book: str, chapter: str) -> bool:
    try:
        value = int(chapter)
    except ValueError:
        return False
    return 1 <= value <= BIBLE_CHAPTER_COUNTS.get(book, 150)


def valid_verse_range(book: str, start_chapter: str, start_verse: str, end_chapter: str, end_verse: str) -> bool:
    try:
        start_chapter_value = int(start_chapter)
        end_chapter_value = int(end_chapter)
        start_verse_value = int(start_verse)
        end_verse_value = int(end_verse)
    except ValueError:
        return False
    if end_chapter_value < start_chapter_value:
        return False
    if start_chapter_value == end_chapter_value and end_verse_value < start_verse_value:
        return False
    return valid_verse(book, start_chapter_value, start_verse_value) and valid_verse(book, end_chapter_value, end_verse_value)


def valid_verse(book: str, chapter: int, verse: int) -> bool:
    if verse < 1:
        return False
    scripture_book = pythonbible_book(book)
    if bible is not None and scripture_book is not None:
        return bool(bible.is_valid_verse(scripture_book, chapter, verse))
    if single_chapter_book(book) and chapter == 1:
        return verse <= SINGLE_CHAPTER_VERSE_COUNTS.get(book, 99)
    return True


def pythonbible_book(book: str) -> object | None:
    if bible is None:
        return None
    enum_name = PYTHONBIBLE_BOOKS.get(book)
    if not enum_name:
        return None
    return getattr(bible.Book, enum_name, None)


def single_chapter_book(book: str) -> bool:
    return BIBLE_CHAPTER_COUNTS.get(book) == 1


def single_chapter_verse_ref(book: str, verse: str, verse_end: str = "") -> str:
    if not single_chapter_book(book):
        return ""
    try:
        start = int(verse)
        end = int(verse_end) if verse_end else start
    except ValueError:
        return ""
    max_verse = SINGLE_CHAPTER_VERSE_COUNTS.get(book, 99)
    if start < 1 or end < start or end > max_verse:
        return ""
    ref = f"{book} {start}"
    if end != start:
        ref += f"-{end}"
    return ref


def overlaps_any(span: tuple[int, int], spans: list[tuple[int, int]]) -> bool:
    start, end = span
    return any(start < other_end and end > other_start for other_start, other_end in spans)


def looks_like_sanitized_verse_range(tail: str) -> bool:
    return bool(re.search(r"\d\s+[\-\u2013]\s*\d", tail) or re.search(r"\d\s*[\-\u2013]\s*\d\s*[\-\u2013]\s*\d", tail))


def allows_book_only_reference(text: str, match: re.Match[str]) -> bool:
    whole = text.strip()
    if len(whole) <= 80 and _book_key(whole) in BOOK_LOOKUP:
        return True
    start, end = match.span()
    before = text[max(0, start - 72) : start].casefold()
    after = text[end : min(len(text), end + 72)].casefold()
    before_patterns = [
        r"(?:book|letter|gospel|prophecy|prophet|story|series|week(?:\s+\w+)?|preaching|sign)\s+of\s+$",
        r"(?:turn(?:ing)?|open(?: up)?(?: your bible)?|flip(?:ping)?|go(?:ing)?|walk(?:ing)?|study(?:ing)?|preach(?:ing|ed)?)\s+(?:to|through|from|on|in)\s+$",
        r"\b(?:in|from|through|throughout|inside)\s+$",
    ]
    after_patterns = [
        r"^\s+(?:chapter|chapters|verse|verses|series|sermon|week|part)\b",
    ]
    return any(re.search(pattern, before) for pattern in before_patterns) or any(
        re.search(pattern, after) for pattern in after_patterns
    )


def number_value(value: str) -> str:
    cleaned = value.strip().casefold()
    if not cleaned:
        return ""
    if cleaned.isdigit():
        return cleaned
    number = NUMBER_WORDS.get(cleaned)
    return str(number) if number is not None else ""


def append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def fields_from_frontmatter(data: dict[str, object]) -> dict[str, object]:
    scripture = data.get("scripture_refs") or data.get("scripture") or data.get("scripture_ref")
    return {
        "title": data.get("title") or "",
        "date": str(data.get("date") or ""),
        "speaker": data.get("speaker") or "",
        "series": data.get("series") or "",
        "scripture_refs": split_list(scripture),
        "topics": split_list(data.get("topics")),
        "themes": split_list(data.get("themes")),
        "youtube_url": data.get("youtube_url") or data.get("url") or "",
    }
