#!/usr/bin/env bash
# Raqeeb - The Muslim Shield: one-time setup for macOS and Linux.
# Mirrors "setup.bat" on Windows: installs the scanner and downloads
# the spyware fingerprint lists.
set -euo pipefail
cd "$(dirname "$0")"

echo
echo "  RAQEEB - THE MUSLIM SHIELD"
echo "  One-time setup: installs the scanner and downloads spyware fingerprints."
echo

PY=""
for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
    echo
    echo "  Python was not found. Install Python 3 from https://python.org,"
    echo "  then run this script again."
    exit 1
fi

echo "  [1/2] Installing MVT (the spyware scanner)..."
"$PY" -m pip install --upgrade pip
"$PY" -m pip install -r requirements.txt

echo "  [2/2] Downloading spyware fingerprint lists..."
mvt-android download-iocs

echo
echo "  Setup complete. Run ./run.sh to begin."
echo
