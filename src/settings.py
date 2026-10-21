import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path

from theme import THEME_SETTINGS


@dataclass
class Settings:
    theme: str = "auto"


def default_settings_path():
    appdata = os.environ.get("APPDATA")
    base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    return base / "WeekTrayMA" / "settings.json"


def load_settings(path):
    '''
    Read settings from a JSON file. Never raises: anything missing or invalid
    falls back to its default value.
    '''
    settings = Settings()
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return settings
    if not isinstance(data, dict):
        return settings
    if data.get("theme") in THEME_SETTINGS:
        settings.theme = data["theme"]
    return settings


def save_settings(path, settings):
    # write to a temp file and swap it in, so a crash never leaves a half-written file
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
    os.replace(tmp, path)
