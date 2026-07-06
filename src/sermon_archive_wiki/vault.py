from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import textwrap
from typing import Any

import yaml

from .models import SermonRecord
from .scripture_index import ScriptureEntry, build_scripture_index, scripture_entry_totals, scripture_role
from .util import markdown_table_row, media_uri, now_stamp, page_stem, safe_filename, wikilink, write_text


def write_vault(records: list[SermonRecord], vault_dir: Path, config: dict[str, Any]) -> dict[str, Any]:
    vault_dir.mkdir(parents=True, exist_ok=True)
    for child in ("Sermons", "Series", "Speakers", "Scripture", "Themes", "Review"):
        (vault_dir / child).mkdir(parents=True, exist_ok=True)

    sermon_pages: dict[str, str] = {}
    for record in records:
        stem = page_stem(record.date, record.title)
        sermon_pages[record_key(record)] = stem
        write_text(vault_dir / "Sermons" / f"{stem}.md", sermon_page(record, config))

    write_home(vault_dir, records)
    write_series_pages(vault_dir, records)
    write_speaker_pages(vault_dir, records)
    write_scripture_pages(vault_dir, records)
    write_theme_pages(vault_dir, records)
    write_review_pages(vault_dir, records)
    return {
        "vault_dir": str(vault_dir),
        "sermon_count": len(records),
        "draft_count": sum(1 for record in records if record.review_status == "draft"),
    }


def sermon_page(record: SermonRecord, config: dict[str, Any]) -> str:
    frontmatter = {
        "title": record.title,
        "date": record.date,
        "speaker": record.speaker,
        "series": record.series,
        "scripture_refs": record.scripture_refs,
        "mentioned_scripture_refs": record.mentioned_scripture_refs,
        "scripture_ref_counts": record.scripture_ref_counts,
        "source_files": record.source_files,
        "audio_files": record.audio_files,
        "youtube_url": record.youtube_url,
        "transcript_status": record.transcript_status,
        "status": "draft",
        "review_status": "draft",
        "summary_status": record.summary_status,
        "generated_by": "sermon-archive-wiki",
        "generated_at": now_stamp(),
        "questionable_claims": record.questionable_claims,
        "review_flags": record.review_flags,
    }
    lines = ["---", yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=False, width=1000).strip(), "---", ""]
    lines.append(f"# {record.title}")
    lines.append("")
    if record.date or record.speaker or record.series:
        bits = []
        if record.date:
            bits.append(f"**{record.date}**")
        if record.speaker:
            bits.append(wikilink(safe_filename(record.speaker)))
        if record.series:
            bits.append(wikilink(safe_filename(record.series)))
        lines.append(" | ".join(bits))
        lines.append("")

    if record.review_flags or record.questionable_claims:
        lines.append("> [!warning] Review needed")
        for flag in [*record.review_flags, *record.questionable_claims]:
            lines.append(f"> - {flag}")
        lines.append("")

    lines.extend(metadata_section(record))
    lines.extend(audio_section(record))
    lines.extend(summary_section(record))
    lines.extend(cross_reference_section(record))
    lines.extend(source_section(record))
    lines.extend(transcript_section(record, config))
    return "\n".join(lines).rstrip() + "\n"


def metadata_section(record: SermonRecord) -> list[str]:
    lines = ["## Sermon Metadata", ""]
    lines.append(f"- **Review status:** draft")
    lines.append("- **Status path:** draft -> reviewed -> canonical")
    lines.append(f"- **Date:** {record.date or 'Review needed'}")
    lines.append(f"- **Speaker:** {wikilink(safe_filename(record.speaker)) if record.speaker else 'Review needed'}")
    lines.append(f"- **Series:** {wikilink(safe_filename(record.series)) if record.series else 'Review needed'}")
    if record.scripture_refs:
        refs = ", ".join(wikilink(safe_filename(ref)) for ref in record.scripture_refs)
        lines.append(f"- **Scripture:** {refs}")
    else:
        lines.append("- **Scripture:** Review needed")
    referenced_refs = [ref for ref in record.mentioned_scripture_refs if ref.casefold() not in {item.casefold() for item in record.scripture_refs}]
    if referenced_refs:
        refs = ", ".join(wikilink(safe_filename(ref)) for ref in referenced_refs[:20])
        if len(referenced_refs) > 20:
            refs += f", +{len(referenced_refs) - 20} more"
        lines.append(f"- **Referenced Scripture:** {refs}")
    lines.append(f"- **Transcript status:** {record.transcript_status}")
    if record.youtube_url:
        lines.append(f"- **YouTube:** [{record.youtube_url}]({record.youtube_url})")
    lines.append("")
    return lines


