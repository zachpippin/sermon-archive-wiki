#!/usr/bin/env bash
set -euo pipefail

echo "Installing Homebrew packages..."
brew install python@3.11 yt-dlp

PYTHON_BIN="$(command -v python3.12 || command -v python3.11 || command -v python3.10 || true)"
if [[ -z "$PYTHON_BIN" ]]; then
  echo "Could not find Python 3.10+. Install a Homebrew Python first."
  exit 1
fi

echo "Creating Python environment..."
"$PYTHON_BIN" -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .

echo "Run: source .venv/bin/activate && sermon-archive-wiki doctor && sermon-archive-wiki init && sermon-archive-wiki ingest"
echo "Then open: sermon-wiki-site/index.html"
