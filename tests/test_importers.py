from pathlib import Path

from sermon_archive_wiki.importers import (
    collect_records,
    merge_records,
    record_from_transcript_file,
    records_from_archivist_archive,
    records_from_transcript_dir,
)
from sermon_archive_wiki.models import SermonRecord


def test_imports_church_sermon_archivist_archive() -> None:
    records = records_from_archivist_archive(Path("examples/fixtures/archivist_archive"))

    assert len(records) == 1
    record = records[0]
    assert record.title == "Ordinary Courage"
    assert record.youtube_id == "example123"
    assert record.transcript_status == "provided"
    assert "Joshua 1:1-9" in record.transcript_text


def test_collect_records_merges_catalog_transcript_youtube_and_archivist() -> None:
    records = collect_records(
        transcript_dirs=[Path("examples/fixtures/transcripts")],
        catalog_paths=[Path("examples/catalog.example.csv")],
        youtube_metadata_paths=[Path("examples/fixtures/youtube/video.json")],
        archivist_archive_dir=Path("examples/fixtures/archivist_archive"),
    )

    assert len(records) == 1
    record = records[0]
    assert record.speaker == "Jane Pastor"
    assert record.series == "Ordinary Faith"
    assert record.scripture_refs == ["Joshua 1:1-9"]
    assert record.audio_files
    assert record.youtube_url == "https://www.youtube.com/watch?v=example123"


def test_transcript_file_reads_leading_author_and_series_metadata(tmp_path: Path) -> None:
    transcript = tmp_path / "2026-07-05_2_Samuel_21.txt"
    transcript.write_text(
        "Title: 2 Samuel 21\n"
        "Date: 2026-07-05\n"
        "Author: Chet Phillips\n"
        "Series: 2 Samuel\n"
        "Squarespace URL: /sermons-1/example\n"
        "\n"
        "---\n"
        "\n"
        "Open your Bible to 2 Samuel 21.\n",
        encoding="utf-8",
    )

    record = record_from_transcript_file(transcript)

    assert record.speaker == "Chet Phillips"
    assert record.series == "2 Samuel"
    assert "/sermons-1/example" in record.source_files
    assert "Author:" not in record.transcript_text
    assert record.transcript_text.startswith("Open your Bible")


def test_transcript_file_prefers_leading_title_metadata(tmp_path: Path) -> None:
    transcript = tmp_path / "2024-09-29_Revelation_86-921.txt"
    transcript.write_text(
        "Title: Revelation 8:6-9:21\n"
        "Date: 2024-09-29\n"
        "Author: Spencer Cary\n"
        "\n"
        "---\n"
        "\n"
        "Turn to Revelation 8:6-9:21.\n",
        encoding="utf-8",
    )

    record = record_from_transcript_file(transcript)

    assert record.title == "Revelation 8:6-9:21"


def test_transcript_dir_skips_work_logs(tmp_path: Path) -> None:
    (tmp_path / "transcription_log.txt").write_text("2026-01-01\tExodus 20:14\tcomplete\n", encoding="utf-8")
    (tmp_path / "2026-01-01_Sermon.txt").write_text("Please turn to Romans 8.\n", encoding="utf-8")

    records = records_from_transcript_dir(tmp_path)

    assert [record.title for record in records] == ["Sermon"]


def test_merge_records_does_not_merge_recurring_titles_across_years() -> None:
    records = merge_records(
        [
            SermonRecord(title="|giv| Week 1", date="2022-11-27", series="giv 2022"),
            SermonRecord(title="|giv| Week 1", date="2025-11-30", speaker="Chet Phillips"),
        ]
    )

    assert len(records) == 2
    assert [(record.date, record.series) for record in records] == [
        ("2022-11-27", "giv 2022"),
        ("2025-11-30", ""),
    ]


def test_merge_records_can_merge_same_year_title_variants() -> None:
    records = merge_records(
        [
            SermonRecord(title="|giv| Week 1: Refiner and the Unjust", date="2023-11-26", speaker="Chet Phillips"),
            SermonRecord(
                title="giv Week 1 Refiner and the Unjust",
                date="2023-11-27",
                transcript_text="Transcript text.",
                transcript_status="provided",
            ),
        ]
    )

    assert len(records) == 1
    assert records[0].speaker == "Chet Phillips"
    assert records[0].transcript_text == "Transcript text."


def test_merge_records_keeps_incoming_aliases_after_merge() -> None:
    records = merge_records(
        [
            SermonRecord(title="|giv| Week 1: Refiner and the Unjust", date="2023-11-26", speaker="Chet Phillips"),
            SermonRecord(
                title="giv Week 1 Refiner and the Unjust",
                date="2023-11-27",
                transcript_text="Clean transcript.",
                transcript_status="provided",
            ),
            SermonRecord(
                title="giv Week 1 Refiner and the Unjust (2023 11 27)",
                date="2023-11-27",
                transcript_text="Generated wiki page, not the transcript.",
                transcript_status="provided",
            ),
        ]
    )

    assert len(records) == 1
    assert records[0].transcript_text == "Clean transcript."
