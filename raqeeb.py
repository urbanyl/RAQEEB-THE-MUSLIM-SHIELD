"""Raqeeb - The Muslim Shield: launcher.

Presents the user with a choice of Android or iPhone, then runs the right
collection + spyware scan. Android is fully automated; iPhone is guided
(the user makes an encrypted backup, then Raqeeb scans it with mvt-ios).
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
COLLECTOR = os.path.join(HERE, "raqeeb-The.muslim.shield-v1.1.exe")
SCANNER = os.path.join(HERE, "raqeeb-scan.py")
MVT_DIR = os.path.join(HERE, "mvt", ".venv", "Scripts")
MVT_IOS = os.path.join(MVT_DIR, "mvt-ios.exe")
MVT_ANDROID = os.path.join(MVT_DIR, "mvt-android.exe")
IOS_TOOLS = os.path.join(HERE, "raqeeb-ios-tools")
IDEVICEINFO = os.path.join(IOS_TOOLS, "ideviceinfo.exe")
IDEVICEPAIR = os.path.join(IOS_TOOLS, "idevicepair.exe")
IDEVICEBACKUP2 = os.path.join(IOS_TOOLS, "idevicebackup2.exe")
BACKUP_PASSWORD = "raqeeb"  # encryption password set on the iPhone backup

CYAN, BLUE, GREEN, YELLOW, BOLD, DIM, RESET = (
    "\033[96m", "\033[94m", "\033[92m", "\033[93m", "\033[1m", "\033[2m", "\033[0m")

BANNER = f"""{BOLD}{BLUE}
   ██████╗  █████╗  ██████╗ ███████╗███████╗██████╗
   ██╔══██╗██╔══██╗██╔═══██╗██╔════╝██╔════╝██╔══██╗
   ██████╔╝███████║██║   ██║█████╗  █████╗  ██████╔╝
   ██╔══██╗██╔══██║██║▄▄ ██║██╔══╝  ██╔══╝  ██╔══██╗
   ██║  ██║██║  ██║╚██████╔╝███████╗███████╗██████╔╝
   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚══▀▀═╝ ╚══════╝╚══════╝╚═════╝{RESET}
{CYAN}        T H E   M U S L I M   S H I E L D{RESET}
"""


def ask_platform():
    print(BANNER)
    print("  Which phone do you want to check for spyware?\n")
    print(f"    {BOLD}1{RESET}) Android")
    print(f"    {BOLD}2{RESET}) iPhone (iOS)")
    print()
    while True:
        choice = input("  Enter 1 or 2: ").strip()
        if choice in ("1", "2"):
            return "android" if choice == "1" else "iphone"
        print(YELLOW + "  Please type 1 or 2." + RESET)


def newest_zip_in(folder):
    zips = [os.path.join(folder, f) for f in os.listdir(folder)
            if f.lower().endswith(".zip") and len(f) > 30]  # UUID-named
    return max(zips, key=os.path.getmtime) if zips else None


def run_android():
    print(f"\n{CYAN}== ANDROID =={RESET}")
    print("  1. Enable USB debugging on the phone (Settings > About phone,")
    print("     tap Build number 7x; then Developer options > USB debugging).")
    print("  2. Connect the phone by USB and tap 'Allow' on the phone.\n")
    input("  Press Enter when the phone is connected... ")

    print(DIM + "\n  Collecting data from the phone (tap 'Back up my data' on the phone)..." + RESET)
    subprocess.run([COLLECTOR], cwd=os.path.expanduser("~"))

    archive = newest_zip_in(os.path.expanduser("~"))
    if not archive:
        print(YELLOW + "  Could not find the collected archive. Was collection cancelled?" + RESET)
        return
    print(GREEN + f"\n  Collected: {archive}" + RESET)

    print(DIM + "  Scanning for spyware..." + RESET)
    subprocess.run([sys.executable, SCANNER, archive])


def run_iphone():
    print(f"\n{CYAN}== iPHONE (iOS) =={RESET}")
    print("  Raqeeb will make an encrypted backup of the iPhone and scan it.")
    print("  This is the same method Amnesty International uses - no jailbreak.\n")
    print("  1. Connect the iPhone by USB cable and unlock it.")
    print("  2. If the phone asks 'Trust This Computer?', tap Trust and enter")
    print("     the phone passcode.\n")
    input("  Press Enter when the iPhone is connected and unlocked... ")

    # 1. Wait for the device to be visible.
    info = subprocess.run([IDEVICEINFO], cwd=IOS_TOOLS, capture_output=True, text=True)
    if "No device found" in (info.stdout + info.stderr) or info.returncode != 0 and not info.stdout:
        print(YELLOW + "  No iPhone detected. Make sure it's unlocked and the Apple")
        print("  USB driver is installed (comes with iTunes / Apple Devices app)." + RESET)
        return

    # 2. Pair (triggers the Trust prompt on the phone if not already trusted).
    print(DIM + "  Pairing with the iPhone..." + RESET)
    pair = subprocess.run([IDEVICEPAIR, "pair"], cwd=IOS_TOOLS, capture_output=True, text=True)
    out = pair.stdout + pair.stderr
    if "Please accept the trust dialog" in out or "SUCCESS" not in out.upper():
        input("  Tap 'Trust' on the iPhone, enter its passcode, then press Enter... ")
        subprocess.run([IDEVICEPAIR, "pair"], cwd=IOS_TOOLS, capture_output=True, text=True)

    backup_dir = os.path.join(HERE, "iphone-backup")
    os.makedirs(backup_dir, exist_ok=True)

    # 3. Turn on backup encryption (MVT needs an encrypted backup for full data).
    print(DIM + "  Enabling encrypted backup..." + RESET)
    subprocess.run([IDEVICEBACKUP2, "encryption", "on", BACKUP_PASSWORD],
                   cwd=IOS_TOOLS, capture_output=True, text=True)

    # 4. Make the backup.
    print(DIM + "  Backing up the iPhone. This can take several minutes..." + RESET)
    subprocess.run([IDEVICEBACKUP2, "backup", "--full", backup_dir], cwd=IOS_TOOLS)

    # idevicebackup2 stores the backup in a sub-folder named by the device UDID.
    subdirs = [os.path.join(backup_dir, d) for d in os.listdir(backup_dir)
               if os.path.isdir(os.path.join(backup_dir, d))]
    target = max(subdirs, key=os.path.getmtime) if subdirs else backup_dir
    if not os.path.exists(os.path.join(target, "Manifest.plist")):
        print(YELLOW + "  Backup does not look complete (no Manifest.plist). Aborting scan." + RESET)
        return
    print(GREEN + f"\n  Backup saved: {target}" + RESET)

    # 5. Scan it with mvt-ios.
    results = os.path.join(HERE, "iphone-results")
    print(DIM + "  Decrypting and scanning the backup for spyware..." + RESET)
    subprocess.run([MVT_IOS, "check-backup", "--non-interactive",
                    "-p", BACKUP_PASSWORD, "-o", results, target])
    subprocess.run([sys.executable, SCANNER, "--summarize", results])


def main():
    os.system("")  # enable ANSI colours on Windows
    platform = ask_platform()
    if platform == "android":
        run_android()
    else:
        run_iphone()
    print(f"\n{DIM}  Done. A clean result means no KNOWN spyware was found -")
    print(f"  it is not absolute proof the phone is clean.{RESET}")
    input("\n  Press Enter to close... ")


if __name__ == "__main__":
    main()
