# External Summary Command

The summary interface is vendor-agnostic. Sermon Archive Wiki runs a command
you provide, sends JSON to stdin, and reads stdout.

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
  "summary": "Short review summary.",
  "themes": ["Courage", "Faithfulness"],
  "topics": ["Discipleship"],
  "related_sermons": ["Do Not Fear"],
  "questionable_claims": ["Theme was inferred from application section."]
}
```

Plain text stdout is accepted as the summary.

Run it with:

```bash
sermon-archive-wiki ingest \
  --summary-pass \
  --external-summary-command "python scripts/example_summary_command.py"
```

Any generated summary is labeled review-required in the vault.
