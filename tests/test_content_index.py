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


def test_content_index_avoids_opening_logistics_as_summary() -> None:
    record = SermonRecord(
        title="New Creation",
        date="2026-02-01",
        series="Revelation",
        scripture_refs=["Revelation 21:1-4"],
        transcript_text=(
            "Good morning. Grab a Bible and turn to Revelation 21. "
            "We are back in Revelation and you should be excited. "
            "The point of the passage is that God will remove the chaos of sin and make all things new. "
            "The sermon calls the church to endure present suffering because future resurrection glory is secure in Christ. "
            "There is a day coming when death, mourning, crying, and pain will be former things."
        ),
        transcript_status="provided",
    )

    result = apply_content_index([record], max_related_sermons=0, summary_sentences=2)

    assert "Grab a Bible" not in result[0].generated_summary
    assert "God will remove the chaos" in result[0].generated_summary


def test_content_index_preserves_external_summary_labels() -> None:
    record = SermonRecord(
        title="Sarai and Hagar",
        date="2018-10-28",
        series="Patriarchs",
        transcript_text="Marriage and family words appear in an illustration, but not as generated labels.",
        transcript_status="provided",
        generated_summary="AI summary.",
        summary_status="ai_generated_review_required",
        summary_source="external_command",
        themes=["Promise"],
        topics=["Suffering"],
    )

    result = apply_content_index([record], max_related_sermons=0, summary_sentences=2)

    assert result[0].themes == ["Promise"]
    assert result[0].topics == ["Suffering"]
    assert not any("Generated content summary" in flag for flag in result[0].review_flags)
