# Raqeeb — The Muslim Shield (رقيب)

> **Raqeeb** (Arabic: رقيب, "The Watchful") is a beginner-friendly tool for collecting forensic data from an Android phone to check it for traces of spyware such as Pegasus and Predator.

**Raqeeb is a fork of [androidqf](https://github.com/mvt-project/androidqf)** (Android Quick Forensics) by [Amnesty International's Security Lab](https://securitylab.amnesty.org/), originally developed by [Claudio Guarnieri](https://github.com/botherder/). It is rebranded and simplified for non-technical users; all forensic functionality is unchanged. The data it collects is analyzed with [MVT](https://github.com/mvt-project/mvt).

Licensed under the [MVT License 1.1](https://license.mvt.re/1.1/) — see [License](#license).

---

## What it does

Raqeeb does **not** scan your phone by itself. It works in two stages:

1. **Collect** — Raqeeb copies forensic data off the phone over USB: the list of installed apps, the app files (APKs), SMS messages, running processes, system logs, and settings. It saves all of this into a single archive.
2. **Scan** — you run [MVT](https://github.com/mvt-project/mvt) on that archive. MVT compares everything against public lists of known-spyware "fingerprints" and reports anything that matches.

> **Important:** A clean result means *no known spyware was found* — not that the phone is guaranteed clean. Raqeeb detects **known** spyware families. It cannot see inside other apps' private storage without root, and it cannot guarantee detection of brand-new, never-before-seen implants. It is a helpful check, not absolute proof.

---

## Quick start (Windows)

### 1. Download

Get `raqeeb-The.muslim.shield.exe` from the [latest release](../../releases/latest).

### 2. If Windows blocks it

Because Raqeeb is a small open-source tool and the download is **not code-signed**, Windows may warn about it or block it. This is expected for independent software — it is not a sign that anything is wrong. To allow it:

- **SmartScreen warning** ("Windows protected your PC"): click **More info** → **Run anyway**.
- **"Blocked by your organization's Device Guard / Smart App Control policy":**
  1. Right-click the downloaded `.exe` → **Properties**.
  2. At the bottom, tick **Unblock**, then click **OK**.
  3. Run it again.

  If it is still blocked, your PC has **Smart App Control** turned on, which only runs software Microsoft already recognizes. You can either run Raqeeb on a different PC, or (advanced) build it yourself from this source — see [Build](#build).

> Never turn off Smart App Control or your antivirus just to run a tool. A tool that asks you to disable your security to run it is behaving like malware. Raqeeb will never ask you to do that — the **Unblock** step above is all that is needed on a normal PC.

### 3. Prepare the phone

1. On the phone: **Settings → About phone**, tap **Build number** seven times to unlock Developer options.
2. **Settings → Developer options → enable USB debugging.**
3. Connect the phone to the PC with a USB **data** cable and tap **Allow** on the "Allow USB debugging?" prompt.

### 4. Collect

Double-click `raqeeb-The.muslim.shield.exe` (or run it from a terminal). It runs automatically — no questions to answer — except that your phone will show a **"Back up my data"** screen: tap it (leave the password blank). When it finishes it writes an archive named `<UUID>.zip`.

### 5. Scan the archive with MVT

Install [MVT](https://github.com/mvt-project/mvt), then:

```bash
mvt-android download-iocs
mvt-android check-androidqf --non-interactive -o results <UUID>.zip
```

To also check the links inside your SMS messages, add your device PIN:

```bash
mvt-android check-androidqf --non-interactive -p YOUR-PIN -o results <UUID>.zip
```

### 6. (Optional) Friendly result reader

`raqeeb-scan.py` in this repo runs the scan and prints a plain-language verdict (green **CLEAN** or red **SPYWARE DETECTED**) instead of MVT's raw logs:

```bash
python raqeeb-scan.py <UUID>.zip           # add -p YOUR-PIN to include SMS
```

---

## Build

Building it yourself produces a binary your own PC trusts (no Smart App Control block).

Requirements: [Go](https://go.dev/dl/) 1.24+, and the Android platform-tools (`adb.exe` and its two DLLs) plus the `collector_*` binaries in `assets/` (see the upstream build docs or `build_locally.sh`).

```bash
go build -o raqeeb.exe .
```

---

## Encryption & potential threats

Carrying acquisitions on an unencrypted drive can expose you — and the people whose data you collected — to serious risk (for example, if a drive is seized at a border). Ideally keep the drive fully encrypted.

Raqeeb can also encrypt each acquisition with an [age](https://age-encryption.org) public key. Place a `key.txt` file (one age recipient per line) in the working directory or next to the executable, and Raqeeb writes an encrypted `<UUID>.zip.age` instead of a plaintext zip. Ideally the matching private key is one the person carrying the drive does **not** hold, so the data cannot be decrypted under duress:

```bash
age --decrypt -i ~/path/to/privatekey.txt -o <UUID>.zip <UUID>.zip.age
```

---

## License

The purpose of Raqeeb (and androidqf) is to facilitate the ***consensual forensic analysis*** of devices belonging to people who might be targeted by sophisticated mobile spyware — especially members of civil society and marginalized communities. It must **not** be used to violate the privacy of non-consenting individuals.

Raqeeb is released under the [MVT License 1.1](https://license.mvt.re/1.1/), an adaptation of the Mozilla Public License v2.0 with an added "Consensual Use Restriction" (clause 3.0) permitting use only with the explicit consent of the person whose data is being extracted and analyzed.
