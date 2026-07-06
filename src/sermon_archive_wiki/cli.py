from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

import typer
from rich.console import Console
from rich.table import Table

from .config import CONFIG_FILE, DEFAULT_CONFIG, ensure_output_dirs, load_config, save_config
from .content_index import apply_content_index
from .html_site import write_html_site
from .inference import add_deterministic_inferences
from .importers import collect_records
from .normalization import apply_name_normalization
from .reports import write_completeness_report, write_ingest_report, write_naming_report
from .summaries import apply_external_summary
from .util import resolve_executable, split_list
from .vault import write_vault
from .youtube import fetch_youtube_records


app = typer.Typer(help="Build a local Obsidian-compatible sermon archive wiki.")
console = Console()


def _status(ok: bool) -> str:
    return "[green]OK[/green]" if ok else "[yellow]Needs attention[/yellow]"


@app.command()
def doctor(
    config_path: Path = typer.Option(Path(CONFIG_FILE), "--config"),
    strict: bool = typer.Option(False, "--strict", help="Exit non-zero if useful local tools are missing."),
) -> None:
    """Check local setup without publishing or uploading anything."""
    config = load_config(config_path)
    yt_dlp = str(config["youtube"].get("yt_dlp_command") or "yt-dlp")
    checks = [
        ("Python 3.10+", sys.version_info >= (3, 10), sys.version.split()[0]),
        ("Config file", config_path.exists(), str(config_path)),
        ("Vault path", bool(config["paths"].get("vault_dir")), config["paths"].get("vault_dir") or "missing"),
        ("HTML site path", bool(config["paths"].get("site_dir")), config["paths"].get("site_dir") or "missing"),
        ("yt-dlp", resolve_executable(yt_dlp) is not None, resolve_executable(yt_dlp) or "optional/missing"),
    ]
    table = Table("Check", "Status", "Detail")
    for name, ok, detail in checks:
        table.add_row(name, _status(ok), str(detail))
    console.print(table)
    if strict and not all(ok for _name, ok, _detail in checks[:3]):
        raise typer.Exit(1)


@app.command("init")
def init_project(
    config_path: Path = typer.Option(Path(CONFIG_FILE), "--config", help="Where to write the config file."),
    non_interactive: bool = typer.Option(False, "--non-interactive", help="Write example config without prompts."),
) -> None:
    """Create an initial config for a church's local sermon wiki."""
    config = deepcopy(DEFAULT_CONFIG)
    if non_interactive:
        save_config(config, config_path)
        console.print(f"Wrote example config to [bold]{config_path}[/bold].")
        return

    config["church"]["name"] = typer.prompt("Church name", default="")
    config["church"]["timezone"] = typer.prompt("Timezone", default=config["church"]["timezone"])
    config["paths"]["vault_dir"] = typer.prompt("Output vault folder", default=config["paths"]["vault_dir"])
    config["paths"]["site_dir"] = typer.prompt("Output local HTML website folder", default=config["paths"]["site_dir"])
    config["paths"]["transcript_dirs"] = split_list(typer.prompt("Transcript folders, comma-separated", default=""))
    config["paths"]["html_transcript_dirs"] = split_list(typer.prompt("Saved sermon-page HTML transcript folders, comma-separated", default=""))
    config["paths"]["caption_dirs"] = split_list(typer.prompt("Caption folders (.srt/.vtt), comma-separated", default=""))
    config["paths"]["audio_dirs"] = split_list(typer.prompt("Audio folders, comma-separated", default=""))
    config["paths"]["catalog_paths"] = split_list(typer.prompt("CSV/YAML catalog paths, comma-separated", default=""))
    config["paths"]["youtube_metadata_paths"] = split_list(typer.prompt("YouTube metadata JSON paths, comma-separated", default=""))
    config["paths"]["youtube_urls_file"] = typer.prompt("YouTube URL list file", default="")
    config["paths"]["archivist_archive_dir"] = typer.prompt(
        "church-sermon-archivist archive folder",
        default=config["paths"]["archivist_archive_dir"],
    )
    summary = typer.confirm(
        "Should initial ingests and updates ask whether to run an optional AI summary pass for cross-reference purposes?",
        default=True,
    )
    config["summary"]["ask_during_ingest"] = summary
    if typer.confirm("Do you already have an external summary command to configure?", default=False):
        config["summary"]["external_command"] = typer.prompt("External summary command")
        config["summary"]["enabled"] = True
    save_config(config, config_path)
    ensure_output_dirs(config)
    console.print(f"Wrote [bold]{config_path}[/bold].")
    console.print("Next: [bold]sermon-archive-wiki ingest[/bold]")


