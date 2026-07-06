#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "Sermon Archive Wiki installer"
echo "This installs local tools only. It does not publish or upload anything."
echo

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew was not found."
  echo "Install Homebrew from https://brew.sh, then run this installer again."
  exit 1
fi

brew install python@3.11 yt-dlp

PYTHON_BIN="$(command -v python3.12 || command -v python3.11 || command -v python3.10 || true)"
if [[ -z "$PYTHON_BIN" ]]; then
  echo "Could not find Python 3.10+ after Homebrew install."
  exit 1
fi

"$PYTHON_BIN" -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .

echo
echo "Install complete."
echo "Next commands:"
echo "  source .venv/bin/activate"
echo "  sermon-archive-wiki doctor"
echo "  sermon-archive-wiki init"
echo "  sermon-archive-wiki ingest"
echo "  open sermon-wiki-site/index.html"
echo
read -r -p "Press Return to close this window."
