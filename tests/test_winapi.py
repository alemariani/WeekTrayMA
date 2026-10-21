import sys
import types

import winapi


def test_module_imports_on_any_platform():
    assert hasattr(winapi, "read_apps_light_theme")


def test_autostart_command_frozen():
    assert winapi.autostart_command(True, r"C:\Apps\WeekTrayMA.exe", "x") == r'"C:\Apps\WeekTrayMA.exe"'


def test_autostart_command_from_source():
    cmd = winapi.autostart_command(False, r"C:\Py\python.exe", r"C:\src\main.py")
    assert cmd == r'"C:\Py\pythonw.exe" "C:\src\main.py"'


def test_theme_reads_default_to_light_when_key_missing(monkeypatch):
    def open_key(*args, **kwargs):
        raise FileNotFoundError()

    fake = types.SimpleNamespace(HKEY_CURRENT_USER=0, OpenKey=open_key)
    monkeypatch.setitem(sys.modules, "winreg", fake)
    assert winapi.read_apps_light_theme() is True
    assert winapi.read_taskbar_light_theme() is True
