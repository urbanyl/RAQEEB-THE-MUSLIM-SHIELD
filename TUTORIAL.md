# Raqeeb — How to scan your phone (step by step)

This guide is for **Windows**. It takes about 15 minutes the first time.

---

## What you need first

1. **Your phone** and a **USB cable** (a real data cable, not charge-only).
2. **Python** — free from [python.org/downloads](https://www.python.org/downloads/).
   During install, tick **"Add Python to PATH"**.
3. **Git** — free from [git-scm.com/downloads](https://git-scm.com/downloads).

---

## Step 1 — Download Raqeeb

Open a terminal (press Start, type `cmd`, press Enter) and run:

```bash
git clone https://github.com/Raqeeb-info/RAQEEB-THE-MUSLIM-SHIELD.git
cd RAQEEB-THE-MUSLIM-SHIELD
```

This downloads all the code into a folder called `RAQEEB-THE-MUSLIM-SHIELD`.

---

## Step 2 — Install the scanner (MVT)

Raqeeb uses MVT to do the actual spyware detection. Install it once:

```bash
pip install mvt
```

Then download the spyware fingerprint lists:

```bash
mvt-android download-iocs
```

---

## Step 3 — Get the collector

Download `raqeeb-The.muslim.shield.exe` from the
[**Releases page**](https://github.com/Raqeeb-info/RAQEEB-THE-MUSLIM-SHIELD/releases)
and put it in the `RAQEEB-THE-MUSLIM-SHIELD` folder.

> If Windows warns or blocks the file: right-click it → **Properties** →
> tick **Unblock** → **OK**. (Never turn off your antivirus to run it.)

---

## Step 4 — Turn on USB debugging (Android)

On the phone:

1. **Settings → About phone** → tap **Build number** 7 times.
2. **Settings → Developer options** → turn on **USB debugging**.
3. Plug the phone into the PC → tap **Allow** on the phone.

---

## Step 5 — Scan

Run the collector:

```bash
raqeeb-The.muslim.shield.exe
```

Tap **"Back up my data"** on the phone when it asks, then wait. It creates a
file named like `xxxxxxxx-xxxx-....zip`.

Then scan that file (replace the name with your actual file):

```bash
mvt-android check-androidqf --non-interactive -o results YOUR-FILE.zip
```

To also check links inside your text messages, add your phone PIN:

```bash
mvt-android check-androidqf --non-interactive -p YOUR-PIN -o results YOUR-FILE.zip
```

---

## Step 6 — Read the result

Show the result in plain language:

```bash
python raqeeb-scan.py --summarize results
```

A report opens in your browser:

- **Green — No spyware found:** nothing matched any known spyware.
- **Red — Spyware detected:** a match was found. Follow the on-screen
  advice: do **not** factory-reset (it destroys evidence), and contact
  [Amnesty's Security Lab](https://securitylab.amnesty.org/get-help/).

---

## Important

Raqeeb finds **known** spyware — the families researchers have already
documented (Pegasus, Predator, and others). A clean result means *nothing
known was found*, not a 100% guarantee. It is a helpful check, not proof.

Your phone's data stays on your own computer. Nothing is uploaded anywhere.
When you're done, delete the `.zip` files and the `results` folder to keep
your data private.
