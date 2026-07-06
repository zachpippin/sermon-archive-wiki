# Configuration

The default config file is `sermon-archive-wiki.yml`.

```yaml
church:
  name: Example Church
  timezone: America/New_York
paths:
  vault_dir: sermon-wiki-vault
  site_dir: sermon-wiki-site
  reports_dir: reports
  transcript_dirs:
    - sermon-transcripts
  caption_dirs:
    - captions
  audio_dirs:
    - audio
  catalog_paths:
    - sermons.csv
  youtube_metadata_paths:
    - youtube-metadata.json
  youtube_urls_file: youtube-urls.txt
  archivist_archive_dir: ../church-sermon-archivist/archive
summary:
  enabled: false
  ask_during_ingest: true
  external_command: ""
content_index:
  enabled: false
  max_related_sermons: 5
  summary_sentences: 3
normalization:
  speaker_aliases:
    Jane Pastor:
      - Pastor Jane
      - J. Pastor
  series_aliases: {}
  annual_series_patterns: []
  title_series_patterns: []
  infer_scripture_book_series_from_title: true
  scripture_aliases: {}
  theme_aliases: {}
  ignored_speakers:
    - Example Church
output:
  include_html_site: true
  include_full_transcripts: true
  transcript_excerpt_chars: 0
```

## Input Priority

The tool merges records that share a YouTube ID, YouTube URL, date/title, or
same-year title. The same-year title fallback helps merge catalog rows with
transcript files when one source is off by a day, without merging recurring
seasonal titles across different years.

Useful sources:

- CSV/YAML catalog for known metadata.
- Transcript `.txt` or `.md` files for sermon body text.
- Caption `.srt` or `.vtt` files for caption-derived transcript text.
- Audio files for source tracking.
- YouTube metadata JSON from `yt-dlp`.
- `church-sermon-archivist/archive` folders.

## Scripture Concordance

`scripture_refs` is reserved for primary or explicit sermon texts. The ingest
also scans transcript text deterministically and writes
`mentioned_scripture_refs` plus `scripture_ref_counts` so pastors can find
sermons that reference a book or passage even when that passage was not the
main sermon text.

The local HTML Scripture index is sortable by:

- sermons that mention the reference
- total detected mentions
- primary sermon texts
- first and latest sermon dates

## Local Content Index

The optional `content_index` pass is deterministic and local. It creates
review-required extractive summaries, controlled topic/theme labels, and
related-sermon suggestions from the whole discovered corpus. It does not call
an AI service or publish anything.

Run it explicitly with:

```bash
sermon-archive-wiki ingest --content-pass
```

## Naming Normalization

Use `normalization` when old catalogs, transcripts, or website metadata use
inconsistent names.

Alias maps can be written as `canonical: [aliases]`:

```yaml
normalization:
  speaker_aliases:
    Spencer Cary:
      - Spencer Carey
      - Spencer Clay
    Chet Phillips:
      - Chet Philips
  ignored_speakers:
    - Example Church
    - Example Church Pastoral Team
```

The ingest also clears obvious non-person speaker values when they look like a
scripture reference or the configured church name. Cleared values are sent to
the review inbox.

Recurring annual series can be normalized with `annual_series_patterns`. This
is useful when a church repeats a giving, Advent, mission, or vision series
every year and source metadata sometimes omits the year or carries a stale
series value.

```yaml
normalization:
  annual_series_patterns:
    - canonical: "Advent {year}"
      aliases:
        - Advent
        - Christmas
      require_week: false
      override_existing: true
```

Title patterns can fill blank series values from local naming conventions:

```yaml
normalization:
  title_series_patterns:
    - pattern: '^Membership Class\b'
      series: Membership Class
```

By default, titles that begin with a Bible book and chapter, such as
`Romans 8` or `2 Samuel 11`, are treated as book-series candidates when the
series field is blank. Set `infer_scripture_book_series_from_title: false` to
disable that fallback.

After each ingest, check:

```text
reports/naming-report.md
```

It lists applied aliases and possible duplicate names that still need review.

## Frontmatter Schema

Generated sermon pages include:

```yaml
title:
date:
speaker:
series:
scripture_refs:
mentioned_scripture_refs:
scripture_ref_counts:
source_files:
audio_files:
youtube_url:
transcript_status:
status: draft
review_status: draft
summary_status:
questionable_claims:
review_flags:
```

V1 always writes draft pages. Churches can promote pages locally after review.