def summary_section(record: SermonRecord) -> list[str]:
    lines = ["## Generated Summary", ""]
    if record.generated_summary:
        lines.append(f"> [!note] {summary_notice(record)}")
        for paragraph in record.generated_summary.splitlines():
            if paragraph.strip():
                lines.append(f"> {paragraph.strip()}")
            else:
                lines.append(">")
        lines.append("")
        if record.themes:
            lines.append("**Generated/cross-reference themes to review:**")
            for theme in record.themes:
                lines.append(f"- {wikilink(safe_filename(theme))}")
            lines.append("")
    else:
        lines.append("_No generated summary was created for this sermon._")
        lines.append("")
    return lines


def audio_section(record: SermonRecord) -> list[str]:
    if not record.audio_files:
        return []
    lines = ["## Audio", ""]
    seen: set[str] = set()
    for index, audio in enumerate(record.audio_files, start=1):
        normalized = audio.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        label = "Listen" if index == 1 else f"Listen {index}"
        lines.append(f"- [{label}]({media_uri(normalized)})")
    lines.append("")
    return lines


def summary_notice(record: SermonRecord) -> str:
    if record.summary_source == "external_command" or "ai" in record.summary_status.casefold():
        return "AI-generated, review before relying on this"
    return "Generated locally for review; confirm before relying on this"


def cross_reference_section(record: SermonRecord) -> list[str]:
    lines = ["## Cross-References", ""]
    if record.series:
        lines.append(f"- **Series:** {wikilink(safe_filename(record.series))}")
    if record.speaker:
        lines.append(f"- **Speaker:** {wikilink(safe_filename(record.speaker))}")
    for ref in record.scripture_refs:
        lines.append(f"- **Scripture:** {wikilink(safe_filename(ref))}")
    primary_keys = {ref.casefold() for ref in record.scripture_refs}
    for ref in record.mentioned_scripture_refs[:40]:
        if ref.casefold() not in primary_keys:
            lines.append(f"- **Referenced Scripture:** {wikilink(safe_filename(ref))}")
    if len(record.mentioned_scripture_refs) > 40:
        lines.append(f"- **Referenced Scripture:** +{len(record.mentioned_scripture_refs) - 40} more detected references")
    for topic in record.topics:
        lines.append(f"- **Topic:** {wikilink(safe_filename(topic))}")
    for theme in record.themes:
        lines.append(f"- **Theme:** {wikilink(safe_filename(theme))}")
    for related in record.related_sermons:
        lines.append(f"- **Related sermon suggestion:** {wikilink(safe_filename(related))}")
    if len(lines) == 2:
        lines.append("- Review needed: no cross-references found yet.")
    lines.append("")
    return lines


def source_section(record: SermonRecord) -> list[str]:
    lines = ["## Sources", ""]
    if not record.source_files and not record.audio_files and not record.youtube_url:
        lines.append("- Review needed: no source files recorded.")
    for source in record.source_files:
        lines.append(f"- `{source}`")
    for audio in record.audio_files:
        if audio not in record.source_files:
            lines.append(f"- `{audio}`")
    if record.youtube_url:
        lines.append(f"- [{record.youtube_url}]({record.youtube_url})")
    lines.append("")
    return lines


def transcript_section(record: SermonRecord, config: dict[str, Any]) -> list[str]:
    lines = ["## Transcript", ""]
    if not record.transcript_text:
        lines.append("_No transcript text is available yet._")
        lines.append("")
        return lines

    excerpt_chars = int(config.get("output", {}).get("transcript_excerpt_chars") or 0)
    include_full = bool(config.get("output", {}).get("include_full_transcripts", True))
    text = record.transcript_text.strip()
    if excerpt_chars > 0:
        text = text[:excerpt_chars].rstrip() + ("..." if len(record.transcript_text) > excerpt_chars else "")
    elif not include_full:
        text = textwrap.shorten(text.replace("\n", " "), width=1200, placeholder="...")
    lines.append("> [!note] Source transcript")
    lines.append("> Generated page keeps transcript text local for private review.")
    lines.append("")
    lines.append(text)
    lines.append("")
    return lines


