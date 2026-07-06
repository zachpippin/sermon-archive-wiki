from __future__ import annotations

from collections import Counter
from pathlib import Path

from .models import SermonRecord
from .normalization import NamingPassResult
from .util import markdown_table_row, write_text


def write_ingest_report(path: Path, records: list[SermonRecord], vault_dir: Path) -> None:
    lines = [
        "# Sermon Archive Wiki Ingest Report",
        "",
        f"- Vault: `{vault_dir}`",
        f"- Sermons discovered: {len(records)}",
        f"- Draft pages generated: {len(records)}",
        f"- Transcripts provided: {sum(1 for record in records if record.transcript_text.strip())}",
        f"- Missing transcripts: {sum(1 for record in records if not record.transcript_text.strip())}",
        f"- Generated summaries: {sum(1 for record in records if record.generated_summary)}",
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
