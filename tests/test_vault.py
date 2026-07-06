from pathlib import Path

from sermon_archive_wiki.config import DEFAULT_CONFIG
from sermon_archive_wiki.importers import collect_records
from sermon_archive_wiki.models import SermonRecord
from sermon_archive_wiki.vault import write_vault


def test_vault_writes_draft_pages_and_review_indexes(tmp_path: Path) -> None:
    records = collect_records(
        transcript_dirs=[Path("examples/fixtures/transcripts")],
        catalog_paths=[Path("examples/catalog.example.csv")],
    )
    config = DEFAULT_CONFIG.copy()
    config["paths"] = {**DEFAULT_CONFIG["paths"], "vault_dir": str(tmp_path)}

    write_vault(records, tmp_path, config)

    sermon_page = tmp_path / "Sermons" / "2026-07-05 - Ordinary Courage.md"
    assert sermon_page.exists()
    text = sermon_page.read_text(encoding="utf-8")
    assert "status: draft" in text
    assert "review_status: draft" in text
    assert "mentioned_scripture_refs:" in text
    assert "> [!warning] Review needed" not in text
    assert "[[Jane Pastor]]" in text
    assert (tmp_path / "Review" / "Review Inbox.md").exists()
    assert (tmp_path / "Series" / "Series Index.md").exists()
    assert "| Scripture | Sermons | Mentions | Primary | First | Latest |" in (
        tmp_path / "Scripture" / "Scripture Index.md"
    ).read_text(encoding="utf-8")


def test_vault_marks_missing_metadata_for_review(tmp_path: Path) -> None:
    records = collect_records(caption_dirs=[Path("examples/fixtures/captions")])
    config = DEFAULT_CONFIG.copy()
    config["paths"] = {**DEFAULT_CONFIG["paths"], "vault_dir": str(tmp_path)}

    write_vault(records, tmp_path, config)

    sermon_page = tmp_path / "Sermons" / "2026-07-12 - Patient Faith.md"
    text = sermon_page.read_text(encoding="utf-8")
    assert "> [!warning] Review needed" in text
    assert "Review inferred scripture reference." in text


def test_vault_sanitizes_pipe_characters_in_wikilink_labels(tmp_path: Path) -> None:
    records = [SermonRecord(title="|giv| Week 1", date="2025-11-30", speaker="Chet Phillips", series="giv 2025")]
    config = DEFAULT_CONFIG.copy()
    config["paths"] = {**DEFAULT_CONFIG["paths"], "vault_dir": str(tmp_path)}

    write_vault(records, tmp_path, config)

    series_page = (tmp_path / "Series" / "giv 2025.md").read_text(encoding="utf-8")
    assert "||giv|" not in series_page
    assert "[[2025-11-30 - giv Week 1|giv Week 1]]" in series_page
