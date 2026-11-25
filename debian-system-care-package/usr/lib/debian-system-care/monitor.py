
import apt
import subprocess
import json
import time
import os
from pathlib import Path
from datetime import datetime

CHECK_INTERVAL = 60 * 60

STATE_DIR = Path.home() / ".local/state/debian-system-care"
STATE_FILE = STATE_DIR / "updates.json"


def load_previous_updates():
    try:
        with open(STATE_FILE, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_updates(updates):
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    temporary_file = STATE_FILE.with_suffix(".tmp")

    with open(temporary_file, "w") as file:
        json.dump(updates, file, indent=4)

    os.replace(temporary_file, STATE_FILE)


def send_notification(title, message):
    subprocess.run(
        [
            "notify-send",
            "-u", "normal",
            "-i", "system-software-update",
            title,
            message
        ],
        check=False
    )


def check_updates():
    try:
        cache = apt.Cache()
        cache.open()

        updates = {}

        for package in cache:
            if package.is_upgradable:
                updates[package.name] = package.candidate.version

        previous = load_previous_updates()

        print(
            f"[{datetime.now():%Y-%m-%d %H:%M:%S}] "
            f"Available updates: {len(updates)}",
            flush=True
        )

        if previous is None:
            if updates:
                send_notification(
                    "Debian System Care",
                    f"Available updates: {len(updates)}"
                )

        elif updates != previous:
            if updates:
                send_notification(
                    "Debian System Care",
                    f"Update list changed. Available updates: {len(updates)}"
                )
            else:
                send_notification(
                    "Debian System Care",
                    "Your system is up to date!"
                )

        save_updates(updates)

    except Exception as error:
        print(f"Monitor error: {error}", flush=True)


if __name__ == "__main__":
    print("Debian System Care monitor started.", flush=True)

    while True:
        check_updates()
        time.sleep(CHECK_INTERVAL)

