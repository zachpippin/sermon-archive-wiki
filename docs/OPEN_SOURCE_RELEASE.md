# Open Source Release Checklist

Use this checklist before publishing or tagging a public release.

## Privacy Boundary

- Do not commit a church's generated `sermon-wiki-site*/`, `sermon-wiki-vault*/`,
  or `reports*/` folders.
- Do not commit `sermon-archive-wiki.yml`, `*.local.yml`, or any config file
  that points at private local paths.
- Keep examples synthetic and church-agnostic.
- Do not include transcripts, audio, screenshots, YouTube exports, or catalog
  rows from a real church unless that church has explicitly approved public
  release.

## Preflight Commands

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
sermon-archive-wiki doctor --config examples/sermon-archive-wiki.example.yml --strict
pytest
```

Run the example ingest locally. In a clean checkout, a full ingest is fine:

```bash
sermon-archive-wiki ingest \
  --config examples/sermon-archive-wiki.example.yml \
  --no-summary-pass \
  --content-pass
```

If your default output folders currently contain private church test output,
use a dry run or temporary output folders instead:

```bash
sermon-archive-wiki ingest \
  --config examples/sermon-archive-wiki.example.yml \
  --no-summary-pass \
  --content-pass \
  --dry-run
```

After a full ingest, confirm the generated site opens:

```bash
open sermon-wiki-site/index.html
```

## Leak Scan

Before pushing, run a basic scan for local/private strings:

```bash
rg -n "Zach|Mill City|/Users/|Tailscale|taildc|100\\." \
  --glob '!sermon-wiki-site*/**' \
  --glob '!sermon-wiki-vault*/**' \
  --glob '!reports*/**' \
  --glob '!.venv/**' \
  --glob '!.git/**'
```

Expected public matches should be limited to author/license metadata or docs
that intentionally describe the release process.

## Release Notes

For the first public release, mention:

- Local-first static HTML and Obsidian vault generation.
- Draft-only pastor review workflow.
- Deterministic parsing and optional vendor-agnostic summary command.
- Sortable indexes for sermons, speakers, series, scripture, themes, and
  review status.
- Configurable naming and series normalization.
- Direct import support for `church-sermon-archivist` folders.
