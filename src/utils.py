import datetime
import winreg


def get_current_week():
    return datetime.date.today().isocalendar()[1]

def get_windows_system_theme():
    theme = "Light"

    try:
        key_path_personalize = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path_personalize) as key:
            system_light_theme, _ = winreg.QueryValueEx(key, "SystemUsesLightTheme")
            theme = "Light" if system_light_theme == 1 else "Dark"
    except Exception as e:
        print(f"An error occurred while accessing theme settings: {e}")
    
    return theme


