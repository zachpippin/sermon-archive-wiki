from pathlib import Path

from sermon_archive_wiki.captions import caption_text


def test_caption_text_strips_vtt_timestamps() -> None:
    text = caption_text(Path("examples/fixtures/captions/2026-07-12_Patient_Faith.vtt"))

    assert "WEBVTT" not in text
    assert "-->" not in text
    assert "Good morning church." in text
    assert "James 1" in text
