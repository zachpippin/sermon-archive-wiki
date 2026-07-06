from sermon_archive_wiki.config import DEFAULT_CONFIG
from sermon_archive_wiki.models import SermonRecord
from sermon_archive_wiki.normalization import apply_name_normalization


def test_normalization_aliases_speakers_and_clears_church_values() -> None:
    config = {
        **DEFAULT_CONFIG,
        "church": {**DEFAULT_CONFIG["church"], "name": "Example Church"},
        "normalization": {
            "speaker_aliases": {
                "Jane Pastor": ["J. Pastor", "Pastor Jane"],
            },
            "ignored_speakers": ["Example Church Pastoral Team"],
        },
    }
    records = [
        SermonRecord(title="One", date="2026-01-01", speaker="J. Pastor"),
        SermonRecord(title="Two", date="2026-01-08", speaker="Example Church"),
        SermonRecord(title="Three", date="2026-01-15", speaker="Example Church Pastoral Team"),
    ]

    result = apply_name_normalization(records, config)

    assert result.records[0].speaker == "Jane Pastor"
    assert result.records[1].speaker == ""
    assert result.records[2].speaker == ""
    assert len(result.changes) == 3


def test_normalization_moves_scripture_from_speaker_to_scripture_refs() -> None:
    config = {**DEFAULT_CONFIG, "normalization": {}}
    records = [SermonRecord(title="Misfiled", date="2026-01-01", speaker="1 Peter 2:11-12")]

    result = apply_name_normalization(records, config)

    assert result.records[0].speaker == ""
    assert result.records[0].scripture_refs == ["1 Peter 2:11-12"]
    assert "confirm the missing speaker" in result.records[0].review_flags[0]


def test_normalization_rejects_non_scripture_frontmatter_values() -> None:
    config = {**DEFAULT_CONFIG, "normalization": {}}
    records = [
        SermonRecord(
            title="The Law",
            date="2026-01-01",
            scripture_refs=["The", "Jesus", "1 Cor 15", "Exodus 21-23"],
        )
    ]

    result = apply_name_normalization(records, config)

    assert result.records[0].scripture_refs == ["1 Corinthians 15", "Exodus 21-23"]
    assert any(change["value"] == "The" for change in result.changes)
    assert any(warning["value"] == "Jesus" for warning in result.warnings)
    assert result.records[0].review_flags == []


def test_normalization_corrects_configured_annual_series_from_title_date() -> None:
    config = {
        **DEFAULT_CONFIG,
        "normalization": {
            "annual_series_patterns": [
                {
                    "canonical": "giv {year}",
                    "aliases": ["giv", "|giv|"],
                    "require_week": True,
                    "override_existing": True,
                }
            ],
        },
    }
    records = [SermonRecord(title="|giv| Week 3", date="2025-12-14", series="giv 2022", review_flags=["Add or confirm series."])]

    result = apply_name_normalization(records, config)

    assert result.records[0].series == "giv 2025"
    assert any(change["replacement"] == "giv 2025" for change in result.changes)
    assert "Add or confirm series." not in result.records[0].review_flags
    assert any("Series was corrected from giv 2022 to giv 2025" in flag for flag in result.records[0].review_flags)


def test_normalization_canonicalizes_annual_series_display_text() -> None:
    config = {
        **DEFAULT_CONFIG,
        "normalization": {
            "annual_series_patterns": [
                {
                    "canonical": "giv {year}",
                    "aliases": ["giv", "|giv|"],
                    "require_week": True,
                    "override_existing": True,
                }
            ],
        },
    }
    records = [SermonRecord(title="|giv| Week 1", date="2022-11-27", series="|giv| 2022")]

    result = apply_name_normalization(records, config)

    assert result.records[0].series == "giv 2022"
    assert not result.records[0].review_flags


def test_normalization_handles_annual_series_aliases_from_existing_series() -> None:
    config = {
        **DEFAULT_CONFIG,
        "normalization": {
            "annual_series_patterns": [
                {
                    "canonical": "giv {year}",
                    "aliases": ["giv", "lgivl"],
                    "require_week": True,
                }
            ],
        },
    }
    records = [SermonRecord(title="Light in the Darkness", date="2018-11-25", series="lgivl 2018")]

    result = apply_name_normalization(records, config)

    assert result.records[0].series == "giv 2018"


def test_normalization_infers_series_from_title_patterns_and_scripture_book_titles() -> None:
    config = {
        **DEFAULT_CONFIG,
        "normalization": {
            "title_series_patterns": [
                {
                    "pattern": r"^Re:Member\b",
                    "series": "Re:Member",
                }
            ],
            "infer_scripture_book_series_from_title": True,
        },
    }
    records = [
        SermonRecord(title="Re:Member Core Practices I", date="2025-10-12"),
        SermonRecord(title="2 Samuel 11", date="2026-04-19"),
    ]

    result = apply_name_normalization(records, config)

    assert [record.series for record in result.records] == ["Re:Member", "2 Samuel"]
