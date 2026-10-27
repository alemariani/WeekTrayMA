from pathlib import Path

from settings import Settings, load_settings, save_settings, default_settings_path


def test_missing_file_gives_defaults(tmp_path):
    assert load_settings(tmp_path / "nope.json") == Settings()


def test_corrupt_file_gives_defaults(tmp_path):
    p = tmp_path / "s.json"
    p.write_text("{not json")
    assert load_settings(p) == Settings()


def test_non_dict_json_gives_defaults(tmp_path):
    p = tmp_path / "s.json"
    p.write_text("[1, 2]")
    assert load_settings(p) == Settings()


def test_unknown_theme_falls_back(tmp_path):
    p = tmp_path / "s.json"
    p.write_text('{"theme": "purple"}')
    assert load_settings(p).theme == "auto"


def test_round_trip_creates_dirs(tmp_path):
    p = tmp_path / "a" / "b" / "settings.json"
    save_settings(p, Settings(theme="dark"))
    assert load_settings(p) == Settings(theme="dark")
    assert not p.with_suffix(".tmp").exists()


def test_default_path_uses_appdata(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert default_settings_path() == tmp_path / "WeekTrayMA" / "settings.json"


def test_default_path_without_appdata(monkeypatch):
    monkeypatch.delenv("APPDATA", raising=False)
    assert default_settings_path().parts[-3:] == ("Roaming", "WeekTrayMA", "settings.json")


def test_default_path_without_any_home_directory(monkeypatch):
    def no_home():
        raise RuntimeError("Could not determine home directory.")

    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setattr(Path, "home", no_home)
    assert default_settings_path().parts[-2:] == ("WeekTrayMA", "settings.json")
