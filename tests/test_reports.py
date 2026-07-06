from pathlib import Path

from sermon_archive_wiki.models import SermonRecord
from sermon_archive_wiki.reports import write_completeness_report


def test_completeness_report_flags_audio_without_transcript_or_summary(tmp_path: Path) -> None:
    records = [
        SermonRecord(
            title="Audio Only",
            date="2026-07-05",
            audio_files=["https://example.test/audio.mp3"],
            transcript_status="catalog-listed",
        ),
        SermonRecord(
            title="Complete",
            date="2026-07-12",
            audio_files=["https://example.test/complete.mp3"],
            transcript_text="Turn to Romans 8.",
            transcript_status="provided",
            generated_summary="Romans 8 gives hope.",
        ),
    ]

    report_path = tmp_path / "completeness-report.md"
    write_completeness_report(report_path, records)

    text = report_path.read_text(encoding="utf-8")
    assert "- Audio pages missing transcript text: 1" in text
    assert "- Audio pages missing generated summaries: 1" in text
    assert "Audio present but transcript text missing" in text
    assert "Catalog lists a transcript" in text