def write_home(vault_dir: Path, records: list[SermonRecord]) -> None:
    lines = [
        "# Sermon Archive Wiki",
        "",
        "Local private review vault generated by `sermon-archive-wiki`.",
        "",
        "## Indexes",
        "",
        "- [[Series Index]]",
        "- [[Speakers Index]]",
        "- [[Scripture Index]]",
        "- [[Themes Index]]",
        "- [[Review Inbox]]",
        "- [[Review Status]]",
        "",
        "## Sermons",
        "",
    ]
    for record in records:
        lines.append(f"- {sermon_link(record)}")
    write_text(vault_dir / "Home.md", "\n".join(lines) + "\n")


def write_series_pages(vault_dir: Path, records: list[SermonRecord]) -> None:
    grouped = group_records(records, lambda record: record.series)
    write_index(vault_dir / "Series" / "Series Index.md", "Series Index", grouped)
    for name, items in grouped.items():
        write_group_page(vault_dir / "Series" / f"{safe_filename(name)}.md", name, "Series", items)


def write_speaker_pages(vault_dir: Path, records: list[SermonRecord]) -> None:
    grouped = group_records(records, lambda record: record.speaker)
    write_index(vault_dir / "Speakers" / "Speakers Index.md", "Speakers Index", grouped)
    for name, items in grouped.items():
        write_group_page(vault_dir / "Speakers" / f"{safe_filename(name)}.md", name, "Speaker", items)


def write_scripture_pages(vault_dir: Path, records: list[SermonRecord]) -> None:
    grouped = build_scripture_index(records)
    write_scripture_index(vault_dir / "Scripture" / "Scripture Index.md", grouped)
    for name, entries in grouped.items():
        write_scripture_group_page(vault_dir / "Scripture" / f"{safe_filename(name)}.md", name, entries)


def write_theme_pages(vault_dir: Path, records: list[SermonRecord]) -> None:
    grouped: dict[str, list[SermonRecord]] = defaultdict(list)
    for record in records:
        for theme in [*record.topics, *record.themes]:
            grouped[theme].append(record)
    write_index(vault_dir / "Themes" / "Themes Index.md", "Themes Index", grouped)
    for name, items in grouped.items():
        write_group_page(vault_dir / "Themes" / f"{safe_filename(name)}.md", name, "Theme", items)


def write_review_pages(vault_dir: Path, records: list[SermonRecord]) -> None:
    actionable_records = [
        record
        for record in records
        if record.review_flags or record.questionable_claims or not record.transcript_text.strip() or record.generated_summary
    ]
    inbox = [
        "# Review Inbox",
        "",
        "Generated pages begin as `draft`. This inbox lists pages with specific flags, missing transcript text, or generated summaries.",
        "",
        f"- Actionable pages: {len(actionable_records)}",
        f"- Total draft pages: {len(records)}",
        "",
        "| Sermon | Date | Flags |",
        "|---|---:|---|",
    ]
    for record in actionable_records:
        flags = "; ".join([*record.review_flags, *record.questionable_claims])
        if not record.transcript_text.strip():
            flags = "; ".join([flags, "Missing transcript text"]).strip("; ")
        if record.generated_summary:
            flags = "; ".join([flags, "Review generated summary"]).strip("; ")
        inbox.append(markdown_table_row([sermon_link(record, labeled=False), record.date or "?", flags]))
    write_text(vault_dir / "Review" / "Review Inbox.md", "\n".join(inbox) + "\n")

    report = [
        "# Review Status",
        "",
        f"- Sermons generated: {len(records)}",
        f"- Draft pages: {sum(1 for record in records if record.review_status == 'draft')}",
        f"- Pages with generated summaries: {sum(1 for record in records if record.generated_summary)}",
        f"- Pages missing transcript text: {sum(1 for record in records if not record.transcript_text.strip())}",
        "",
        "## Status Path",
        "",
        "`draft -> reviewed -> canonical`",
        "",
        "V1 only creates draft pages and clearly tags generated summaries. Churches can promote pages locally after pastoral review.",
        "",
        "## Sermons",
        "",
        "| Sermon | Review status | Transcript | Summary |",
        "|---|---|---|---|",
    ]
    for record in records:
        report.append(markdown_table_row([sermon_link(record, labeled=False), record.review_status, record.transcript_status, record.summary_status]))
    write_text(vault_dir / "Review" / "Review Status.md", "\n".join(report) + "\n")
    write_text(vault_dir / "review-report.md", "\n".join(report).replace("# Review Status", "# Review Report", 1) + "\n")


