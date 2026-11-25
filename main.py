
import gi
import apt
import os
import platform
import subprocess
import threading

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk

from updater import install_updates, refresh_package_lists
from cleanup import (
    clean_apt_cache,
    preview_autoremove,
    remove_unused_packages,
    clear_thumbnails
)

from antivirus import scan_directory, stop_scan

from firewall import (
    get_firewall_status,
    enable_firewall,
    disable_firewall
)


class SystemCare:

    def __init__(self):
        self.window = Gtk.Window(
            title="Debian System Care"
        )
        self.window.set_default_size(760, 680)
        self.window.set_position(Gtk.WindowPosition.CENTER)
        self.window.connect("destroy", Gtk.main_quit)

        self.load_styles()

        # Main layout
        main = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0
        )
        self.window.add(main)

        # Header
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title("Debian System Care")
        header.set_subtitle("System maintenance")
        self.window.set_titlebar(header)

        app_icon = Gtk.Image.new_from_icon_name(
            "system-software-update",
            Gtk.IconSize.DIALOG
        )
        header.pack_start(app_icon)

        menu_button = Gtk.MenuButton()
        menu_button.set_image(
            Gtk.Image.new_from_icon_name(
                "open-menu-symbolic",
                Gtk.IconSize.BUTTON
            )
        )

        menu = Gtk.Menu()

        about_item = Gtk.MenuItem(label="About")
        about_item.connect("activate", self.show_about)
        menu.append(about_item)

        menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect(
            "activate",
            lambda item: Gtk.main_quit()
        )
        menu.append(quit_item)

        menu.show_all()
        menu_button.set_popup(menu)
        header.pack_end(menu_button)

        # Scrollable content
        self.main_scroll = Gtk.ScrolledWindow()
        self.main_scroll.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC
        )
        self.main_scroll.set_hexpand(True)
        self.main_scroll.set_vexpand(True)

        main.pack_start(
            self.main_scroll, True, True, 0
        )

        # Content
        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=16
        )
        content.set_margin_start(22)
        content.set_margin_end(22)
        content.set_margin_top(20)
        content.set_margin_bottom(20)

        self.main_scroll.add(content)

        # Welcome section
        welcome = Gtk.Label()
        welcome.set_markup(
            "<span size='20000' weight='bold'>"
            "System Overview"
            "</span>"
        )
        welcome.set_xalign(0)
        content.pack_start(welcome, False, False, 0)

        description = Gtk.Label(
            label="Monitor your Debian system and manage updates."
        )
        description.set_xalign(0)
        description.get_style_context().add_class("muted")
        content.pack_start(description, False, False, 0)

        # System information cards
        system_title = Gtk.Label()
        system_title.set_markup(
            "<b>System Information</b>"
        )
        system_title.set_xalign(0)
        content.pack_start(system_title, False, False, 3)

        info_grid = Gtk.Grid()
        info_grid.set_column_spacing(12)
        info_grid.set_row_spacing(12)
        content.pack_start(info_grid, False, False, 0)

        self.distro_value = self.create_info_card(
            info_grid, 0, 0,
            "Debian Version",
            self.get_debian_version()
        )

        self.kernel_value = self.create_info_card(
            info_grid, 1, 0,
            "Linux Kernel",
            platform.release()
        )

        self.arch_value = self.create_info_card(
            info_grid, 0, 1,
            "Architecture",
            platform.machine()
        )

        self.host_value = self.create_info_card(
            info_grid, 1, 1,
            "Hostname",
            platform.node()
        )

        # Update section
        update_title = Gtk.Label()
        update_title.set_markup(
            "<b>Software Updates</b>"
        )
        update_title.set_xalign(0)
        content.pack_start(update_title, False, False, 3)

        update_card = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12
        )
        update_card.get_style_context().add_class("card")

        content.pack_start(
            update_card, False, False, 0
        )

        self.status = Gtk.Label(
            label="System status: Ready"
        )
        self.status.set_xalign(0)
        update_card.pack_start(
            self.status, False, False, 0
        )

        self.update_count = Gtk.Label(
            label="Available updates: Not checked"
        )
        self.update_count.set_xalign(0)
        update_card.pack_start(
            self.update_count, False, False, 0
        )

        # Buttons
        buttons = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=10
        )

        self.check_button = Gtk.Button(
            label="Check for Updates"
        )
        self.check_button.set_image(
            Gtk.Image.new_from_icon_name(
                "view-refresh-symbolic",
                Gtk.IconSize.BUTTON
            )
        )
        self.check_button.set_always_show_image(True)
        self.check_button.connect(
            "clicked", self.check_updates
        )

        buttons.pack_start(
            self.check_button, True, True, 0
        )

        self.install_button = Gtk.Button(
            label="Install All Updates"
        )
        self.install_button.set_image(
            Gtk.Image.new_from_icon_name(
                "system-software-install-symbolic",
                Gtk.IconSize.BUTTON
            )
        )
        self.install_button.set_always_show_image(True)
        self.install_button.get_style_context().add_class(
            "suggested-action"
        )
        self.install_button.connect(
            "clicked", self.start_installation
        )
        self.install_button.set_sensitive(False)

        buttons.pack_start(
            self.install_button, True, True, 0
        )

        update_card.pack_start(
            buttons, False, False, 0
        )

        # Progress bar
        self.progress = Gtk.ProgressBar()
        self.progress.set_show_text(True)
        self.progress.set_text("Ready")

        update_card.pack_start(
            self.progress, False, False, 0
        )

        self.result = Gtk.Label(
            label="Update information will appear here."
        )
        self.result.set_xalign(0)
        self.result.set_line_wrap(True)

        update_card.pack_start(
            self.result, False, False, 0
        )


        # System Cleanup section
        cleanup_title = Gtk.Label()
        cleanup_title.set_markup("<b>System Cleanup</b>")
        cleanup_title.set_xalign(0)
        content.pack_start(cleanup_title, False, False, 3)

        cleanup_card = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12
        )
        cleanup_card.get_style_context().add_class("card")
        content.pack_start(cleanup_card, False, False, 0)

        self.cleanup_status = Gtk.Label(
            label="System cleanup: Ready"
        )
        self.cleanup_status.set_xalign(0)
        cleanup_card.pack_start(
            self.cleanup_status, False, False, 0
        )

        cleanup_buttons = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8
        )

        self.clean_cache_button = Gtk.Button(
            label="Clean APT Cache"
        )
        self.clean_cache_button.connect(
            "clicked", self.start_cache_cleanup
        )
        cleanup_buttons.pack_start(
            self.clean_cache_button, True, True, 0
        )

        self.autoremove_button = Gtk.Button(
            label="Remove Unused Packages"
        )
        self.autoremove_button.connect(
            "clicked", self.start_autoremove_preview
        )
        cleanup_buttons.pack_start(
            self.autoremove_button, True, True, 0
        )

        self.thumbnails_button = Gtk.Button(
            label="Clean Thumbnails"
        )
        self.thumbnails_button.connect(
            "clicked", self.start_thumbnail_cleanup
        )
        cleanup_buttons.pack_start(
            self.thumbnails_button, True, True, 0
        )

        cleanup_card.pack_start(
            cleanup_buttons, False, False, 0
        )


        # Antivirus Protection section
        antivirus_title = Gtk.Label()
        antivirus_title.set_markup("<b>Antivirus Protection</b>")
        antivirus_title.set_xalign(0)
        content.pack_start(antivirus_title, False, False, 3)

        antivirus_card = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12
        )
        antivirus_card.get_style_context().add_class("card")
        content.pack_start(antivirus_card, False, False, 0)

        self.antivirus_status = Gtk.Label(
            label="Antivirus: Ready"
        )
        self.antivirus_status.set_xalign(0)
        antivirus_card.pack_start(
            self.antivirus_status, False, False, 0
        )

        self.antivirus_directory = Gtk.Label(
            label="Selected location: Home directory"
        )
        self.antivirus_directory.set_xalign(0)
        self.antivirus_directory.set_line_wrap(True)
        antivirus_card.pack_start(
            self.antivirus_directory, False, False, 0
        )

        antivirus_buttons = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8
        )

        self.antivirus_home_button = Gtk.Button(
            label="Scan Home"
        )
        self.antivirus_home_button.connect(
            "clicked", self.start_home_scan
        )
        antivirus_buttons.pack_start(
            self.antivirus_home_button, True, True, 0
        )

        self.antivirus_folder_button = Gtk.Button(
            label="Choose Folder"
        )
        self.antivirus_folder_button.connect(
            "clicked", self.choose_scan_folder
        )
        antivirus_buttons.pack_start(
            self.antivirus_folder_button, True, True, 0
        )

        self.antivirus_stop_button = Gtk.Button(
            label="Stop Scan"
        )
        self.antivirus_stop_button.connect(
            "clicked", self.stop_antivirus_scan
        )
        self.antivirus_stop_button.set_sensitive(False)
        antivirus_buttons.pack_start(
            self.antivirus_stop_button, True, True, 0
        )

        antivirus_card.pack_start(
            antivirus_buttons, False, False, 0
        )

        self.antivirus_progress = Gtk.ProgressBar()
        self.antivirus_progress.set_show_text(True)
        self.antivirus_progress.set_text("Ready")
        antivirus_card.pack_start(
            self.antivirus_progress, False, False, 0
        )

        antivirus_log_scroll = Gtk.ScrolledWindow()
        antivirus_log_scroll.set_min_content_height(120)
        antivirus_log_scroll.set_policy(
            Gtk.PolicyType.AUTOMATIC,
            Gtk.PolicyType.AUTOMATIC
        )

        self.antivirus_log_view = Gtk.TextView()
        self.antivirus_log_view.set_editable(False)
        self.antivirus_log_view.set_cursor_visible(False)
        self.antivirus_log_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.antivirus_log_view.set_left_margin(8)
        self.antivirus_log_view.set_right_margin(8)
        self.antivirus_log_view.set_top_margin(8)
        self.antivirus_log_view.set_bottom_margin(8)

        antivirus_log_scroll.add(self.antivirus_log_view)
        antivirus_card.pack_start(
            antivirus_log_scroll, False, False, 0
        )

        # Firewall section
        firewall_title = Gtk.Label()
        firewall_title.set_markup("<b>Firewall Protection</b>")
        firewall_title.set_xalign(0)
        content.pack_start(firewall_title, False, False, 3)

        firewall_card = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12
        )
        firewall_card.get_style_context().add_class("card")
        content.pack_start(firewall_card, False, False, 0)

        self.firewall_status = Gtk.Label(
            label="Firewall status: Not checked"
        )
        self.firewall_status.set_xalign(0)
        self.firewall_status.set_markup(
            "<b>Firewall status:</b> Not checked"
        )
        firewall_card.pack_start(
            self.firewall_status, False, False, 0
        )

        self.firewall_details = Gtk.Label(
            label="Click Refresh Status to inspect UFW."
        )
        self.firewall_details.set_xalign(0)
        self.firewall_details.set_line_wrap(True)
        self.firewall_details.set_selectable(True)
        firewall_card.pack_start(
            self.firewall_details, False, False, 0
        )

        firewall_buttons = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8
        )

        self.firewall_refresh_button = Gtk.Button(
            label="Refresh Status"
        )
        self.firewall_refresh_button.connect(
            "clicked", self.refresh_firewall_status
        )
        firewall_buttons.pack_start(
            self.firewall_refresh_button, True, True, 0
        )

        self.firewall_enable_button = Gtk.Button(
            label="Enable Firewall"
        )
        self.firewall_enable_button.get_style_context().add_class(
            "suggested-action"
        )
        self.firewall_enable_button.connect(
            "clicked", self.start_firewall_enable
        )
        firewall_buttons.pack_start(
            self.firewall_enable_button, True, True, 0
        )

        self.firewall_disable_button = Gtk.Button(
            label="Disable Firewall"
        )
        self.firewall_disable_button.connect(
            "clicked", self.start_firewall_disable
        )
        firewall_buttons.pack_start(
            self.firewall_disable_button, True, True, 0
        )

        firewall_card.pack_start(
            firewall_buttons, False, False, 0
        )

        self.firewall_enable_button.set_sensitive(False)
        self.firewall_disable_button.set_sensitive(False)

        # Log section
        log_title = Gtk.Label()
        log_title.set_markup(
            "<b>Activity Log</b>"
        )
        log_title.set_xalign(0)
        content.pack_start(log_title, False, False, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_min_content_height(130)
        scroll.get_style_context().add_class("log-card")

        self.log = Gtk.TextView()
        self.log.set_editable(False)
        self.log.set_cursor_visible(False)
        self.log.set_wrap_mode(Gtk.WrapMode.WORD)
        self.log.set_left_margin(10)
        self.log.set_right_margin(10)
        self.log.set_top_margin(10)
        self.log.set_bottom_margin(10)

        scroll.add(self.log)
        content.pack_start(scroll, True, True, 0)

        # Footer
        footer = Gtk.Label(
            label="Debian System Care 2.0"
        )
        footer.get_style_context().add_class("muted")
        content.pack_start(footer, False, False, 0)

        self.window.show_all()

    # CSS styling
    def load_styles(self):

        css = b"""
        window {
            background-color: @theme_bg_color;
        }

        .card {
            background-color: @theme_base_color;
            border: 1px solid alpha(@theme_fg_color, 0.12);
            border-radius: 10px;
            padding: 16px;
        }

        .info-card {
            background-color: @theme_base_color;
            border: 1px solid alpha(@theme_fg_color, 0.12);
            border-radius: 10px;
            padding: 12px;
        }

        .info-title {
            color: @theme_unfocused_fg_color;
            font-size: 10pt;
        }

        .info-value {
            font-size: 12pt;
            font-weight: bold;
        }

        .muted {
            color: @theme_unfocused_fg_color;
        }

        .log-card {
            background-color: @theme_base_color;
            border: 1px solid alpha(@theme_fg_color, 0.12);
            border-radius: 8px;
        }

        button {
            padding: 8px;
        }
        """

        provider = Gtk.CssProvider()
        provider.load_from_data(css)

        screen = Gdk.Screen.get_default()

        Gtk.StyleContext.add_provider_for_screen(
            screen,
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    # Create information card
    def create_info_card(
        self, grid, column, row, title, value
    ):

        card = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=7
        )
        card.get_style_context().add_class("info-card")

        title_label = Gtk.Label(label=title)
        title_label.set_xalign(0)
        title_label.get_style_context().add_class(
            "info-title"
        )

        value_label = Gtk.Label(label=value)
        value_label.set_xalign(0)
        value_label.set_ellipsize(3)
        value_label.get_style_context().add_class(
            "info-value"
        )

        card.pack_start(
            title_label, False, False, 0
        )
        card.pack_start(
            value_label, False, False, 0
        )

        grid.attach(
            card, column, row, 1, 1
        )

        return value_label

    # Debian version
    def get_debian_version(self):

        try:
            with open("/etc/os-release", "r") as file:
                for line in file:
                    if line.startswith("PRETTY_NAME="):
                        return line.split("=", 1)[1].strip().strip('"')

        except Exception:
            pass

        return "Unknown"

    # About dialog
    def show_about(self, item):

        dialog = Gtk.AboutDialog()
        dialog.set_transient_for(self.window)
        dialog.set_modal(True)
        dialog.set_program_name("Debian System Care")
        dialog.set_version("2.0")
        dialog.set_comments(
            "System maintenance and update manager for Debian."
        )
        dialog.set_website("https://www.debian.org/")
        dialog.set_logo_icon_name(
            "system-software-update"
        )
        dialog.set_authors([
            "Debian System Care"
        ])

        dialog.run()
        dialog.destroy()

    # Log output
    def write_log(self, message):

        buffer = self.log.get_buffer()
        end = buffer.get_end_iter()

        buffer.insert(
            end, message + "\n"
        )

        return False

    # Check for updates
    def check_updates(self, button):

        self.check_button.set_sensitive(False)
        self.install_button.set_sensitive(False)

        self.status.set_text(
            "Refreshing package lists..."
        )

        self.result.set_text(
            "Connecting to Debian repositories..."
        )

        self.progress.set_fraction(0)
        self.progress.set_text("Refreshing APT...")
        self.progress.pulse()

        self.log.get_buffer().set_text(
            "Refreshing Debian package lists...\n\n"
        )

        GLib.timeout_add(
            100, self.update_check_progress
        )

        refresh_package_lists(
            self.write_log,
            self.refresh_finished
        )

        return False

    def update_check_progress(self):

        if self.status.get_text() == "Refreshing package lists...":
            self.progress.pulse()
            return True

        return False

    # Refresh completed
    def refresh_finished(self, success):

        if not success:

            self.status.set_text(
                "System status: Update check failed"
            )

            self.result.set_text(
                "Could not refresh package lists."
            )

            self.progress.set_text("Failed")
            self.check_button.set_sensitive(True)

            return False

        self.status.set_text(
            "Checking available updates..."
        )

        self.result.set_text(
            "Reading refreshed APT package information..."
        )

        self.progress.set_fraction(0)
        self.progress.set_text("Checking updates...")

        def worker():

            try:
                cache = apt.Cache()
                cache.open()

                updates = [
                    (
                        package.name,
                        package.installed.version,
                        package.candidate.version
                    )
                    for package in cache
                    if package.is_upgradable
                ]

                GLib.idle_add(
                    self.show_updates,
                    updates
                )

            except Exception as error:

                GLib.idle_add(
                    self.show_error,
                    str(error)
                )

        threading.Thread(
            target=worker,
            daemon=True
        ).start()

        return False

    # Show updates
    def show_updates(self, updates):

        count = len(updates)

        self.update_count.set_text(
            f"Available updates: {count}"
        )

        if count:

            names = "\n".join(
                f"{name}: {installed} → {candidate}"
                for name, installed, candidate in updates
            )

            self.log.get_buffer().set_text(names)

            self.status.set_text(
                "System status: Updates available"
            )

            self.result.set_text(
                "Updates are ready to install."
            )

            self.install_button.set_sensitive(True)

            self.progress.set_fraction(1)
            self.progress.set_text("Updates found")

        else:

            self.log.get_buffer().set_text(
                "Your system is up to date!"
            )

            self.status.set_text(
                "System status: Healthy"
            )

            self.result.set_text(
                "No available updates found."
            )

            self.install_button.set_sensitive(False)

            self.progress.set_fraction(1)
            self.progress.set_text(
                "System is up to date"
            )

        self.check_button.set_sensitive(True)

        return False

    # Error handling
    def show_error(self, error):

        self.status.set_text(
            "System status: Error"
        )

        self.result.set_text(
            "Could not check updates."
        )

        self.write_log(error)

        self.check_button.set_sensitive(True)
        self.install_button.set_sensitive(False)

        self.progress.set_text("Error")

        return False

    # Start installation
    def start_installation(self, button):

        self.check_button.set_sensitive(False)
        self.install_button.set_sensitive(False)

        self.status.set_text(
            "Installing system updates..."
        )

        self.result.set_text(
            "Please wait. Do not close the application."
        )

        self.progress.set_fraction(0)
        self.progress.set_text("Installing updates...")
        self.progress.pulse()

        self.log.get_buffer().set_text(
            "Starting full system upgrade...\n\n"
        )

        GLib.timeout_add(
            100, self.update_progress
        )

        install_updates(
            self.write_log,
            self.installation_finished
        )

        return False

    def update_progress(self):

        if self.status.get_text() == "Installing system updates...":
            self.progress.pulse()
            return True

        return False

    # Installation finished
    def installation_finished(self, success):

        if success:

            self.status.set_text(
                "System status: Installation complete"
            )

            self.result.set_text(
                "System updates installed successfully!"
            )

            self.progress.set_fraction(1)
            self.progress.set_text("Completed")

            subprocess.run(
                [
                    "notify-send",
                    "Debian System Care",
                    "System updates installed successfully!"
                ],
                check=False
            )

        else:

            self.status.set_text(
                "System status: Installation failed"
            )

            self.result.set_text(
                "Check the log for installation errors."
            )

            self.progress.set_fraction(0)
            self.progress.set_text("Failed")

        self.check_button.set_sensitive(True)

        # Check again after installation
        self.check_updates(None)

        return False


    # Cleanup helpers
    def set_cleanup_buttons(self, enabled):

        self.clean_cache_button.set_sensitive(enabled)
        self.autoremove_button.set_sensitive(enabled)
        self.thumbnails_button.set_sensitive(enabled)

    def start_cache_cleanup(self, button):

        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Clean APT package cache?"
        )
        dialog.format_secondary_text(
            "This will remove downloaded package files. "
            "Installed programs will not be removed."
        )

        response = dialog.run()
        dialog.destroy()

        if response != Gtk.ResponseType.YES:
            return

        self.set_cleanup_buttons(False)
        self.cleanup_status.set_text("Cleaning APT cache...")
        self.write_log("Starting APT cache cleanup...")

        clean_apt_cache(
            self.write_log,
            self.cleanup_finished
        )

    def start_autoremove_preview(self, button):

        self.set_cleanup_buttons(False)
        self.cleanup_status.set_text(
            "Checking packages that can be removed..."
        )
        self.write_log("Simulating APT autoremove...")

        preview_autoremove(
            self.autoremove_preview_finished
        )

    def autoremove_preview_finished(self, success, output):

        if not success:
            self.cleanup_status.set_text(
                "Could not inspect unused packages."
            )
            self.write_log(output)
            self.set_cleanup_buttons(True)
            return False

        dialog = Gtk.Dialog(
            title="Review packages to remove",
            transient_for=self.window,
            modal=True
        )
        dialog.add_button(
            "Cancel", Gtk.ResponseType.CANCEL
        )
        dialog.add_button(
            "Remove Packages", Gtk.ResponseType.OK
        )

        dialog.set_default_size(620, 420)

        area = dialog.get_content_area()
        area.set_spacing(10)
        area.set_margin_start(12)
        area.set_margin_end(12)
        area.set_margin_top(12)
        area.set_margin_bottom(12)

        explanation = Gtk.Label(
            label=(
                "APT simulation. Review the proposed changes "
                "before allowing package removal."
            )
        )
        explanation.set_xalign(0)
        explanation.set_line_wrap(True)
        area.pack_start(explanation, False, False, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(280)
        scroll.set_vexpand(True)

        preview = Gtk.TextView()
        preview.set_editable(False)
        preview.set_cursor_visible(False)
        preview.set_wrap_mode(Gtk.WrapMode.WORD)
        preview.set_left_margin(8)
        preview.set_right_margin(8)
        preview.set_top_margin(8)
        preview.set_bottom_margin(8)
        preview.get_buffer().set_text(output)

        scroll.add(preview)
        area.pack_start(scroll, True, True, 0)

        dialog.show_all()
        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.OK:
            self.cleanup_status.set_text(
                "Removing unused packages..."
            )
            self.write_log(
                "Starting confirmed APT autoremove..."
            )

            remove_unused_packages(
                self.write_log,
                self.cleanup_finished
            )
        else:
            self.cleanup_status.set_text(
                "Package removal cancelled."
            )
            self.write_log("Package removal cancelled.")
            self.set_cleanup_buttons(True)

        return False

    def start_thumbnail_cleanup(self, button):

        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Clean thumbnail cache?"
        )
        dialog.format_secondary_text(
            "Cached image thumbnails will be deleted. "
            "They will be recreated automatically when needed."
        )

        response = dialog.run()
        dialog.destroy()

        if response != Gtk.ResponseType.YES:
            return

        self.set_cleanup_buttons(False)
        self.cleanup_status.set_text(
            "Cleaning thumbnail cache..."
        )
        self.write_log("Starting thumbnail cache cleanup...")

        clear_thumbnails(
            self.thumbnail_cleanup_finished
        )

    def cleanup_finished(self, success):

        if success:
            self.cleanup_status.set_text(
                "System cleanup completed successfully."
            )
            self.write_log("Cleanup completed successfully.")

            subprocess.run(
                [
                    "notify-send",
                    "Debian System Care",
                    "System cleanup completed successfully!"
                ],
                check=False
            )
        else:
            self.cleanup_status.set_text(
                "Cleanup failed. Check Activity Log."
            )
            self.write_log("Cleanup failed.")

        self.set_cleanup_buttons(True)
        return False

    def thumbnail_cleanup_finished(self, success, removed):

        if success:
            self.cleanup_status.set_text(
                f"Thumbnail cleanup completed. Items removed: {removed}"
            )
            self.write_log(
                f"Thumbnail cleanup completed. Items removed: {removed}"
            )
        else:
            self.cleanup_status.set_text(
                "Thumbnail cleanup failed."
            )
            self.write_log("Thumbnail cleanup failed.")

        self.set_cleanup_buttons(True)
        return False


    # Firewall management
    def refresh_firewall_status(self, button):

        self.firewall_refresh_button.set_sensitive(False)
        self.firewall_enable_button.set_sensitive(False)
        self.firewall_disable_button.set_sensitive(False)

        self.firewall_status.set_text(
            "Firewall status: Checking..."
        )
        self.firewall_details.set_text(
            "Reading UFW configuration..."
        )

        get_firewall_status(
            self.firewall_status_finished
        )

        return False

    def firewall_status_finished(self, success, output):

        self.firewall_refresh_button.set_sensitive(True)

        if not success:
            self.firewall_status.set_text(
                "Firewall status: Could not read status"
            )
            self.firewall_details.set_text(output)
            self.firewall_enable_button.set_sensitive(False)
            self.firewall_disable_button.set_sensitive(False)
            return False

        status_line = next(
            (
                line.strip()
                for line in output.splitlines()
                if line.strip().lower().startswith("status:")
            ),
            "Status: Unknown"
        )

        active = status_line.lower().endswith("active")

        self.firewall_status.set_text(
            "Firewall status: " + (
                "ACTIVE" if active else "INACTIVE"
            )
        )

        self.firewall_details.set_text(output.strip())

        self.firewall_enable_button.set_sensitive(not active)
        self.firewall_disable_button.set_sensitive(active)

        return False

    def confirm_firewall_action(self, title, message):

        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text=title
        )

        dialog.format_secondary_text(message)
        response = dialog.run()
        dialog.destroy()

        return response == Gtk.ResponseType.YES

    def start_firewall_enable(self, button):

        confirmed = self.confirm_firewall_action(
            "Enable Firewall?",
            "UFW will be enabled. Incoming connections will "
            "follow your configured firewall rules."
        )

        if not confirmed:
            return

        self.firewall_buttons_busy()
        self.firewall_status.set_text(
            "Firewall status: Enabling..."
        )

        self.write_log("Enabling UFW firewall...")

        enable_firewall(
            self.write_log,
            self.firewall_command_finished
        )

    def start_firewall_disable(self, button):

        confirmed = self.confirm_firewall_action(
            "Disable Firewall?",
            "This will turn off firewall protection. "
            "Your computer will no longer filter connections "
            "using UFW until it is enabled again."
        )

        if not confirmed:
            return

        self.firewall_buttons_busy()
        self.firewall_status.set_text(
            "Firewall status: Disabling..."
        )

        self.write_log("Disabling UFW firewall...")

        disable_firewall(
            self.write_log,
            self.firewall_command_finished
        )

    def firewall_buttons_busy(self):

        self.firewall_refresh_button.set_sensitive(False)
        self.firewall_enable_button.set_sensitive(False)
        self.firewall_disable_button.set_sensitive(False)

    def firewall_command_finished(self, success):

        if success:
            self.write_log("Firewall command completed.")
        else:
            self.write_log("Firewall command failed.")

        self.refresh_firewall_status(None)
        return False

    def start_home_scan(self, button):
        self.start_antivirus_scan(os.path.expanduser("~"))

    def choose_scan_folder(self, button):

        dialog = Gtk.FileChooserDialog(
            title="Choose Folder to Scan",
            parent=self.window,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
            buttons=(
                Gtk.STOCK_CANCEL,
                Gtk.ResponseType.CANCEL,
                "Scan Folder",
                Gtk.ResponseType.ACCEPT
            )
        )

        response = dialog.run()
        directory = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT and directory:
            self.start_antivirus_scan(directory)

    def start_antivirus_scan(self, directory):

        self.antivirus_home_button.set_sensitive(False)
        self.antivirus_folder_button.set_sensitive(False)
        self.antivirus_stop_button.set_sensitive(True)

        self.antivirus_status.set_text(
            "Antivirus: Scanning..."
        )
        self.antivirus_directory.set_text(
            "Selected location: " + directory
        )

        self.antivirus_progress.set_fraction(0)
        self.antivirus_progress.set_text("Scanning...")

        self.antivirus_log_view.get_buffer().set_text("")

        self.antivirus_log(
            "Starting ClamAV scan: " + directory
        )

        scan_directory(
            directory,
            self.antivirus_log,
            self.antivirus_scan_finished
        )

    def antivirus_log(self, message):

        buffer = self.antivirus_log_view.get_buffer()
        buffer.insert(
            buffer.get_end_iter(),
            message + "\\n"
        )

        return False

    def stop_antivirus_scan(self, button):

        if stop_scan():
            self.antivirus_status.set_text(
                "Antivirus: Stopping scan..."
            )
            self.antivirus_log("Stopping scan...")

        return False

    def antivirus_scan_finished(self, return_code, infected_count):

        self.antivirus_home_button.set_sensitive(True)
        self.antivirus_folder_button.set_sensitive(True)
        self.antivirus_stop_button.set_sensitive(False)

        self.antivirus_progress.set_fraction(1.0)

        if return_code == 0:
            self.antivirus_status.set_text(
                "Antivirus: No threats found"
            )
            self.antivirus_progress.set_text("Scan completed")
            self.antivirus_log(
                "Scan completed. No infected files found."
            )

        elif return_code == 1:
            self.antivirus_status.set_text(
                "Antivirus: Threats detected!"
            )
            self.antivirus_progress.set_text(
                str(infected_count) + " threat(s) found"
            )
            self.antivirus_log(
                "WARNING: Found " + str(infected_count) +
                " infected file(s). No files were deleted."
            )

        elif return_code < 0:
            self.antivirus_status.set_text(
                "Antivirus: Scan stopped"
            )
            self.antivirus_progress.set_text("Stopped")
            self.antivirus_log("Scan was interrupted.")

        else:
            self.antivirus_status.set_text(
                "Antivirus: Scan error"
            )
            self.antivirus_progress.set_text("Error")
            self.antivirus_log(
                "ClamAV scan failed. Exit code: " +
                str(return_code)
            )

        return False

    def run(self):
        Gtk.main()


app = SystemCare()
app.run()




