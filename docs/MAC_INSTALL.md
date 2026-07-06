# Mac Install Guide

This guide is for a church volunteer using a Mac.

## 1. Install Command Line Tools

Open Terminal and run:

```bash
xcode-select --install
```

If macOS says the tools are already installed, that is fine.

## 2. Install Homebrew

Follow the instructions at <https://brew.sh>, then run:

```bash
brew install python@3.11 yt-dlp
```

`yt-dlp` is only needed when you want the tool to fetch YouTube metadata from
URLs. Exported JSON files work without fetching.

## 3. Install This Tool

The easiest path is:

```bash
./Install.command
```

Manual path:

```bash
git clone https://github.com/zachpippin/sermon-archive-wiki.git
cd sermon-archive-wiki
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 4. Configure The Church

```bash
sermon-archive-wiki init
sermon-archive-wiki ingest --dry-run
sermon-archive-wiki ingest
```

Open the local website in Chrome:

```bash
open sermon-wiki-site/index.html
```

Open the generated vault folder in Obsidian and start with:

- `Home.md`
- `Review/Review Inbox.md`
- `review-report.md`
- `reports/completeness-report.md`
