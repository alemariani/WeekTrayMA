import pystray

from icon_image import render_week_icon

APP_NAME = "WeekTrayMA"
THEME_CHOICES = (("Automatic", "auto"), ("Light", "light"), ("Dark", "dark"))


class Tray:
    '''
    Tray icon and menu. pystray runs its own message loop in a separate thread,
    so every callback passed in here is invoked on that thread.
    '''

    def __init__(self, on_open, on_set_theme, on_toggle_autostart, on_quit, get_theme, get_autostart):
        def theme_item(label, value):
            return pystray.MenuItem(label, lambda icon, item: on_set_theme(value),
                                    checked=lambda item: get_theme() == value, radio=True)

        menu = pystray.Menu(
            pystray.MenuItem("Open Calendar", lambda icon, item: on_open(), default=True, visible=False),
            pystray.MenuItem("Theme", pystray.Menu(*(theme_item(label, value) for label, value in THEME_CHOICES))),
            pystray.MenuItem("Start with Windows", lambda icon, item: on_toggle_autostart(),
                             checked=lambda item: get_autostart()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", lambda icon, item: on_quit()),
        )
        self._icon = pystray.Icon(APP_NAME, title=APP_NAME, menu=menu)

    def start(self):
        self._icon.run_detached()

    def stop(self):
        self._icon.stop()

    def set_week(self, week, light_taskbar):
        self._icon.icon = render_week_icon(week, light_taskbar)
        self._icon.title = f"{APP_NAME} – Week {week}"

    def refresh_menu(self):
        self._icon.update_menu()