def write_index(path: Path, title: str, grouped: dict[str, list[SermonRecord]]) -> None:
    lines = [f"# {title}", ""]
    if not grouped:
        lines.append("_No entries yet._")
    for name, records in sorted(grouped.items(), key=lambda item: item[0].casefold()):
        lines.append(f"- {wikilink(safe_filename(name))} ({len(records)})")
    write_text(path, "\n".join(lines) + "\n")


def write_scripture_index(path: Path, grouped: dict[str, list[ScriptureEntry]]) -> None:
    lines = [
        "# Scripture Index",
        "",
        "Private concordance of primary sermon texts and Scripture references detected in transcripts.",
        "",
        "| Scripture | Sermons | Mentions | Primary | First | Latest |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    if not grouped:
        lines.append("| _No entries yet._ | 0 | 0 | 0 |  |  |")
    for ref, entries in sorted(grouped.items(), key=lambda item: (-scripture_entry_totals(item[1])[1], item[0].casefold())):
        sermons, mentions, primary = scripture_entry_totals(entries)
        dates = sorted(entry.record.date for entry in entries if entry.record.date)
        first_date = dates[0] if dates else ""
        latest_date = dates[-1] if dates else ""
        lines.append(markdown_table_row([wikilink(safe_filename(ref)), sermons, mentions, primary, first_date, latest_date]))
    write_text(path, "\n".join(lines) + "\n")


def write_scripture_group_page(path: Path, ref: str, entries: list[ScriptureEntry]) -> None:
    sermons, mentions, primary = scripture_entry_totals(entries)
    lines = [
        f"# {ref}",
        "",
        "Scripture concordance page generated for private sermon review.",
        "",
        f"- Sermons: {sermons}",
        f"- Mentions: {mentions}",
        f"- Primary sermon texts: {primary}",
        "",
        "## Sermons",
        "",
        "| Sermon | Date | Speaker | Series | Role | Mentions |",
        "|---|---:|---|---|---|---:|",
    ]
    for entry in sorted(entries, key=lambda item: (item.record.date or "9999-99-99", item.record.title.casefold())):
        record = entry.record
        lines.append(
            markdown_table_row(
                [
                    sermon_link(record, labeled=False),
                    record.date or "?",
                    wikilink(safe_filename(record.speaker)) if record.speaker else "Review",
                    wikilink(safe_filename(record.series)) if record.series else "Review",
                    scripture_role(entry),
                    entry.mentions,
                ]
            )
        )
    write_text(path, "\n".join(lines) + "\n")


def write_group_page(path: Path, name: str, kind: str, records: list[SermonRecord]) -> None:
    lines = [f"# {name}", "", f"{kind} index generated for private sermon review.", "", "## Sermons", ""]
    for record in sorted(records, key=lambda item: (item.date or "9999-99-99", item.title.casefold())):
        lines.append(f"- {sermon_link(record)}")
    write_text(path, "\n".join(lines) + "\n")


def group_records(records: list[SermonRecord], key_func: Any) -> dict[str, list[SermonRecord]]:
    grouped: dict[str, list[SermonRecord]] = defaultdict(list)
    for record in records:
        key = key_func(record)
        if key:
            grouped[key].append(record)
    return grouped


def sermon_link(record: SermonRecord, labeled: bool = True) -> str:
    if labeled:
        return wikilink(page_stem(record.date, record.title), record.title)
    return wikilink(page_stem(record.date, record.title))


def record_key(record: SermonRecord) -> str:
    if record.youtube_id:
        return record.youtube_id
    if record.youtube_url:
        return record.youtube_url
    return f"{record.date}:{record.title}"
