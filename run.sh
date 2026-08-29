#!/usr/bin/env bash
# Raqeeb - The Muslim Shield: one-click launcher for macOS and Linux.
# Mirrors "Scan my phone.bat" on Windows.
set -euo pipefail
cd "$(dirname "$0")"
exec python3 raqeeb.py
