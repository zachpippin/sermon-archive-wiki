# Pastor Review Workflow

V1 is private local review only.

## Statuses

Generated pages start with:

```yaml
status: draft
review_status: draft
```

The documented path is:

```text
draft -> reviewed -> canonical
```

V1 does not promote pages automatically. A pastor or trusted reviewer can edit
frontmatter locally later if the church wants to use `reviewed` or `canonical`.

## Review Surfaces

Questionable claims appear in three places:

- `questionable_claims` and `review_flags` frontmatter fields.
- An inline `> [!warning] Review needed` callout on the sermon page.
- `Review/Review Inbox.md`.

Content gaps are summarized in `reports/completeness-report.md`. Check this
after each ingest for pages with audio but no transcript text, pages without
generated summaries, and catalog rows that claimed a transcript was available
but did not have local transcript text.

Generated summaries appear under `## Generated Summary`. AI summaries from an
external command are tagged with:

```yaml
summary_status: ai_generated_review_required
summary_source: external_command
```

The local deterministic content index uses:

```yaml
summary_status: deterministic_review_required
summary_source: deterministic_content_index
```

## What Pastors Should Review First

- Speaker and series attribution.
- Scripture references inferred from a title or transcript.
- Caption-derived transcript errors.
- Missing transcripts for audio-only records.
- Pages listed in `reports/completeness-report.md`.
- Any AI-generated summary, theme, topic, or related-sermon suggestion.
