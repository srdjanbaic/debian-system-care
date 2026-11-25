import subprocess
import threading
from gi.repository import GLib


def get_firewall_status(on_finished):

    def worker():
        try:
            result = subprocess.run(
                ["pkexec", "/usr/sbin/ufw", "status", "verbose"],
                capture_output=True,
                text=True,
                timeout=30
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

    threading.Thread(target=worker, daemon=True).start()


def run_firewall_command(command, on_output, on_finished):

    def worker():
        try:
            process = subprocess.Popen(
                ["pkexec", "/usr/sbin/ufw"] + command,
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

    threading.Thread(target=worker, daemon=True).start()


def enable_firewall(on_output, on_finished):
    run_firewall_command(
        ["--force", "enable"],
        on_output,
        on_finished
    )


def disable_firewall(on_output, on_finished):
    run_firewall_command(
        ["disable"],
        on_output,
        on_finished
    )
