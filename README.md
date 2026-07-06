# Sermon Archive Wiki

Local-first sermon archive wiki builder for churches.

Sermon Archive Wiki takes a church's existing sermon archive -- transcripts,
caption files, audio files, YouTube metadata, CSV/YAML catalogs, and
`church-sermon-archivist` output folders -- and generates a private
Chrome-openable HTML website plus an Obsidian-compatible Markdown vault for
pastoral review.

V1 does not publish anything. It creates local files only, including an
`index.html` a volunteer can open like a private church archive website.

## What It Does

- Creates a local static HTML website that opens in Chrome.
- Creates one Markdown page per sermon.
- Adds sortable HTML tables for sermon, speaker, series, scripture, theme, and
  review indexes.
- Builds the Scripture index as a transcript-aware concordance, with separate
  counts for sermons, detected mentions, and primary sermon texts.
- Validates detected Bible chapters and verses, keeps generic book mentions as
  broad rows, and surfaces repeated specific passages for review.
- Can run a local deterministic content pass for review summaries, topics,
  themes, and related-sermon suggestions.
- Writes Obsidian-style wikilinks between sermons, series, speakers,
  scripture passages, topics, themes, and related sermon suggestions.
- Creates index pages for series, speakers, scripture, themes, and review
  status.
- Writes `Review/Review Inbox.md` and `review-report.md`.
- Starts every generated page as `status: draft` and `review_status: draft`.
- Marks inferred or uncertain claims in frontmatter, inline warning callouts,
  and the review inbox.
- Supports local name normalization aliases and writes a naming QA report.
- Supports configurable annual-series and title-pattern normalization so
  recurring series names do not merge across years by accident.
- Clearly labels AI-generated summaries when an optional external summary
  command is configured.
- Imports `church-sermon-archivist` archive folders directly.

## Quick Start

For a volunteer-friendly Mac install, double-click:

```bash
./Install.command
```

Manual install:

```bash
git clone https://github.com/zachpippin/sermon-archive-wiki.git
cd sermon-archive-wiki

python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .

sermon-archive-wiki doctor
sermon-archive-wiki init
sermon-archive-wiki ingest
```

Then open the local website:

```bash
open sermon-wiki-site/index.html
```

Agent-guided install:

```text
Read AGENTS.md and help me install Sermon Archive Wiki for my church.
Keep everything local. Ask whether to run the optional summary pass.
```

## Common Inputs

```bash
sermon-archive-wiki ingest \
  --catalog examples/catalog.example.csv \
  --transcripts examples/fixtures/transcripts \
  --captions examples/fixtures/captions \
  --audio examples/fixtures/audio \
  --youtube-metadata examples/fixtures/youtube/video.json \
  --archivist-archive examples/fixtures/archivist_archive \
  --vault sermon-wiki-vault
```

## Output

```text
sermon-wiki-site/
  index.html
  sermons/
  series/
  speakers/
  scripture/
  themes/
  review/

sermon-wiki-vault/
  Home.md
  Sermons/
  Series/
  Speakers/
  Scripture/
  Themes/
  Review/
    Review Inbox.md
    Review Status.md
  review-report.md
```

## AI Boundary

Deterministic parsing runs first. The optional summary pass is vendor-agnostic:
you provide an external command, and the tool sends sermon JSON to stdin. The
command may call a local model, a cloud model, or nothing at all. Any output is
tagged as AI-generated and review-required.

## Companion Project

`church-sermon-archivist` creates local audio/transcript archive folders.
`sermon-archive-wiki` turns those folders, plus any other church archive
sources, into a private website and Markdown review vault.

See [church-sermon-archivist integration](docs/CHURCH_SERMON_ARCHIVIST_INTEGRATION.md).

## Open Source Release

Before publishing, run the checklist in
[Open Source Release Checklist](docs/OPEN_SOURCE_RELEASE.md). The repo ignores
local generated sites, vaults, reports, and `*.local.yml` configs so churches
can test privately without committing their archive data.

## License

MIT
