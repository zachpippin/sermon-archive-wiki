# Start Here For Agents

This repository is designed so a church volunteer can point Codex, Cowork,
Hermes, or another coding agent at it and say: "Install this for our church."

## The Short Version

```bash
./Install.command
source .venv/bin/activate
sermon-archive-wiki doctor
sermon-archive-wiki init
sermon-archive-wiki ingest --dry-run
sermon-archive-wiki ingest
```

Then stop and show the volunteer:

- `sermon-wiki-site/index.html`
- the generated vault folder
- `Review/Review Inbox.md`
- `review-report.md`

## What To Tell The Volunteer

"This will not publish anything. It creates a local website and Markdown vault
on this Mac. It can use transcripts, captions, audio files, YouTube metadata, and
`church-sermon-archivist` folders. Any optional AI summary will be clearly
tagged for review."

## What Not To Do

- Do not ask for YouTube passwords.
- Do not ask for website admin credentials.
- Do not upload the vault.
- Do not publish a static site.
- Do not use cloud AI unless the user explicitly configures an external command.
- Do not mark pages reviewed or canonical on behalf of a pastor.

## If Something Fails

Run:

```bash
sermon-archive-wiki doctor
```

Most failures are one of:

- Python 3.10+ is missing.
- `yt-dlp` is missing for live YouTube metadata fetches.
- Config paths point at folders that do not exist.
- There are audio files but no transcripts yet.
- The external summary command failed or returned invalid output.
