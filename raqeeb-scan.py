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
import shutil
import subprocess
import sys
import zipfile


def find_mvt(name="mvt-android"):
    """Locate an MVT command. Prefer a copy bundled next to this script,
    otherwise use the one 'pip install mvt' put on the system PATH."""
    here = os.path.dirname(os.path.abspath(__file__))
    bundled = os.path.join(here, "mvt", ".venv", "Scripts", name + ".exe")
    if os.path.exists(bundled):
        return bundled
    found = shutil.which(name)
    if found:
        return found
    return name  # last resort; will error clearly if truly missing


MVT = find_mvt("mvt-android")

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
    ("Serial Number",
     "The phone's serial number appeared in the data. This is normal - it just helps identify the scan."),
    ("android.permission",
     "An app holds a permission that can read data or track activity. Check that the app is one you installed and trust."),
    ("accessibility",
     "An app can read what's on your screen. Only legitimate apps (screen readers, some banking apps) usually need this - worth a second look if you don't recognise it."),
    ("Keylogging",
     "An app may be able to record what you type. Legitimate keyboards do this too - confirm it's your keyboard or a trusted app."),
    ("screen recording",
     "An app may be able to record the screen. Suspicious if you don't recognise the app."),
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


def write_html_report(results_dir, detections, warnings):
    """Write a clean browser report a non-technical person can read at a glance."""
    import html as _html

    clean = not detections
    if clean:
        verdict, sub, klass = ("No spyware found",
                               "We compared this phone against fingerprints of known spyware "
                               "(Pegasus, Predator and others). Nothing matched.", "clean")
    else:
        verdict, sub, klass = (f"Spyware detected ({len(detections)})",
                               "This phone matches a known spyware fingerprint. Read the guidance below.",
                               "danger")

    det_html = ""
    for d in detections:
        det_html += f'<li>{_html.escape(d.get("message", "?"))}</li>'

    groups = {}
    for w in warnings:
        groups.setdefault(friendly_reason(w.get("message", "")), []).append(w.get("message", "?"))
    warn_html = ""
    for reason, msgs in groups.items():
        items = "".join(f'<li>{_html.escape(m)}</li>' for m in msgs)
        warn_html += (f'<details><summary><span class="count">{len(msgs)}</span> {_html.escape(reason)}'
                      f'</summary><ul class="tech">{items}</ul></details>')

    danger_block = ""
    if not clean:
        danger_block = """
      <div class="advice">
        <h3>What to do now</h3>
        <ol>
          <li><b>Do not factory-reset the phone</b> - that would destroy the evidence.</li>
          <li>Keep the phone in airplane mode if you can.</li>
          <li>Contact a security professional or Amnesty International's Security Lab:
              <a href="https://securitylab.amnesty.org/get-help/">securitylab.amnesty.org/get-help</a></li>
        </ol>
      </div>"""

    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Raqeeb Scan Result</title>
<style>
  :root {{ --bg:#0f1216; --card:#171c22; --ink:#e8ecf1; --dim:#9aa6b2;
          --clean:#2ecc71; --danger:#ff5252; --warn:#ffb547; --line:#242c34; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
         font:16px/1.6 system-ui,Segoe UI,Roboto,sans-serif; padding:24px; }}
  .wrap {{ max-width:640px; margin:0 auto; }}
  .brand {{ text-align:center; letter-spacing:.35em; color:var(--dim);
           font-size:13px; margin-bottom:18px; }}
  .verdict {{ border-radius:16px; padding:32px 24px; text-align:center;
             background:var(--card); border:1px solid var(--line); }}
  .verdict.clean {{ border-color:var(--clean); }}
  .verdict.danger {{ border-color:var(--danger); }}
  .icon {{ font-size:56px; line-height:1; }}
  .verdict h1 {{ margin:12px 0 6px; font-size:28px; }}
  .verdict.clean h1 {{ color:var(--clean); }}
  .verdict.danger h1 {{ color:var(--danger); }}
  .verdict p {{ color:var(--dim); margin:0 auto; max-width:44ch; }}
  .advice {{ background:#241416; border:1px solid var(--danger); border-radius:12px;
            padding:16px 20px; margin-top:18px; }}
  .advice h3 {{ margin:0 0 8px; color:var(--danger); }}
  .advice a {{ color:var(--warn); }}
  .matches {{ background:#241416; border:1px solid var(--danger); border-radius:12px;
             padding:8px 20px; margin-top:18px; }}
  .section-title {{ margin:26px 4px 10px; color:var(--dim); font-size:13px;
                   text-transform:uppercase; letter-spacing:.12em; }}
  details {{ background:var(--card); border:1px solid var(--line); border-radius:10px;
            padding:10px 16px; margin-bottom:8px; }}
  summary {{ cursor:pointer; }}
  .count {{ display:inline-block; min-width:26px; text-align:center; background:var(--warn);
           color:#111; border-radius:20px; font-weight:700; padding:1px 8px; margin-right:8px; }}
  ul.tech {{ color:var(--dim); font-size:14px; font-family:ui-monospace,Consolas,monospace;
            word-break:break-all; }}
  .foot {{ color:var(--dim); font-size:13px; text-align:center; margin-top:28px; }}
</style></head><body><div class="wrap">
  <div class="brand">R A Q E E B &nbsp;·&nbsp; THE MUSLIM SHIELD</div>
  <div class="verdict {klass}">
    <div class="icon">{"✓" if clean else "⚠"}</div>
    <h1>{_html.escape(verdict)}</h1>
    <p>{_html.escape(sub)}</p>
  </div>
  {f'<div class="matches"><h3 style="color:var(--danger)">Matched spyware</h3><ul>{det_html}</ul></div>' if det_html else ''}
  {danger_block}
  {f'<div class="section-title">Things worth a quick look (not spyware)</div>{warn_html}' if warn_html else ''}
  <p class="foot">A clean result means no <b>known</b> spyware was found - it is not absolute proof
     the phone is clean. Technical details are saved in the results folder.</p>
</div></body></html>"""

    out = os.path.join(os.path.abspath(results_dir), "raqeeb-report.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    return out


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

    # Write and open an easy-to-read browser report.
    try:
        report = write_html_report(results_dir, detections, warnings)
        print(GREEN + "\n  Opening an easy-to-read report in your browser..." + RESET)
        import webbrowser
        webbrowser.open("file:///" + report.replace("\\", "/"))
        print(DIM + "  Report saved: " + report + RESET)
    except Exception as e:
        print(YELLOW + f"  (Could not open the browser report: {e})" + RESET)

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
    if not shutil.which(MVT) and not os.path.exists(MVT):
        print(RED + "  MVT was not found. Install it once with:" + RESET)
        print(YELLOW + "      pip install -r requirements.txt" + RESET)
        print(DIM + "  (or simply:  pip install mvt)" + RESET)
        sys.exit(1)
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
