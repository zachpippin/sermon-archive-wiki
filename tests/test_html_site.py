from pathlib import Path

from sermon_archive_wiki.config import DEFAULT_CONFIG
from sermon_archive_wiki.html_site import write_html_site
from sermon_archive_wiki.importers import collect_records
from sermon_archive_wiki.inference import add_deterministic_inferences
from sermon_archive_wiki.models import SermonRecord


def test_html_site_writes_chrome_openable_pages(tmp_path: Path) -> None:
    records = collect_records(
        transcript_dirs=[Path("examples/fixtures/transcripts")],
        catalog_paths=[Path("examples/catalog.example.csv")],
    )
    config = DEFAULT_CONFIG.copy()
    config["church"] = {**DEFAULT_CONFIG["church"], "name": "Example Church"}

    result = write_html_site(records, tmp_path, config)

    index = tmp_path / "index.html"
    sermon = tmp_path / "sermons" / "2026-07-05-ordinary-courage.html"
    assert index.exists()
    assert sermon.exists()
    assert result["index_path"].endswith("index.html")
    assert "Example Church Sermon Archive" in index.read_text(encoding="utf-8")
    assert 'data-sortable' in index.read_text(encoding="utf-8")
    assert "data-sort-initial" in index.read_text(encoding="utf-8")
    assert "Ordinary Courage" in sermon.read_text(encoding="utf-8")
    assert "Private local files. Not published." in sermon.read_text(encoding="utf-8")


def test_html_review_page_lists_actionable_items(tmp_path: Path) -> None:
    records = collect_records(caption_dirs=[Path("examples/fixtures/captions")])

    write_html_site(records, tmp_path, DEFAULT_CONFIG)

    review = (tmp_path / "review" / "index.html").read_text(encoding="utf-8")
    assert "Review Inbox" in review
    assert "Review inferred scripture reference." in review


def test_html_category_indexes_are_count_sortable(tmp_path: Path) -> None:
    records = collect_records(
        transcript_dirs=[Path("examples/fixtures/transcripts")],
        catalog_paths=[Path("examples/catalog.example.csv")],
    )

    write_html_site(records, tmp_path, DEFAULT_CONFIG)

    speakers = (tmp_path / "speakers" / "index.html").read_text(encoding="utf-8")
    assert "<th" in speakers
    assert "Sermons" in speakers
    assert 'data-sort-initial="1:desc"' in speakers


def test_html_scripture_index_uses_transcript_concordance(tmp_path: Path) -> None:
    record = SermonRecord(
        title="A Prayer from the Deep",
        date="2015-03-15",
        speaker="Raz Bradley",
        series="Jonah",
        transcript_text="Turn to Jonah chapter 2. Jesus references the sign of Jonah in Matthew 12:40.",
        transcript_status="provided",
    )
    add_deterministic_inferences(record)

    write_html_site([record], tmp_path, DEFAULT_CONFIG)

    scripture = (tmp_path / "scripture" / "index.html").read_text(encoding="utf-8")
    jonah = (tmp_path / "scripture" / "jonah-2.html").read_text(encoding="utf-8")
    assert "Mentions" in scripture
    assert 'aria-label="About Mentions"' in scripture
    assert "Total deterministic matches" in scripture
    assert 'aria-label="About Primary"' in scripture
    assert 'data-sort-initial="2:desc"' in scripture
    assert ">Jonah 2<" in scripture
    assert "A Prayer from the Deep" in jonah
    assert "Primary" in jonah


def test_html_scripture_index_surfaces_frequent_specific_passages(tmp_path: Path) -> None:
    records = [
        SermonRecord(
            title="New Creation One",
            date="2024-01-07",
            speaker="Jane Pastor",
            transcript_text="Turn to Revelation 21:1-4.",
            transcript_status="provided",
        ),
        SermonRecord(
            title="New Creation Two",
            date="2024-01-14",
            speaker="Jane Pastor",
            transcript_text="The hope of Revelation 21:1-4 keeps showing up.",
            transcript_status="provided",
        ),
    ]
    for record in records:
        add_deterministic_inferences(record)

    write_html_site(records, tmp_path, DEFAULT_CONFIG)

    scripture = (tmp_path / "scripture" / "index.html").read_text(encoding="utf-8")
    assert "Frequent Specific Passages" in scripture
    assert "Revelation 21:1-4" in scripture
    assert "Repeated passage" in scripture
