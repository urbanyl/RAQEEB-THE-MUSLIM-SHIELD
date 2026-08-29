@echo off
title Raqeeb - The Muslim Shield - Setup
cd /d "%~dp0"

echo.
echo   RAQEEB - THE MUSLIM SHIELD
echo   One-time setup: installs the scanner and downloads spyware fingerprints.
echo.

REM Make sure Python is available.
where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo   Python was not found. Install it from python.org and tick
    echo   "Add Python to PATH", then run this again.
    pause
    exit /b 1
)

echo   [1/2] Installing MVT (the spyware scanner)...
python -m pip install --upgrade pip
python -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo.
    echo   Could not install MVT. Check your internet connection and try again.
    pause
    exit /b 1
)

echo   [2/2] Downloading spyware fingerprint lists...
mvt-android download-iocs
if errorlevel 1 (
    echo.
    echo   Could not download the fingerprint lists. The scan may not work yet.
    pause
    exit /b 1
)

echo.
echo   Setup complete. Double-click "Scan my phone.bat" to begin.
echo.
pause
