# External Summary Command

The summary interface is vendor-agnostic. Sermon Archive Wiki runs a command
you provide, sends JSON to stdin, and reads stdout. The command should analyze
the whole transcript rather than returning a memorable excerpt from the opening
or conclusion.

The command receives:

```json
{
  "task": "sermon_archive_wiki_summary",
  "instructions": ["..."],
  "sermon": {
    "title": "Ordinary Courage",
    "date": "2026-07-05",
    "speaker": "Jane Pastor",
    "series": "Ordinary Faith",
    "scripture_refs": ["Joshua 1:1-9"],
    "transcript": "..."
  }
}
```

Preferred stdout is JSON:

```json
{
  "summary": "Short whole-sermon review summary.",
  "themes": ["Courage", "Faithfulness"],
  "topics": ["Discipleship"],
  "related_sermons": ["Do Not Fear"],
  "questionable_claims": ["Theme was inferred from application section."]
}
```

Plain text stdout is accepted as the summary.

If the command intentionally declines to summarize a sermon, it can return:

```json
{"skipped": true}
```

Skipped summaries are not labeled as AI-generated. If `--content-pass` is also
enabled, the deterministic local content pass may still create a review
summary.

Run it with:

```bash
sermon-archive-wiki ingest \
  --summary-pass \
  --external-summary-command "python scripts/example_summary_command.py"
```

For large archives, external summary commands can run concurrently:

```bash
SERMON_ARCHIVE_WIKI_SUMMARY_WORKERS=4 sermon-archive-wiki ingest --summary-pass
```

Any generated summary is labeled review-required in the vault.
