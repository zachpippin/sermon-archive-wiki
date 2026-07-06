from pathlib import Path
import sys

from sermon_archive_wiki.models import SermonRecord
from sermon_archive_wiki.summaries import apply_external_summary


def test_external_summary_command_tags_generated_summary() -> None:
    command = f"{sys.executable} scripts/example_summary_command.py"
    records = [
        SermonRecord(
            title="Ordinary Courage",
            date="2026-07-05",
            transcript_text="Joshua 1 says be strong and courageous.",
            transcript_status="provided",
        )
    ]

    summarized = apply_external_summary(records, command)

    assert summarized[0].summary_status == "ai_generated_review_required"
    assert "Ordinary Courage" in summarized[0].generated_summary
    assert "Courage" in summarized[0].themes
    assert summarized[0].questionable_claims
