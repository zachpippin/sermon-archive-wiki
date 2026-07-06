# church-sermon-archivist Integration

Sermon Archive Wiki directly imports folders created by
`church-sermon-archivist`.

Expected folder shape:

```text
archive/2026/2026-07-05-the-gospel-and-ordinary-courage/
  audio.mp3
  transcript.raw.txt
  transcript.clean.md
  cleanup-notes.md
  metadata.json
```

Run:

```bash
sermon-archive-wiki ingest \
  --archivist-archive ../church-sermon-archivist/archive \
  --vault sermon-wiki-vault
```

Imported fields:

- `metadata.json` title, upload date, YouTube URL, YouTube ID, duration, and
  decision.
- `transcript.clean.md` when present.
- `transcript.raw.txt` when no clean transcript exists.
- `audio.mp3` as a source file.

The importer still marks the page draft and adds a review flag so the pastor
can confirm metadata and transcript quality.
