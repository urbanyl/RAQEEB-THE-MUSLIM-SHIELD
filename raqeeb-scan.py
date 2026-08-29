"""raqeeb-scan: run an MVT scan on a Raqeeb/androidqf archive and print a
plain-language verdict.

Usage:
    python raqeeb-scan.py <acquisition.zip> [-p BACKUP_PIN]
    python raqeeb-scan.py --summarize <results-folder>   (skip scan, just report)
"""

import argparse
import datetime
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


def find_acquisition_json(zip_path):
    """Locate acquisition.json inside the archive, whether it is at the root
    or under an 'acquisition/' subfolder."""
    with zipfile.ZipFile(zip_path) as z:
        for name in z.namelist():
            if name.endswith("acquisition.json"):
                return name
    return None


def read_metadata(zip_path):
    """Read acquisition metadata so the report can show exactly which phone /
    archive was scanned. Combines acquisition.json (uuid, version, timestamps,
    module outcomes) with device properties from getprop.txt."""
    meta = {
        "id": "", "version": "", "device": "", "manufacturer": "",
        "os": "", "serial": "", "started": "", "finished": "",
        "module_results": [], "app_count": "", "fingerprint": "",
    }
    try:
        name = find_acquisition_json(zip_path)
        if name:
            with zipfile.ZipFile(zip_path) as z:
                raw = json.loads(z.read(name).decode("utf-8", "replace"))
            meta["id"] = raw.get("uuid", "")
            meta["version"] = raw.get("androidqf_version", "")
            meta["started"] = str(raw.get("started", "") or "")
            meta["finished"] = str(raw.get("completed", "") or "")
            if isinstance(raw.get("module_results"), list):
                meta["module_results"] = raw["module_results"]
    except Exception:
        pass

    # Device properties come from the raw `adb shell getprop` output.
    try:
        with zipfile.ZipFile(zip_path) as z:
            text = z.read("getprop.txt").decode("utf-8", "replace")
        keymap = {
            "[ro.product.model]": "device",
            "[ro.product.manufacturer]": "manufacturer",
            "[ro.build.version.release]": "os",
            "[ro.serialno]": "serial",
            "[ro.build.fingerprint]": "fingerprint",
        }
        for marker, field in keymap.items():
            for line in text.splitlines():
                if line.startswith(marker):
                    # getprop lines look like:  [ro.product.model]: [Pixel 7]
                    value = line[len(marker):].strip()
                    value = value.lstrip(":").strip()
                    if value.startswith("[") and value.endswith("]"):
                        value = value[1:-1]
                    if value:
                        meta[field] = value.strip()
                        break
    except Exception:
        pass

    # Rough sense of how many installed apps were recorded.
    try:
        with zipfile.ZipFile(zip_path) as z:
            pkgs = json.loads(z.read("packages.json").decode("utf-8", "replace"))
        if isinstance(pkgs, list):
            meta["app_count"] = str(len(pkgs))
    except Exception:
        pass

    return meta


def verify_archive(zip_path):
    """Check the acquisition archive is a complete, readable zip. Returns an
    error string, or None if the archive looks fine."""
    try:
        with zipfile.ZipFile(zip_path) as z:
            bad = z.testzip()
            if bad:
                return f"The archive is damaged (bad entry: {bad}). Re-collect the data."
        # Check we can at least see the acquisition metadata.
        if find_acquisition_json(zip_path) is None:
            return ("This does not look like a Raqeeb/androidqf archive "
                    "(no acquisition.json found). Have you picked the right file?")
    except zipfile.BadZipFile:
        return "The file is not a valid zip archive. Is it the archive Raqeeb produced?"
    except FileNotFoundError:
        return f"File not found: {zip_path}"
    except Exception as e:
        return f"Could not read the archive: {e}"
    return None


def friendly_reason(message):
    for needle, explanation in FRIENDLY:
        if needle in message:
            return explanation
    return "Flagged for manual review."


