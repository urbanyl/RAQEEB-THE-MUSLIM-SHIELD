"""raqeeb-scan: run an MVT scan on a Raqeeb/androidqf archive and print a
plain-language verdict.

Usage:
    python raqeeb-scan.py <acquisition.zip> [-p BACKUP_PIN]
    python raqeeb-scan.py --summarize <results-folder>   (skip scan, just report)
"""

import argparse
import glob
import io
import json
import os
import subprocess
import sys
import zipfile

MVT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mvt", ".venv", "Scripts", "mvt-android.exe")

GREEN, YELLOW, RED, BOLD, DIM, RESET = "\033[92m", "\033[93m", "\033[91m", "\033[1m", "\033[2m", "\033[0m"

# Explanations for the heuristic warnings MVT raises, in beginner language.
FRIENDLY = [
    ("installed via adb or another method",
     "App not installed from the Play Store. Pre-installed Samsung/Google apps "
     "show up here too, so this is usually harmless - just check you recognize the app."),
    ("installed via a browser",
     "App was downloaded and installed outside the Play Store (sideloaded). "
     "Fine if you did it on purpose - suspicious if you don't remember it."),
    ("disabled sharing of crash logs",
     "A privacy setting is turned off. Normal if you chose it yourself."),
    ("disabled sharing of security reports",
     "A privacy setting is turned off. Normal if you chose it yourself."),
    ("root", "Possible sign the phone is rooted (security removed). Serious if you didn't root it yourself."),
]


def repack_if_needed(zip_path):
    """MVT expects androidqf files inside a subfolder; new androidqf writes them
    at the zip root. Repack transparently when needed."""
    z = zipfile.ZipFile(zip_path)
    names = z.namelist()
    if not any(n.split("/")[0] == n and n.endswith(".json") or n == "getprop.txt" for n in names):
        return zip_path
    fixed = os.path.splitext(zip_path)[0] + "-mvt.zip"
    if not os.path.exists(fixed):
        print(DIM + "Preparing archive for scanning..." + RESET)
        with zipfile.ZipFile(fixed, "w", zipfile.ZIP_DEFLATED) as out:
            for n in names:
                data = z.read(n)
                if n == "bugreport.zip":
                    try:
                        zipfile.ZipFile(io.BytesIO(data))
                    except Exception:
                        continue  # drop corrupt bugreport rather than crash MVT
                out.writestr("acquisition/" + n.rstrip("\r"), data)
    return fixed


def friendly_reason(message):
    for needle, explanation in FRIENDLY:
        if needle in message:
            return explanation
    return "Flagged for manual review."


def summarize(results_dir):
    detections, warnings = [], []
    for f in glob.glob(os.path.join(results_dir, "*_detected.json")):
        try:
            entries = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        for e in entries:
            (detections if e.get("matched_indicator") else warnings).append(e)

    print()
    print(BOLD + "=" * 62 + RESET)
    print(BOLD + "  RAQEEB SCAN RESULT" + RESET)
    print(BOLD + "=" * 62 + RESET)
    if detections:
        print(RED + BOLD + f"\n  SPYWARE DETECTED - {len(detections)} match(es) against known spyware\n" + RESET)
        for d in detections:
            print(RED + "  [!] " + d.get("message", "?") + RESET)
        print(RED + "\n  Do NOT factory-reset yet: the evidence would be destroyed." + RESET)
        print(RED + "  Contact a security professional or Amnesty's Security Lab:" + RESET)
        print(RED + "  https://securitylab.amnesty.org/get-help/" + RESET)
    else:
        print(GREEN + BOLD + "\n  CLEAN - no known spyware found on this device\n" + RESET)
        print("  The scan compared your phone's data against fingerprints of")
        print("  known spyware (Pegasus, Predator and others). Nothing matched.")

    if warnings:
        print(YELLOW + f"\n  {len(warnings)} thing(s) worth a quick look (not spyware matches):\n" + RESET)
        seen = {}
        for w in warnings:
            reason = friendly_reason(w.get("message", ""))
            seen.setdefault(reason, []).append(w.get("message", "?"))
        for reason, msgs in seen.items():
            print(YELLOW + f"  * {len(msgs)}x " + RESET + reason)
            for m in msgs[:4]:
                print(DIM + "      - " + m[:95] + RESET)
            if len(msgs) > 4:
                print(DIM + f"      ... and {len(msgs) - 4} more" + RESET)
    print()
    print(DIM + "  Remember: a clean result means no KNOWN spyware was found." + RESET)
    print(DIM + "  Full technical details: " + os.path.abspath(results_dir) + RESET)
    print(BOLD + "=" * 62 + RESET)
    return 2 if detections else 0


def main():
    os.system("")  # enable ANSI colors in Windows terminals
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="acquisition zip (or results folder with --summarize)")
    ap.add_argument("-p", "--pin", help="device PIN / backup password, to also scan SMS messages")
    ap.add_argument("--summarize", action="store_true", help="only summarize an existing results folder")
    args = ap.parse_args()

    if args.summarize:
        sys.exit(summarize(args.target))

    zip_path = repack_if_needed(args.target)
    results = os.path.splitext(args.target)[0] + "-results"
    cmd = [MVT, "check-androidqf", "--non-interactive", "-o", results, zip_path]
    if args.pin:
        cmd[2:2] = ["-p", args.pin]
    print(DIM + "Scanning... this can take several minutes." + RESET)
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    log_path = os.path.join(results, "raqeeb-scan.log")
    os.makedirs(results, exist_ok=True)
    open(log_path, "w", encoding="utf-8").write(proc.stdout + proc.stderr)
    if not args.pin and "Cannot decrypt backup" in proc.stdout + proc.stderr:
        print(YELLOW + "Note: your SMS messages were skipped (backup is locked with your device PIN)." + RESET)
        print(YELLOW + "Re-run with:  -p YOUR-PIN   to include them." + RESET)
    sys.exit(summarize(results))


if __name__ == "__main__":
    main()
