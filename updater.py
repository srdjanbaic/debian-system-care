
import subprocess
import threading
from gi.repository import GLib


def run_apt_command(command, on_output, on_finished):

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
            GLib.idle_add(
                on_output,
                str(error)
            )
            GLib.idle_add(
                on_finished,
                False
            )

    threading.Thread(
        target=worker,
        daemon=True
    ).start()


def refresh_package_lists(on_output, on_finished):
    run_apt_command(
        ["apt-get", "update"],
        on_output,
        on_finished
    )


def install_updates(on_output, on_finished):
    run_apt_command(
        ["apt-get", "-y", "full-upgrade"],
        on_output,
        on_finished
    )

