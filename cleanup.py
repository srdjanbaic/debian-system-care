import subprocess
import threading
import shutil
from pathlib import Path

from gi.repository import GLib


def run_privileged(command, on_output, on_finished):

    def worker():
        try:
            process = subprocess.Popen(
                ["pkexec"] + command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            for line in process.stdout:
                GLib.idle_add(
                    on_output,
                    line.rstrip()
                )

            return_code = process.wait()

            GLib.idle_add(
                on_finished,
                return_code == 0
            )

        except Exception as error:
            GLib.idle_add(on_output, str(error))
            GLib.idle_add(on_finished, False)

    threading.Thread(
        target=worker,
        daemon=True
    ).start()


def clean_apt_cache(on_output, on_finished):

    run_privileged(
        ["apt-get", "clean"],
        on_output,
        on_finished
    )


def preview_autoremove(on_finished):

    def worker():
        try:
            result = subprocess.run(
                ["apt-get", "-s", "autoremove"],
                capture_output=True,
                text=True,
                timeout=60
            )

            output = result.stdout + result.stderr

            GLib.idle_add(
                on_finished,
                result.returncode == 0,
                output
            )

        except Exception as error:
            GLib.idle_add(
                on_finished,
                False,
                str(error)
            )

    threading.Thread(
        target=worker,
        daemon=True
    ).start()


def remove_unused_packages(on_output, on_finished):

    run_privileged(
        ["apt-get", "-y", "autoremove"],
        on_output,
        on_finished
    )


def clear_thumbnails(on_finished):

    def worker():
        try:
            thumbnail_dir = (
                Path.home() / ".cache" / "thumbnails"
            )

            removed = 0

            if thumbnail_dir.exists():
                for item in thumbnail_dir.iterdir():
                    try:
                        if item.is_dir() and not item.is_symlink():
                            shutil.rmtree(item)
                        else:
                            item.unlink()

                        removed += 1

                    except OSError:
                        pass

            GLib.idle_add(
                on_finished,
                True,
                removed
            )

        except Exception:
            GLib.idle_add(
                on_finished,
                False,
                0
            )

    threading.Thread(
        target=worker,
        daemon=True
    ).start()