def write_html_report(results_dir, detections, warnings, metadata=None):
    """Write a clean browser report a non-technical person can read at a glance."""
    import html as _html

    metadata = metadata or {}
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

    # Device / acquisition info block, so the reader can see exactly what was scanned.
    meta_rows = ""
    fields = []
    if metadata.get("manufacturer") and metadata.get("device"):
        fields.append(("Device", f"{metadata.get('manufacturer')} {metadata.get('device')}".strip()))
    elif metadata.get("device"):
        fields.append(("Device", metadata.get("device")))
    if metadata.get("os"):
        fields.append(("Android", metadata.get("os")))
    if metadata.get("serial"):
        fields.append(("Serial", metadata.get("serial")))
    if metadata.get("app_count"):
        fields.append(("Apps recorded", metadata.get("app_count")))
    if metadata.get("id"):
        fields.append(("Acquisition ID", metadata.get("id")))
    fields.append(("Results folder", os.path.basename(results_dir) if results_dir else ""))
    for label, value in fields:
        if value:
            meta_rows += (f'<div class="mrow"><span class="mlabel">{_html.escape(label)}</span>'
                          f'<span class="mvalue">{_html.escape(str(value))}</span></div>')
    meta_html = f'<div class="meta"><div class="mtitle">Scanned data</div>{meta_rows}</div>' if meta_rows else ""

    # If some collection module did not complete, warn that this may be
    # partial evidence (it should be treated with extra caution).
    imperfect = ""
    modules = metadata.get("module_results") or []
    incomplete = [m for m in modules if m.get("status") in ("partial", "failed")]
    if incomplete:
        names = ", ".join(m.get("name", "?") for m in incomplete)
        imperfect = (f'<div class="advice"><h3 style="color:var(--warn)">Incomplete data</h3>'
                     f'<p style="color:var(--ink)">Some parts of the phone could not be collected '
                     f'({_html.escape(names)}). The scan below may be less complete than usual.</p></div>')

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
  .meta {{ background:var(--card); border:1px solid var(--line); border-radius:10px;
          padding:12px 16px; margin-top:18px; font-size:14px; }}
  .mtitle {{ color:var(--dim); font-size:11px; text-transform:uppercase;
            letter-spacing:.12em; margin-bottom:8px; }}
  .mrow {{ display:flex; justify-content:space-between; gap:16px; padding:3px 0;
          border-top:1px solid var(--line); }}
  .mrow:first-of-type {{ border-top:none; }}
  .mlabel {{ color:var(--dim); }}
  .mvalue {{ font-family:ui-monospace,Consolas,monospace; word-break:break-all;
            text-align:right; }}
</style></head><body><div class="wrap">
  <div class="brand">R A Q E E B &nbsp;·&nbsp; THE MUSLIM SHIELD</div>
  {meta_html}
  <div class="verdict {klass}">
    <div class="icon">{"✓" if clean else "⚠"}</div>
    <h1>{_html.escape(verdict)}</h1>
    <p>{_html.escape(sub)}</p>
  </div>
  {f'<div class="matches"><h3 style="color:var(--danger)">Matched spyware</h3><ul>{det_html}</ul></div>' if det_html else ''}
  {imperfect}
  {danger_block}
  {f'<div class="section-title">Things worth a quick look (not spyware)</div>{warn_html}' if warn_html else ''}
  <p class="foot">A clean result means no <b>known</b> spyware was found - it is not absolute proof
     the phone is clean. Technical details are saved in the results folder.</p>
</div></body></html>"""

    out = os.path.join(os.path.abspath(results_dir), "raqeeb-report.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    return out


def summarize(results_dir, metadata=None):
    metadata = metadata or {}
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
    device = metadata.get("device") or metadata.get("serial") or "this phone"
    print(DIM + f"  Scanned: {device}" + RESET)
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
        report = write_html_report(results_dir, detections, warnings, metadata)
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
        # Re-reading an existing scan: show the stored verdict from that folder.
        sys.exit(summarize(args.target))

    zip_path = repack_if_needed(args.target)

    # Major improvement: check the archive is complete and readable before
    # spending several minutes scanning it. Do not scan broken evidence.
    problem = verify_archive(args.target)
    if problem:
        print(RED + "  " + problem + RESET)
        sys.exit(1)

    metadata = read_metadata(zip_path) if zip_path else {}

    # Save results to a fresh, timestamped folder so a re-scan NEVER destroys
    # the previous (possibly important) findings. For a forensic tool it is
    # critical that past evidence remains available.
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    base = os.path.splitext(os.path.basename(args.target))[0]
    results = os.path.join(os.path.dirname(os.path.abspath(args.target)),
                           f"{base}-results-{stamp}")
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
    sys.exit(summarize(results, metadata))


if __name__ == "__main__":
    main()
