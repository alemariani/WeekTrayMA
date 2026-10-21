from dataclasses import dataclass

THEME_SETTINGS = ("auto", "light", "dark")


@dataclass(frozen=True)
class Palette:
    bg: str
    bg2: str
    accent: str
    text: str
    muted: str


LIGHT = Palette("#f9ecec", "#edc5c5", "#E85F5C", "#020222", "#73738c")
DARK = Palette("#232234", "#3e3c5d", "#00fefe", "#EEEEFF", "#686868")


def resolve(setting, apps_light):
    '''
    Return the palette for a theme setting.
    "auto" (and any unknown value) follows the Windows app theme.
    '''
    if setting == "light":
        return LIGHT
    if setting == "dark":
        return DARK
    return LIGHT if apps_light else DARK
