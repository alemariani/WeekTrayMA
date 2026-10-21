import time
import tkinter as tk
from datetime import date

import winapi
from calendar_window import CalendarWindow
from settings import default_settings_path, load_settings, save_settings
from theme import resolve
from tray import Tray

POLL_MS = 2000
# a tray click right after a focus-out hide is the same click that caused the hide
TRAY_CLICK_GUARD_S = 0.3


class App:
    '''
    Owns all state and runs on the Tk (main) thread.
    Tray callbacks arrive on pystray's thread and are forwarded here with root.after.
    '''

    def __init__(self):
        self.root = tk.Tk()
        self.settings_path = default_settings_path()
        self.settings = load_settings(self.settings_path)
        self.apps_light = winapi.read_apps_light_theme()
        self.taskbar_light = winapi.read_taskbar_light_theme()
        self.week = date.today().isocalendar()[1]

        scale = self.root.winfo_fpixels("1i") / 96
        self.calendar = CalendarWindow(self.root, resolve(self.settings.theme, self.apps_light), scale)
        self.tray = Tray(
            on_open=self._from_tray(self._toggle_calendar),
            on_set_theme=lambda value: self.root.after(0, self._set_theme, value),
            on_toggle_autostart=self._from_tray(self._toggle_autostart),
            on_quit=self._from_tray(self._quit),
            get_theme=lambda: self.settings.theme,
            get_autostart=winapi.is_autostart_enabled,
        )
        self.tray.set_week(self.week, self.taskbar_light)

    def run(self):
        # start the tray from inside the mainloop, so its callbacks always find it running
        self.root.after(0, self.tray.start)
        self._poll_job = self.root.after(POLL_MS, self._poll)
        self.root.mainloop()

    def _from_tray(self, handler):
        return lambda: self.root.after(0, handler)

    def _toggle_calendar(self):
        if self.calendar.is_visible:
            self.calendar.hide()
        elif time.monotonic() - self.calendar.last_hidden_at < TRAY_CLICK_GUARD_S:
            pass
        else:
            self.calendar.show()

    def _set_theme(self, value):
        self.settings.theme = value
        try:
            save_settings(self.settings_path, self.settings)
        except OSError:
            pass  # keep the choice for this session even if it can't be saved
        self.calendar.set_palette(resolve(value, self.apps_light))
        self.tray.refresh_menu()

    def _toggle_autostart(self):
        try:
            winapi.set_autostart(not winapi.is_autostart_enabled())
        except OSError:
            pass
        self.tray.refresh_menu()

    def _quit(self):
        self.root.after_cancel(self._poll_job)
        self.tray.stop()
        self.root.destroy()

    def _poll(self):
        # reschedule first: one failed update (e.g. a transient icon error) must not stop polling for good
        self._poll_job = self.root.after(POLL_MS, self._poll)

        week = date.today().isocalendar()[1]
        taskbar_light = winapi.read_taskbar_light_theme()
        if week != self.week or taskbar_light != self.taskbar_light:
            self.week, self.taskbar_light = week, taskbar_light
            self.tray.set_week(week, taskbar_light)

        apps_light = winapi.read_apps_light_theme()
        if apps_light != self.apps_light:
            self.apps_light = apps_light
            if self.settings.theme == "auto":
                self.calendar.set_palette(resolve("auto", apps_light))
