from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


CONFIG_FILE = "sermon-archive-wiki.yml"

DEFAULT_CONFIG: dict[str, Any] = {
    "church": {
        "name": "",
        "timezone": "America/New_York",
    },
    "paths": {
        "vault_dir": "sermon-wiki-vault",
        "site_dir": "sermon-wiki-site",
        "reports_dir": "reports",
        "transcript_dirs": [],
        "html_transcript_dirs": [],
        "caption_dirs": [],
        "audio_dirs": [],
        "catalog_paths": [],
        "youtube_metadata_paths": [],
        "youtube_urls_file": "",
        "archivist_archive_dir": "../church-sermon-archivist/archive",
    },
    "youtube": {
        "fetch_metadata": True,
        "yt_dlp_command": "yt-dlp",
    },
    "summary": {
        "enabled": False,
        "ask_during_ingest": True,
        "external_command": "",
        "timeout_seconds": 180,
    },
    "content_index": {
        "enabled": False,
        "max_related_sermons": 5,
        "summary_sentences": 3,
    },
    "normalization": {
        "speaker_aliases": {},
        "series_aliases": {},
        "annual_series_patterns": [],
        "title_series_patterns": [],
        "infer_scripture_book_series_from_title": True,
        "scripture_aliases": {},
        "theme_aliases": {},
        "ignored_speakers": [],
    },
    "output": {
        "include_html_site": True,
        "obsidian_wikilinks": True,
        "include_full_transcripts": True,
        "transcript_excerpt_chars": 0,
    },
}


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_yaml(path: Path) -> Any:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {} if data is None else data


def save_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=False), encoding="utf-8")


def load_config(path: Path | str = CONFIG_FILE) -> dict[str, Any]:
    config_path = Path(path)
    data = load_yaml(config_path)
    if data and not isinstance(data, dict):
        raise ValueError(f"{config_path} must contain a YAML mapping.")
    return deep_merge(DEFAULT_CONFIG, data)


def save_config(config: dict[str, Any], path: Path | str = CONFIG_FILE) -> None:
    save_yaml(Path(path), config)


def ensure_output_dirs(config: dict[str, Any]) -> None:
    Path(config["paths"]["vault_dir"]).mkdir(parents=True, exist_ok=True)
    Path(config["paths"]["site_dir"]).mkdir(parents=True, exist_ok=True)
    Path(config["paths"]["reports_dir"]).mkdir(parents=True, exist_ok=True)
