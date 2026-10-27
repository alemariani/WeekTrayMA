'''
Thin wrappers around the few Win32 APIs the app needs.
Windows-only modules and DLLs (winreg, ctypes.WinDLL) are touched only inside functions,
so this module can be imported, and its pure helpers tested, on any platform.
'''
import ctypes
import functools
import ntpath
import os
import sys
from ctypes import wintypes

PERSONALIZE_KEY = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE_NAME = "WeekTrayMA"

SPI_GETWORKAREA = 0x0030
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWCP_ROUND = 2
ERROR_ALREADY_EXISTS = 183

# kept alive for the whole process: the mutex is released when the process exits
_instance_mutex = None


# Private DLL handles, loaded once with their signatures declared once.
# They are separate from ctypes.windll, so other ctypes users (e.g. pystray)
# never see these argtypes.

@functools.cache
def _user32():
    user32 = ctypes.WinDLL("user32")
    user32.SystemParametersInfoW.argtypes = [wintypes.UINT, wintypes.UINT, ctypes.c_void_p, wintypes.UINT]
    user32.SystemParametersInfoW.restype = wintypes.BOOL
    user32.GetParent.argtypes = [wintypes.HWND]
    user32.GetParent.restype = wintypes.HWND
    user32.SetWindowRgn.argtypes = [wintypes.HWND, wintypes.HRGN, wintypes.BOOL]
    user32.SetWindowRgn.restype = ctypes.c_int
    return user32


@functools.cache
def _gdi32():
    gdi32 = ctypes.WinDLL("gdi32")
    gdi32.CreateRoundRectRgn.argtypes = [ctypes.c_int] * 6
    gdi32.CreateRoundRectRgn.restype = wintypes.HRGN
    return gdi32


@functools.cache
def _dwmapi():
    dwmapi = ctypes.WinDLL("dwmapi")
    dwmapi.DwmSetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
    dwmapi.DwmSetWindowAttribute.restype = ctypes.c_long
    return dwmapi


@functools.cache
def _kernel32():
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    return kernel32


def enable_dpi_awareness():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # system DPI aware
        return
    except (AttributeError, OSError):
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except (AttributeError, OSError):
        pass


def _read_personalize_flag(name):
    # missing key or value means an old/stripped Windows: treat it as light
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, PERSONALIZE_KEY) as key:
            value, _ = winreg.QueryValueEx(key, name)
            return value == 1
    except OSError:
        return True


def read_apps_light_theme():
    return _read_personalize_flag("AppsUseLightTheme")


def read_taskbar_light_theme():
    return _read_personalize_flag("SystemUsesLightTheme")


def primary_work_area():
    '''Return (left, top, right, bottom) of the primary monitor work area, in pixels.'''
    rect = wintypes.RECT()
    _user32().SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0)
    return rect.left, rect.top, rect.right, rect.bottom


def toplevel_hwnd(widget_id):
    '''Return the HWND of the top-level window that wraps a Tk widget.'''
    return _user32().GetParent(widget_id) or widget_id


def apply_rounded_corners(hwnd, width, height, radius):
    '''
    Windows 11: native antialiased corners through DWM.
    Older versions reject the attribute: fall back to a rounded window region.
    '''
    try:
        preference = ctypes.c_int(DWMWCP_ROUND)
        result = _dwmapi().DwmSetWindowAttribute(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE,
                                                 ctypes.byref(preference), ctypes.sizeof(preference))
        if result == 0:
            return
    except (AttributeError, OSError):
        pass

    region = _gdi32().CreateRoundRectRgn(0, 0, width + 1, height + 1, 2 * radius, 2 * radius)
    # the system owns the region after SetWindowRgn succeeds
    _user32().SetWindowRgn(hwnd, region, True)


def autostart_command(frozen, executable, script):
    if frozen:
        return f'"{executable}"'
    pythonw = ntpath.join(ntpath.dirname(executable), "pythonw.exe")
    return f'"{pythonw}" "{script}"'


def is_autostart_enabled():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, RUN_VALUE_NAME)
            return True
    except OSError:
        return False


def set_autostart(enabled):
    import winreg
    # CreateKeyEx also opens the key if it exists; it is missing on some stripped-down installs
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            command = autostart_command(getattr(sys, "frozen", False), sys.executable,
                                        os.path.abspath(sys.argv[0]))
            winreg.SetValueEx(key, RUN_VALUE_NAME, 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, RUN_VALUE_NAME)
            except FileNotFoundError:
                pass


def acquire_single_instance(name="Local\\WeekTrayMA"):
    '''Return False if another instance already holds the named mutex.'''
    global _instance_mutex
    _instance_mutex = _kernel32().CreateMutexW(None, False, name)
    return ctypes.get_last_error() != ERROR_ALREADY_EXISTS
