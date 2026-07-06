from sermon_archive_wiki.models import SermonRecord
from sermon_archive_wiki.scripture_index import ScriptureEntry, scripture_flag, scripture_refs_for_record


def test_scripture_index_prunes_broad_book_when_specific_passage_exists() -> None:
    record = SermonRecord(
        title="The Trumpets",
        scripture_refs=["Revelation"],
        mentioned_scripture_refs=["Revelation", "Revelation 8:6-9:21"],
        scripture_ref_counts={"Revelation": 3, "Revelation 8:6-9:21": 2},
    )

    refs = scripture_refs_for_record(record)

    assert "Revelation 8:6-9:21" in refs
    assert "Revelation" not in refs


def test_scripture_index_keeps_broad_book_when_no_specific_context_exists() -> None:
    record = SermonRecord(
        title="Apocalypse and Hope",
        mentioned_scripture_refs=["Revelation"],
        scripture_ref_counts={"Revelation": 1},
    )

    assert scripture_refs_for_record(record) == ["Revelation"]


def test_scripture_flag_surfaces_repeated_specific_passages() -> None:
    first = SermonRecord(title="First", mentioned_scripture_refs=["Revelation 21:1-4"])
    second = SermonRecord(title="Second", mentioned_scripture_refs=["Revelation 21:1-4"])
    entries = [
        ScriptureEntry("Revelation 21:1-4", first, mentions=1, primary=False),
        ScriptureEntry("Revelation 21:1-4", second, mentions=1, primary=False),
    ]

    assert scripture_flag("Revelation 21:1-4", entries) == "Repeated passage"
