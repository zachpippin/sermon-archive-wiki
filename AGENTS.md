# Agent Instructions

You are helping a church volunteer install and run Sermon Archive Wiki.
Assume the user is not a developer. Keep the workflow calm, explicit, and
reversible.

## Product Boundary

This tool only creates local files:

- a private static HTML website
- an Obsidian-compatible sermon vault
- sermon pages
- index pages
- review inbox and review report

Do not publish to a website, upload media, delete source files, or ask for
passwords/API keys. Do not use cloud LLMs unless the user explicitly configures
an external summary command.

## First Actions

1. Read this file and `START_HERE_FOR_AGENTS.md`.
2. Run `sermon-archive-wiki doctor` if the package is installed.
3. If the package is not installed, follow `docs/MAC_INSTALL.md` or run
   `./Install.command` from the repo root.
4. Ask only the minimum setup questions listed below.
5. Run `sermon-archive-wiki init`.
6. Run `sermon-archive-wiki ingest --dry-run`.
7. Ask whether the volunteer wants the optional summary pass for cross-reference
   purposes.
8. Run `sermon-archive-wiki ingest`.
9. Show the volunteer `sermon-wiki-site/index.html`, the generated vault path,
   `Review/Review Inbox.md`, and `review-report.md`.

## Clarifying Questions

Ask for these if they are not already known:

- Church name.
- Where the local HTML website should be written.
- Where the Obsidian vault should be written.
- Where transcript files live.
- Where saved sermon-page HTML files live, if any.
- Where caption files live, if any.
- Where sermon audio files live, if any.
- Whether there is a CSV/YAML catalog.
- Whether there are YouTube URLs or exported YouTube metadata JSON files.
- Whether there is a `church-sermon-archivist/archive` folder to import.
- Whether to run an optional AI summary pass for cross-reference purposes.
- If yes, what external summary command should be used.

## Safe Commands

Use these commands from the repo root:

```bash
source .venv/bin/activate
sermon-archive-wiki doctor
sermon-archive-wiki init
sermon-archive-wiki ingest --dry-run
sermon-archive-wiki ingest
sermon-archive-wiki update
```

## Expected Deliverables

At the end of an install, report:

- Whether local tools are installed.
- Config path.
- Local website path and `index.html` link.
- Vault path.
- Input sources discovered.
- Whether the optional summary pass ran.
- Where the review inbox and review report are.
- Any missing transcripts or metadata the pastor should review first.
