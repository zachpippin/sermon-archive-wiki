from __future__ import annotations

from collections import Counter
from pathlib import Path

from .models import SermonRecord
from .normalization import NamingPassResult
from .quality import completeness_counts, completeness_issues, has_audio, has_summary, has_transcript
from .util import markdown_table_row, write_text


def write_ingest_report(path: Path, records: list[SermonRecord], vault_dir: Path) -> None:
    counts = completeness_counts(records)
    lines = [
        "# Sermon Archive Wiki Ingest Report",
        "",
        f"- Vault: `{vault_dir}`",
        f"- Sermons discovered: {len(records)}",
        f"- Draft pages generated: {len(records)}",
        f"- Transcripts provided: {counts['with_transcript']}",
        f"- Missing transcripts: {counts['missing_transcript']}",
        f"- Generated summaries: {counts['with_summary']}",
        f"- Missing summaries: {counts['missing_summary']}",
        f"- Audio pages missing transcripts: {counts['audio_missing_transcript']}",
        f"- Audio pages missing summaries: {counts['audio_missing_summary']}",
        "",
        "## Review Notes",
        "",
        "Every sermon page starts as `status: draft` and `review_status: draft`.",
        "Questionable inferred claims are repeated in frontmatter, inline warning callouts, and `Review/Review Inbox.md`.",
        "",
        "## Sermons",
        "",
        "| Date | Title | Transcript | Flags |",
        "|---|---|---|---|",
    ]
    for record in records:
        flags = "; ".join([*record.review_flags, *record.questionable_claims])
        lines.append(markdown_table_row([record.date or "?", record.title, record.transcript_status, flags]))
    write_text(path, "\n".join(lines) + "\n")


def write_completeness_report(path: Path, records: list[SermonRecord]) -> None:
    counts = completeness_counts(records)
    problem_records = [(record, completeness_issues(record)) for record in records]
    problem_records = [(record, issues) for record, issues in problem_records if issues]
    lines = [
        "# Content Completeness QA",
        "",
        "This report checks whether generated sermon pages have the core review content pastors expect.",
        "",
        f"- Sermons discovered: {counts['sermons']}",
        f"- Pages with audio: {counts['with_audio']}",
        f"- Pages with transcript text: {counts['with_transcript']}",
        f"- Pages missing transcript text: {counts['missing_transcript']}",
        f"- Pages with generated summaries: {counts['with_summary']}",
        f"- Pages missing generated summaries: {counts['missing_summary']}",
        f"- Audio pages missing transcript text: {counts['audio_missing_transcript']}",
        f"- Audio pages missing generated summaries: {counts['audio_missing_summary']}",
        f"- Catalog-listed transcript gaps: {counts['catalog_listed_missing_transcript']}",
        "",
        "## Pages To Fix",
        "",
        "| Date | Title | Audio | Transcript | Summary | Transcript status | Issues |",
        "|---|---|---|---|---|---|---|",
    ]
    if problem_records:
        for record, issues in problem_records:
            lines.append(
                markdown_table_row(
                    [
                        record.date or "?",
                        record.title,
                        "yes" if has_audio(record) else "no",
                        "yes" if has_transcript(record) else "no",
                        "yes" if has_summary(record) else "no",
                        record.transcript_status,
                        "; ".join(issues),
                    ]
                )
            )
    else:
        lines.append(markdown_table_row(["-", "No completeness issues found.", "-", "-", "-", "-", "-"]))
    write_text(path, "\n".join(lines) + "\n")


def write_naming_report(path: Path, result: NamingPassResult) -> None:
    lines = [
        "# Naming QA Report",
        "",
        "This report lists deterministic name cleanups and remaining suspicious values.",
        "",
        f"- Changes applied: {len(result.changes)}",
        f"- Warnings to review: {len(result.warnings)}",
        "",
        "## Problem Values Summary",
        "",
        "| Scope | Value | Count | Reason |",
        "|---|---|---:|---|",
    ]
    summary_items = [
        *result.warnings,
        *[change for change in result.changes if change["reason"] == "configured alias"],
    ]
    summary = Counter((item["scope"], item["value"], item["reason"]) for item in summary_items)
    if summary:
        for (scope, value, reason), count in summary.most_common(40):
            lines.append(markdown_table_row([scope, value, count, reason]))
    else:
        lines.append(markdown_table_row(["-", "-", 0, "No naming issues found."]))

    lines.extend(
        [
            "",
            "## Applied Changes",
            "",
            "| Scope | Original | Replacement | Reason | Date | Sermon |",
            "|---|---|---|---|---:|---|",
        ]
    )
    if result.changes:
        for change in result.changes:
            lines.append(
                markdown_table_row(
                    [
                        change["scope"],
                        change["value"],
                        change["replacement"] or "(cleared)",
                        change["reason"],
                        change["date"] or "?",
                        change["sermon"],
                    ]
                )
            )
    else:
        lines.append(markdown_table_row(["-", "-", "-", "No configured aliases or deterministic cleanups were applied.", "-", "-"]))

    lines.extend(
        [
            "",
            "## Warnings",
            "",
            "| Scope | Value | Possible Match | Reason | Date | Sermon |",
            "|---|---|---|---|---:|---|",
        ]
    )
    if result.warnings:
        for warning in result.warnings:
            lines.append(
                markdown_table_row(
                    [
                        warning["scope"],
                        warning["value"],
                        warning["replacement"],
                        warning["reason"],
                        warning["date"] or "?",
                        warning["sermon"],
                    ]
                )
            )
    else:
        lines.append(markdown_table_row(["-", "-", "-", "No suspicious naming values found.", "-", "-"]))
    write_text(path, "\n".join(lines) + "\n")
