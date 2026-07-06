from sermon_archive_wiki.content_index import apply_content_index
from sermon_archive_wiki.models import SermonRecord


def test_content_index_generates_summary_labels_and_related_sermons() -> None:
    records = [
        SermonRecord(
            title="Prayer in Exile",
            date="2026-01-01",
            series="Daniel",
            scripture_refs=["Daniel 6"],
            transcript_text=(
                "Daniel prays faithfully even when the empire threatens him. "
                "Prayer forms courage because God's kingdom is more secure than the kingdoms of this world. "
                "The sermon calls the church to practice prayer, faith, and hope in public pressure."
            ),
            transcript_status="provided",
        ),
        SermonRecord(
            title="Courage Under Pressure",
            date="2026-01-08",
            series="Daniel",
            scripture_refs=["Daniel 3"],
            transcript_text=(
                "God gives courage to faithful people under pressure. "
                "The church learns hope, prayer, and trust when earthly kingdoms demand worship. "
                "This sermon invites disciples to resist idols and follow God with courage."
            ),
            transcript_status="provided",
        ),
        SermonRecord(
            title="Generosity and Treasure",
            date="2026-01-15",
            series="Wisdom",
            scripture_refs=["Matthew 6:19-24"],
            transcript_text=(
                "Jesus teaches about treasure, money, and generosity. "
                "The sermon calls the church to give freely because grace reshapes our desires. "
                "Generosity witnesses to the gospel in daily life."
            ),
            transcript_status="provided",
        ),
    ]

    result = apply_content_index(records, max_related_sermons=2, summary_sentences=2)

    assert result[0].summary_status == "deterministic_review_required"
    assert result[0].summary_source == "deterministic_content_index"
    assert result[0].generated_summary
    assert "Prayer" in result[0].themes or "Prayer" in result[0].topics
    assert "2026-01-08 - Courage Under Pressure" in result[0].related_sermons
