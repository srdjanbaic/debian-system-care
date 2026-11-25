import subprocess
import threading
from pathlib import Path
from gi.repository import GLib


_active_process = None
_process_lock = threading.Lock()


def scan_directory(directory, on_output, on_finished):
    """
    Scan a directory in a background thread.

    Return codes:
        0  - no threats found
        1  - threats found
        2  - scanning error
    """

    def worker():
        global _active_process

        infected_count = 0

        try:
            scan_path = Path(directory).expanduser().resolve()

            if not scan_path.is_dir():
                raise ValueError(
                    "Selected location is not a directory."
                )

            command = [
                "/usr/bin/clamscan",
                "--recursive",
                "--infected",
                "--no-summary",
                str(scan_path)
            ]

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            with _process_lock:
                _active_process = process

            for line in process.stdout:
                line = line.rstrip()

                if line:
                    GLib.idle_add(on_output, line)

                    if line.endswith(" FOUND"):
                        infected_count += 1

            return_code = process.wait()

        except Exception as error:
            GLib.idle_add(on_output, str(error))
            return_code = 2

        finally:
            with _process_lock:
                _active_process = None

        GLib.idle_add(
            on_finished,
            return_code,
            infected_count
        )

    threading.Thread(
        target=worker,
        daemon=True
    ).start()


def stop_scan():
    global _active_process

    with _process_lock:
        process = _active_process

    if process and process.poll() is None:
        process.terminate()
        return True

    return False