@app.command()
def ingest(
    config_path: Path = typer.Option(Path(CONFIG_FILE), "--config"),
    church_name: str = typer.Option("", "--church-name", help="Override the church name for generated outputs."),
    vault_dir: Path | None = typer.Option(None, "--vault"),
    site_dir: Path | None = typer.Option(None, "--site"),
    html_site: bool = typer.Option(True, "--html-site/--no-html-site", help="Write a local Chrome-openable HTML site."),
    catalog: list[Path] = typer.Option(None, "--catalog", help="CSV/YAML catalog path."),
    transcripts: list[Path] = typer.Option(None, "--transcripts", help="Transcript directory."),
    html_transcripts: list[Path] = typer.Option(None, "--html-transcripts", help="Saved sermon-page HTML transcript directory."),
    captions: list[Path] = typer.Option(None, "--captions", help="SRT/VTT caption directory."),
    audio: list[Path] = typer.Option(None, "--audio", help="Audio directory."),
    youtube_metadata: list[Path] = typer.Option(None, "--youtube-metadata", help="yt-dlp/exported JSON metadata."),
    youtube_url: list[str] = typer.Option(None, "--youtube-url", help="YouTube video/playlist/channel URL."),
    youtube_urls_file: Path | None = typer.Option(None, "--youtube-urls-file", help="Text file with one YouTube URL per line."),
    archivist_archive: Path | None = typer.Option(None, "--archivist-archive", help="church-sermon-archivist archive dir."),
    summary_pass: bool | None = typer.Option(None, "--summary-pass/--no-summary-pass", help="Run optional external summary pass."),
    content_pass: bool | None = typer.Option(None, "--content-pass/--no-content-pass", help="Run local deterministic summary and cross-index pass."),
    external_summary_command: str = typer.Option("", "--external-summary-command", help="Vendor-agnostic command that reads JSON on stdin."),
    fetch_youtube: bool = typer.Option(True, "--fetch-youtube/--no-fetch-youtube", help="Use yt-dlp for URLs, if provided."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Discover records without writing the vault."),
) -> None:
    """Generate or update the local Markdown sermon vault."""
    _run_ingest(
        config_path=config_path,
        church_name=church_name,
        vault_dir=vault_dir,
        site_dir=site_dir,
        html_site=html_site,
        catalog=catalog or [],
        transcripts=transcripts or [],
        html_transcripts=html_transcripts or [],
        captions=captions or [],
        audio=audio or [],
        youtube_metadata=youtube_metadata or [],
        youtube_url=youtube_url or [],
        youtube_urls_file=youtube_urls_file,
        archivist_archive=archivist_archive,
        summary_pass=summary_pass,
        content_pass=content_pass,
        external_summary_command=external_summary_command,
        fetch_youtube=fetch_youtube,
        dry_run=dry_run,
    )


@app.command()
def update(
    config_path: Path = typer.Option(Path(CONFIG_FILE), "--config"),
    summary_pass: bool | None = typer.Option(None, "--summary-pass/--no-summary-pass"),
    content_pass: bool | None = typer.Option(None, "--content-pass/--no-content-pass"),
) -> None:
    """Run a normal configured ingest/update."""
    _run_ingest(config_path=config_path, summary_pass=summary_pass, content_pass=content_pass)


def _run_ingest(
    config_path: Path = Path(CONFIG_FILE),
    church_name: str = "",
    vault_dir: Path | None = None,
    site_dir: Path | None = None,
    html_site: bool | None = None,
    catalog: list[Path] | None = None,
    transcripts: list[Path] | None = None,
    html_transcripts: list[Path] | None = None,
    captions: list[Path] | None = None,
    audio: list[Path] | None = None,
    youtube_metadata: list[Path] | None = None,
    youtube_url: list[str] | None = None,
    youtube_urls_file: Path | None = None,
    archivist_archive: Path | None = None,
    summary_pass: bool | None = None,
    content_pass: bool | None = None,
    external_summary_command: str = "",
    fetch_youtube: bool = True,
    dry_run: bool = False,
) -> None:
    config = load_config(config_path)
    if church_name.strip():
        config["church"]["name"] = church_name.strip()
    if vault_dir is not None:
        config["paths"]["vault_dir"] = str(vault_dir)
    if site_dir is not None:
        config["paths"]["site_dir"] = str(site_dir)

    records = collect_records(
        transcript_dirs=[Path(p) for p in [*config["paths"]["transcript_dirs"], *(transcripts or [])] if str(p)],
        html_transcript_dirs=[Path(p) for p in [*config["paths"].get("html_transcript_dirs", []), *(html_transcripts or [])] if str(p)],
        caption_dirs=[Path(p) for p in [*config["paths"]["caption_dirs"], *(captions or [])] if str(p)],
        audio_dirs=[Path(p) for p in [*config["paths"]["audio_dirs"], *(audio or [])] if str(p)],
        catalog_paths=[Path(p) for p in [*config["paths"]["catalog_paths"], *(catalog or [])] if str(p)],
        youtube_metadata_paths=[Path(p) for p in [*config["paths"]["youtube_metadata_paths"], *(youtube_metadata or [])] if str(p)],
        archivist_archive_dir=archivist_archive or _optional_path(config["paths"].get("archivist_archive_dir")),
    )

    urls = [*(youtube_url or [])]
    url_file = youtube_urls_file or _optional_path(config["paths"].get("youtube_urls_file"))
    if url_file and url_file.exists():
        urls.extend(line.strip() for line in url_file.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#"))
    if urls and fetch_youtube:
        records.extend(fetch_youtube_records(urls, str(config["youtube"].get("yt_dlp_command") or "yt-dlp")))
        records = collect_records_from_existing(records)

    naming_result = apply_name_normalization(records, config)
    records = [add_deterministic_inferences(record) for record in naming_result.records]

    do_summary = should_run_summary(config, summary_pass)
    command = external_summary_command or str(config["summary"].get("external_command") or "")
    if do_summary:
        if not command:
            console.print("[yellow]Summary pass requested, but no external command is configured. Skipping summaries.[/yellow]")
        else:
            records = apply_external_summary(records, command, int(config["summary"].get("timeout_seconds") or 180))
    if should_run_content_index(config, content_pass):
        content_config = config.get("content_index", {})
        records = apply_content_index(
            records,
            max_related_sermons=int(content_config.get("max_related_sermons") or 5),
            summary_sentences=int(content_config.get("summary_sentences") or 3),
        )

    table = Table("Date", "Title", "Transcript", "Flags")
    for record in records[:25]:
        table.add_row(record.date or "?", record.title, record.transcript_status, str(len(record.review_flags) + len(record.questionable_claims)))
    console.print(table)
    console.print(f"Discovered {len(records)} sermon records.")
    if dry_run:
        return

    target_vault = Path(config["paths"]["vault_dir"])
    reports_dir = Path(config["paths"]["reports_dir"])
    ensure_output_dirs(config)
    result = write_vault(records, target_vault, config)
    write_ingest_report(reports_dir / "review-report.md", records, target_vault)
    write_completeness_report(reports_dir / "completeness-report.md", records)
    write_naming_report(reports_dir / "naming-report.md", naming_result)
    console.print(f"Wrote vault to [bold]{result['vault_dir']}[/bold].")
    should_write_site = bool(config.get("output", {}).get("include_html_site", True)) if html_site is None else html_site
    if should_write_site:
        site_result = write_html_site(records, Path(config["paths"]["site_dir"]), config)
        site_index = Path(site_result["index_path"])
        console.print(f"Wrote local website to [bold]{site_result['site_dir']}[/bold].")
        console.print(f"Open in Chrome: [bold]{site_index.as_uri()}[/bold]")
    console.print(f"Wrote report to [bold]{reports_dir / 'review-report.md'}[/bold].")
    console.print(f"Wrote completeness QA report to [bold]{reports_dir / 'completeness-report.md'}[/bold].")
    console.print(f"Wrote naming QA report to [bold]{reports_dir / 'naming-report.md'}[/bold].")


def should_run_summary(config: dict, summary_pass: bool | None) -> bool:
    if summary_pass is not None:
        return summary_pass
    if bool(config["summary"].get("ask_during_ingest", True)) and sys.stdin.isatty():
        return typer.confirm("Run optional external AI summary pass for cross-reference purposes?", default=bool(config["summary"].get("enabled")))
    return bool(config["summary"].get("enabled"))


def should_run_content_index(config: dict, content_pass: bool | None) -> bool:
    if content_pass is not None:
        return content_pass
    return bool(config.get("content_index", {}).get("enabled"))


def _optional_path(value: object) -> Path | None:
    text = str(value or "").strip()
    return Path(text) if text else None


def collect_records_from_existing(records):
    from .inference import add_deterministic_inferences
    from .importers import merge_records

    return [add_deterministic_inferences(record) for record in merge_records(records)]


if __name__ == "__main__":
    app()
