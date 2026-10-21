'''
Tests that need tkinter (and, for real windows, a display).
They are skipped where tkinter or a display is unavailable.
'''
import contextlib
import os
import types

import pytest

pytest.importorskip("tkinter")
os.environ.setdefault("PYSTRAY_BACKEND", "dummy")

import tkinter as tk  # noqa: E402

import app as app_module  # noqa: E402
import winapi  # noqa: E402
from calendar_window import CalendarWindow  # noqa: E402
from settings import Settings  # noqa: E402
from theme import DARK  # noqa: E402

needs_display = pytest.mark.skipif(not os.environ.get("DISPLAY"), reason="needs a display")


def test_poll_reschedules_even_if_tray_update_fails(monkeypatch):
    monkeypatch.setattr(winapi, "read_taskbar_light_theme", lambda: False)
    monkeypatch.setattr(winapi, "read_apps_light_theme", lambda: True)

    class FailingTray:
        def set_week(self, week, light_taskbar):
            raise OSError("temp folder unavailable")

    scheduled = []
    a = app_module.App.__new__(app_module.App)
    a.root = types.SimpleNamespace(after=lambda ms, fn: scheduled.append(fn) or "job")
    a.tray = FailingTray()
    a.settings = Settings()
    a.week, a.taskbar_light, a.apps_light = 0, True, True

    with contextlib.suppress(OSError):
        a._poll()
    assert scheduled == [a._poll]


@needs_display
def test_show_keeps_window_transparent_until_painted(monkeypatch):
    events = []
    monkeypatch.setattr(winapi, "primary_work_area", lambda: (0, 0, 1024, 768))
    monkeypatch.setattr(winapi, "toplevel_hwnd", lambda widget_id: widget_id)
    monkeypatch.setattr(winapi, "apply_rounded_corners", lambda *args: events.append("corners"))

    root = tk.Tk()
    try:
        window = CalendarWindow(root, DARK, 1.0)
        real_attributes, real_deiconify, real_update = root.attributes, root.deiconify, root.update

        def attributes(*args):
            if args[:1] == ("-alpha",) and len(args) == 2:
                events.append(("alpha", float(args[1])))
            return real_attributes(*args)

        monkeypatch.setattr(root, "attributes", attributes)
        monkeypatch.setattr(root, "deiconify", lambda: (events.append("deiconify"), real_deiconify()))
        monkeypatch.setattr(root, "update", lambda: (events.append("update"), real_update()))

        window.show()
        assert window.is_visible
        assert ("alpha", 0.0) in events and ("alpha", 1.0) in events
        order = [events.index(e) for e in (("alpha", 0.0), "deiconify", "update", "corners", ("alpha", 1.0))]
        assert order == sorted(order)
    finally:
        root.destroy()
