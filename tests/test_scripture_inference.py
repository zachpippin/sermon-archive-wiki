from sermon_archive_wiki.inference import add_deterministic_inferences, extract_scripture_refs, infer_scripture_refs
from sermon_archive_wiki.models import SermonRecord


def test_extracts_book_level_and_abbreviated_scripture_refs() -> None:
    text = "Open your Bible to the book of Jonah. Later we will look at 1 Cor 15 and Matthew 12:38-45."

    refs = extract_scripture_refs(text, include_book_only=True)

    assert "Jonah" in refs
    assert "1 Corinthians 15" in refs
    assert "Matthew 12:38-45" in refs


def test_book_only_refs_need_context() -> None:
    assert infer_scripture_refs("John said hello", include_book_only=True) == []
    assert infer_scripture_refs("Turn to John", include_book_only=True) == ["John"]


def test_deterministic_inference_builds_transcript_concordance() -> None:
    record = SermonRecord(
        title="A Prayer from the Deep",
        date="2015-03-15",
        series="Jonah",
        transcript_text="We are in week two of Jonah. Turn to Jonah chapter 2. Jesus also says this in Matthew 12:40.",
        transcript_status="provided",
    )

    add_deterministic_inferences(record)

    assert record.scripture_refs[0] == "Jonah 2"
    assert "Jonah 2" in record.mentioned_scripture_refs
    assert "Matthew 12:40" in record.mentioned_scripture_refs
    assert record.scripture_ref_counts["Jonah 2"] >= 1


def test_outline_numbers_do_not_become_chapters() -> None:
    refs = extract_scripture_refs("The sailors respond better than Jonah. 17. And the Lord appointed a fish.", include_book_only=True)

    assert "Jonah 17" not in refs


def test_future_series_announcement_is_referenced_not_primary() -> None:
    record = SermonRecord(
        title="Groups that Multiply",
        date="2015-03-01",
        series="Anchor",
        transcript_text="Next week, we're going to start walking verse by verse through the book of Jonah.",
        transcript_status="provided",
    )

    add_deterministic_inferences(record)

    assert "Jonah" not in record.scripture_refs
    assert "Jonah" in record.mentioned_scripture_refs


def test_four_digit_years_do_not_become_scripture_chapters() -> None:
    assert extract_scripture_refs("Exodus 2022", include_book_only=True) == []


def test_extracts_cross_chapter_verse_ranges() -> None:
    refs = extract_scripture_refs("Title: Revelation 8:6-9:21", include_book_only=True)

    assert "Revelation 8:6-9:21" in refs


def test_invalid_chapters_do_not_become_scripture_refs() -> None:
    refs = extract_scripture_refs(
        "Revelation 129 is not a passage. Jude 202 is not either. "
        "Revelation 3:174, Revelation 7:30, and 1 Corinthians 11:46 are also bad.",
        include_book_only=True,
    )

    assert "Revelation 129" not in refs
    assert "Jude 202" not in refs
    assert "Revelation 3:174" not in refs
    assert "Revelation 7:30" not in refs
    assert "1 Corinthians 11:46" not in refs


def test_contextual_chapter_and_verse_mentions_are_linked() -> None:
    refs = extract_scripture_refs(
        "Grab a Bible and go to Revelation chapter 8. We are starting in verse 6.",
        include_book_only=True,
    )

    assert "Revelation 8" in refs
    assert "Revelation 8:6" in refs


def test_single_chapter_book_ranges_are_treated_as_verses() -> None:
    refs = extract_scripture_refs("Jude 17-23 is a common warning text.", include_book_only=True)

    assert "Jude 17-23" in refs
