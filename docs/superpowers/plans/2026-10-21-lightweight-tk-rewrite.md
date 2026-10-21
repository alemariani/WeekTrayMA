# Lightweight Tk Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite WeekTrayMA on plain tkinter so the calendar opens in one step, animates smoothly, survives rapid clicks, and gains theme / autostart settings and rounded corners, with fewer dependencies.

**Architecture:** Tk runs in the main thread and owns all state; pystray runs detached and forwards clicks via `root.after(0, ...)`. The calendar is one `tk.Canvas` built once and only shown/hidden. All logic that can be pure (month grid, animation stepping, theme, settings, icon image) lives in modules without tkinter so it is unit-tested on Linux.

**Tech Stack:** Python ≥ 3.10, tkinter (stdlib), ctypes + winreg (stdlib), Pillow 12, pystray 0.19.5, pytest, pyflakes, PyInstaller.

**Spec:** `docs/superpowers/specs/2026-10-21-lightweight-tk-rewrite-design.md`

## Global Constraints

- Python ≥ 3.10; Windows 10 and 11 only at runtime.
- Runtime dependencies: `pillow==12.0.0`, `pystray==0.19.5` only. No customtkinter, darkdetect, packaging, pywin32.
- Dev dependencies (`requirements-dev.txt`): `-r requirements.txt`, `pytest`, `pyflakes`, `pyinstaller`.
- Module names lowercase. Code, comments, identifiers in English.
- Pure modules (`month_model`, `animation`, `theme`, `settings`, `icon_image`) must not import tkinter, pystray, winreg or `ctypes.windll` at import time.
- `winapi.py` must be importable on Linux: import `winreg` and use `ctypes.windll` only inside functions.
- The dev container has no tkinter and no Windows: GUI modules are verified by `python -m pyflakes src` + `python -m py_compile`, then the owner's manual checklist (spec, "Testing").
- Tests run with `python -m pytest` from repo root; `pytest.ini` sets `pythonpath = src` and `testpaths = tests`.
- Pinned values: animation 180 ms ease-out cubic; tray-click guard 300 ms after a focus-out hide; screen margin 12 px logical; Win10 corner radius 8 px logical; system poll every 2 s; mutex `Local\WeekTrayMA`; settings `%APPDATA%\WeekTrayMA\settings.json`; Run value name `WeekTrayMA`; tooltip `WeekTrayMA – Week {n}` (en dash).

## Review Focus

1. **ISO week at year boundaries** (Dec 2026 has week 53; 28 Dec 2026–3 Jan 2027 is week 53; 4 Jan 2027 is week 1) → week labels correct. Pinned in Task 1.
2. **Clicking `<<`/`>>` many times during an animation** → never more than two pages, every outgoing page deleted, last month fully in place. Pinned in Task 2.
3. **Missing/corrupt settings file, unknown theme value, missing `APPDATA`** → defaults, no crash. Pinned in Task 3.
4. **Theme registry values missing** (e.g. LTSC, key absent) → treated as light, no crash. Pinned in Task 4.
5. **Midnight passes while the app runs** → next open shows the new today and the correct month; icon updates at the next poll. Pinned in Task 1 (`needs_redraw`).

---

### Task 1: Test scaffolding and month model

**Files:**
- Create: `pytest.ini`, `requirements-dev.txt`, `src/month_model.py`, `tests/test_month_model.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class Day: date: datetime.date; in_month: bool; is_today: bool`
  - `@dataclass(frozen=True) class Week: number: int; days: tuple[Day, ...]`
  - `month_grid(year: int, month: int, today: datetime.date) -> list[Week]` — always 6 weeks, Monday-first, starting at the Monday on or before the 1st; `number` is the ISO week of that week's Monday.
  - `shift_month(year: int, month: int, delta: int) -> tuple[int, int]`
  - `needs_redraw(shown: tuple[int, int], drawn_today: datetime.date, today: datetime.date) -> bool` — True if `shown != (today.year, today.month)` or `drawn_today != today`.

- [ ] **Step 1: Create `pytest.ini`** (`[pytest]`, `pythonpath = src`, `testpaths = tests`) and `requirements-dev.txt` (see Global Constraints).

- [ ] **Step 2: Write the failing tests** in `tests/test_month_model.py`:

```python
from datetime import date
from month_model import month_grid, shift_month, needs_redraw

def test_grid_always_has_six_weeks_of_seven_days():
    for month in range(1, 13):
        weeks = month_grid(2025, month, date(2025, 1, 1))
        assert len(weeks) == 6
        assert all(len(w.days) == 7 for w in weeks)

def test_grid_starts_on_monday_on_or_before_first():
    weeks = month_grid(2025, 6, date(2025, 1, 1))  # 1 Jun 2025 is a Sunday
    assert weeks[0].days[0].date == date(2025, 5, 26)
    assert weeks[0].days[0].in_month is False
    assert weeks[0].days[6].date == date(2025, 6, 1)
    assert weeks[0].days[6].in_month is True

def test_month_starting_on_monday_begins_with_the_first():
    weeks = month_grid(2025, 9, date(2025, 1, 1))  # 1 Sep 2025 is a Monday
    assert weeks[0].days[0].date == date(2025, 9, 1)

def test_iso_week_numbers_across_year_boundary():
    weeks = month_grid(2026, 12, date(2026, 12, 1))
    assert [w.number for w in weeks] == [49, 50, 51, 52, 53, 1]
    weeks = month_grid(2027, 1, date(2027, 1, 1))
    assert weeks[0].number == 53
    assert weeks[0].days[0].date == date(2026, 12, 28)
    assert weeks[1].number == 1

def test_today_flag_only_on_today():
    weeks = month_grid(2025, 7, date(2025, 7, 24))
    flagged = [d.date for w in weeks for d in w.days if d.is_today]
    assert flagged == [date(2025, 7, 24)]

def test_shift_month_wraps_years():
    assert shift_month(2025, 12, 1) == (2026, 1)
    assert shift_month(2025, 1, -1) == (2024, 12)
    assert shift_month(2025, 5, 0) == (2025, 5)
    assert shift_month(2025, 5, 14) == (2026, 7)

def test_needs_redraw():
    today = date(2026, 10, 21)
    assert needs_redraw((2026, 10), today, today) is False
    assert needs_redraw((2026, 11), today, today) is True
    assert needs_redraw((2026, 10), date(2026, 10, 20), today) is True
```

- [ ] **Step 3: Run** `python -m pytest tests/test_month_model.py -v` — Expected: FAIL (`ModuleNotFoundError: month_model`).

- [ ] **Step 4: Implement `src/month_model.py`** with the interfaces above (use `datetime.timedelta` from the 1st minus `weekday()` days; `date.isocalendar()[1]`).

- [ ] **Step 5: Run** `python -m pytest tests/test_month_model.py -v` — Expected: 7 passed.

- [ ] **Step 6: Commit** `git add pytest.ini requirements-dev.txt src/month_model.py tests/test_month_model.py && git commit -m "Add pure month model with tests"`

---

### Task 2: Slide animation stepper

**Files:**
- Create: `src/animation.py`, `tests/test_animation.py`

**Interfaces:**
- Produces:
  - `ease_out_cubic(t: float) -> float` — `1 - (1 - t) ** 3`, with `t` clamped to `[0, 1]`.
  - `class PageSlide`:
    - `__init__(self, move: Callable[[str, float], None], delete: Callable[[str], None], duration: float = 0.18)`
    - `start(self, outgoing: str, incoming: str, distance: float, now: float) -> None` — if active, `finish()` first. The incoming page has already been drawn offset by `+distance` on x; over the animation both tags move by `-distance` in total.
    - `step(self, now: float) -> bool` — moves both tags by the eased offset delta since the previous step; when `now - start >= duration`, completes (exact remaining delta, `delete(outgoing)`), returns False; otherwise True.
    - `finish(self) -> None` — no-op when inactive; else moves the remaining delta, deletes outgoing, becomes inactive.
    - `active: bool` (property)

- [ ] **Step 1: Write the failing tests** in `tests/test_animation.py`, using a fake canvas that records `moves: dict[str, float]` (summed dx per tag) and `deleted: list[str]`:

```python
import pytest
from animation import PageSlide, ease_out_cubic

class FakeCanvas:
    def __init__(self):
        self.moves, self.deleted = {}, []
    def move(self, tag, dx):
        self.moves[tag] = self.moves.get(tag, 0.0) + dx
    def delete(self, tag):
        self.deleted.append(tag)

def make():
    c = FakeCanvas()
    return c, PageSlide(c.move, c.delete, duration=0.18)

def test_ease_out_cubic_bounds_and_clamp():
    assert ease_out_cubic(0) == 0 and ease_out_cubic(1) == 1
    assert ease_out_cubic(-1) == 0 and ease_out_cubic(2) == 1
    assert ease_out_cubic(0.5) > 0.5

def test_full_run_moves_exact_distance_and_deletes_outgoing():
    c, s = make()
    s.start("p0", "p1", 300.0, now=10.0)
    assert s.step(10.05) is True
    assert s.step(10.18) is False
    assert c.moves["p0"] == pytest.approx(-300.0)
    assert c.moves["p1"] == pytest.approx(-300.0)
    assert c.deleted == ["p0"] and not s.active

def test_first_step_moves_immediately():
    c, s = make()
    s.start("p0", "p1", 300.0, now=0.0)
    s.step(0.016)
    assert c.moves["p1"] < -10

def test_restart_while_active_snaps_previous_then_starts_new():
    c, s = make()
    s.start("p0", "p1", 300.0, now=0.0)
    s.step(0.05)
    s.start("p1", "p2", -300.0, now=0.06)
    assert c.deleted == ["p0"]
    assert c.moves["p1"] == pytest.approx(-300.0)
    s.step(1.0)
    assert c.deleted == ["p0", "p1"]
    assert c.moves["p2"] == pytest.approx(300.0)

def test_many_rapid_restarts_leave_only_last_page():
    c, s = make()
    tags = [f"p{i}" for i in range(10)]
    for i in range(9):
        s.start(tags[i], tags[i + 1], 300.0, now=i * 0.01)
        s.step(i * 0.01 + 0.005)
    s.finish()
    assert c.deleted == tags[:9]
    assert not s.active

def test_finish_when_inactive_is_noop():
    c, s = make()
    s.finish()
    assert c.moves == {} and c.deleted == []
```

- [ ] **Step 2: Run** `python -m pytest tests/test_animation.py -v` — Expected: FAIL (`ModuleNotFoundError`).
- [ ] **Step 3: Implement `src/animation.py`.** Track `applied` offset (sum moved so far); each step moves `target - applied` where `target = -distance * ease_out_cubic(elapsed / duration)`.
- [ ] **Step 4: Run** `python -m pytest tests/test_animation.py -v` — Expected: 6 passed.
- [ ] **Step 5: Commit** `git commit -m "Add time-based page slide animation stepper"` (with the two files added).

---

### Task 3: Theme palettes and settings persistence

**Files:**
- Create: `src/theme.py`, `src/settings.py`, `tests/test_theme.py`, `tests/test_settings.py`

**Interfaces:**
- Produces (`theme.py`):
  - `THEME_SETTINGS: tuple[str, ...] = ("auto", "light", "dark")`
  - `@dataclass(frozen=True) class Palette: bg: str; bg2: str; accent: str; text: str; muted: str`
  - `LIGHT = Palette("#f9ecec", "#edc5c5", "#E85F5C", "#020222", "#73738c")`
  - `DARK = Palette("#232234", "#3e3c5d", "#00fefe", "#EEEEFF", "#686868")`
  - `resolve(setting: str, apps_light: bool) -> Palette` — `"light"`→LIGHT, `"dark"`→DARK, anything else → by `apps_light`.
- Produces (`settings.py`):
  - `@dataclass class Settings: theme: str = "auto"`
  - `default_settings_path() -> pathlib.Path` — `$APPDATA/WeekTrayMA/settings.json`; if `APPDATA` unset, `Path.home() / "AppData" / "Roaming" / "WeekTrayMA" / "settings.json"`.
  - `load_settings(path: Path) -> Settings` — missing file, invalid JSON, non-dict, or theme not in `THEME_SETTINGS` → default for that field; never raises.
  - `save_settings(path: Path, settings: Settings) -> None` — creates parent dirs; writes `path.with_suffix(".tmp")` then `os.replace`.

- [ ] **Step 1: Write the failing tests.**

`tests/test_theme.py`:
```python
from theme import resolve, LIGHT, DARK

def test_resolve_all_combinations():
    assert resolve("light", False) is LIGHT
    assert resolve("dark", True) is DARK
    assert resolve("auto", True) is LIGHT
    assert resolve("auto", False) is DARK
    assert resolve("bogus", False) is DARK
```

`tests/test_settings.py`:
```python
from pathlib import Path
from settings import Settings, load_settings, save_settings, default_settings_path

def test_missing_file_gives_defaults(tmp_path):
    assert load_settings(tmp_path / "nope.json") == Settings()

def test_corrupt_file_gives_defaults(tmp_path):
    p = tmp_path / "s.json"; p.write_text("{not json")
    assert load_settings(p) == Settings()

def test_non_dict_json_gives_defaults(tmp_path):
    p = tmp_path / "s.json"; p.write_text("[1, 2]")
    assert load_settings(p) == Settings()

def test_unknown_theme_falls_back(tmp_path):
    p = tmp_path / "s.json"; p.write_text('{"theme": "purple"}')
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
```

- [ ] **Step 2: Run** `python -m pytest tests/test_theme.py tests/test_settings.py -v` — Expected: FAIL (`ModuleNotFoundError`).
- [ ] **Step 3: Implement `src/theme.py` and `src/settings.py`** per Interfaces.
- [ ] **Step 4: Run** the same command — Expected: 8 passed.
- [ ] **Step 5: Commit** `git commit -m "Add theme palettes and settings persistence"`.

---

### Task 4: Windows API helpers

**Files:**
- Create: `src/winapi.py`, `tests/test_winapi.py`

**Interfaces:**
- Produces (all Windows calls via `ctypes.windll` / lazily imported `winreg`):
  - `enable_dpi_awareness() -> None` — `shcore.SetProcessDpiAwareness(1)`, fallback `user32.SetProcessDPIAware()`, swallow errors.
  - `read_apps_light_theme() -> bool` / `read_taskbar_light_theme() -> bool` — `HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize`, values `AppsUseLightTheme` / `SystemUsesLightTheme`; `True` on any `OSError`.
  - `primary_work_area() -> tuple[int, int, int, int]` — `(left, top, right, bottom)` via `SystemParametersInfoW(SPI_GETWORKAREA=0x0030)` into a `wintypes.RECT`.
  - `apply_rounded_corners(hwnd: int, width: int, height: int, radius: int) -> None` — try `dwmapi.DwmSetWindowAttribute(hwnd, 33, byref(c_int(2)), 4)`; if it returns non-zero (or raises), `user32.SetWindowRgn(hwnd, gdi32.CreateRoundRectRgn(0, 0, width + 1, height + 1, 2 * radius, 2 * radius), True)`.
  - `autostart_command(frozen: bool, executable: str, script: str) -> str` — pure: frozen → `f'"{executable}"'`; else `f'"{pythonw}" "{script}"'` where `pythonw` is `pythonw.exe` in `executable`'s directory (`ntpath`, so it tests on Linux).
  - `is_autostart_enabled() -> bool`, `set_autostart(enabled: bool) -> None` — `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`, value `WeekTrayMA` (`REG_SZ`); command from `autostart_command(getattr(sys, "frozen", False), sys.executable, os.path.abspath(sys.argv[0]))`; deleting a missing value is not an error.
  - `acquire_single_instance(name: str = "Local\\WeekTrayMA") -> bool` — `kernel32.CreateMutexW(None, False, name)`, keep the handle in a module global, return `GetLastError() != 183` (`ERROR_ALREADY_EXISTS`).

- [ ] **Step 1: Write the failing tests** in `tests/test_winapi.py`:

```python
import sys, types
import winapi

def test_module_imports_on_any_platform():
    assert hasattr(winapi, "read_apps_light_theme")

def test_autostart_command_frozen():
    assert winapi.autostart_command(True, r"C:\Apps\WeekTrayMA.exe", "x") == r'"C:\Apps\WeekTrayMA.exe"'

def test_autostart_command_from_source():
    cmd = winapi.autostart_command(False, r"C:\Py\python.exe", r"C:\src\main.py")
    assert cmd == r'"C:\Py\pythonw.exe" "C:\src\main.py"'

def test_theme_reads_default_to_light_when_key_missing(monkeypatch):
    fake = types.SimpleNamespace(
        HKEY_CURRENT_USER=0,
        OpenKey=lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError()),
    )
    monkeypatch.setitem(sys.modules, "winreg", fake)
    assert winapi.read_apps_light_theme() is True
    assert winapi.read_taskbar_light_theme() is True
```

- [ ] **Step 2: Run** `python -m pytest tests/test_winapi.py -v` — Expected: FAIL (`ModuleNotFoundError`).
- [ ] **Step 3: Implement `src/winapi.py`** per Interfaces (`import winreg` inside each registry function).
- [ ] **Step 4: Run** `python -m pytest tests/test_winapi.py -v && python -m pyflakes src/winapi.py` — Expected: 4 passed, no pyflakes output.
- [ ] **Step 5: Commit** `git commit -m "Add ctypes/winreg Windows helpers"`.

---

### Task 5: Tray icon image

**Files:**
- Create: `src/icon_image.py`, `tests/test_icon_image.py`

**Interfaces:**
- Produces: `render_week_icon(week: int, light_taskbar: bool, size: int = 64) -> PIL.Image.Image` — RGBA, transparent background, digits black if `light_taskbar` else white, centered (`anchor="mm"`). Font: `ImageFont.truetype("arial.ttf", s)`, on `OSError` `ImageFont.load_default(size=s)`; start at `s = size` and decrease until `draw.textbbox` width and height are ≤ `size - 4`.

- [ ] **Step 1: Write the failing tests:**

```python
from icon_image import render_week_icon

def test_two_digit_weeks_fit_with_padding():
    for week in (1, 8, 48, 53, 88):
        bbox = render_week_icon(week, light_taskbar=True).getbbox()
        assert bbox is not None
        left, top, right, bottom = bbox
        assert left >= 2 and top >= 2 and right <= 62 and bottom <= 62

def test_digit_color_follows_taskbar():
    dark = render_week_icon(42, light_taskbar=False)
    light = render_week_icon(42, light_taskbar=True)
    assert max(p[0] for p in dark.getdata() if p[3] == 255) == 255
    assert min(p[0] for p in light.getdata() if p[3] == 255) == 0
```

- [ ] **Step 2: Run** `python -m pytest tests/test_icon_image.py -v` — Expected: FAIL.
- [ ] **Step 3: Implement `src/icon_image.py`.**
- [ ] **Step 4: Run** the same command — Expected: 2 passed.
- [ ] **Step 5: Commit** `git commit -m "Render tray week icon sized to fit"`.

---

### Task 6: Canvas calendar window

**Files:**
- Create: `src/calendar_window.py`

**Interfaces:**
- Consumes: `month_grid`, `shift_month`, `needs_redraw` (Task 1); `PageSlide` (Task 2); `Palette` (Task 3); `primary_work_area`, `apply_rounded_corners` (Task 4).
- Produces: `class CalendarWindow` — uses the given `tk.Tk` root as the popup window.
  - `__init__(self, root: tk.Tk, palette: Palette, scale: float)` — `overrideredirect(True)`, `-topmost`, builds the canvas, draws the current month, binds `<FocusOut>` to `hide`, then `withdraw()`.
  - `show(self) -> None` — redraw without animation if `needs_redraw(...)`; position; `update_idletasks()`; `deiconify()`; apply rounded corners; `focus_force()`.
  - `hide(self) -> None` — `PageSlide.finish()`, `withdraw()`, set `last_hidden_at = time.monotonic()`.
  - `set_palette(self, palette: Palette) -> None` — recolor window and redraw current month in place.
  - `is_visible: bool` (property, `winfo_viewable()`), `last_hidden_at: float` (starts `0.0`).

Layout starting values (logical px, × `scale`): width 300; header band 44 (month name `"{calendar.month_name[m]} {y}"` at x=14; `<<` / `>>` as 30×28 rounded hover targets at the right, hover fill `bg2`); weekday row 24 (`Wk Mon Tue Wed Thu Fri Sat Sun`, muted); 6 week rows × 26; bottom padding 8 → height 232. 8 equal columns across `300 - 2*14`. Today: rounded rect (radius 10) in `accent`, text in `bg`. Fonts match today's customtkinter pixel sizes: header `("Arial", -round(16 * scale))`, everything else `("Arial", -round(12 * scale))` (negative = pixels in Tk). Only week rows + week numbers belong to a page (tag `f"page-{n}"`, increasing `n`); header and weekday row are static items.

- [ ] **Step 1: Implement drawing:** `_draw_page(self, year: int, month: int, x_offset: float) -> str` returns the new page tag; `_draw_static(self)` draws header and weekday row; rounded rectangles via `create_polygon(..., smooth=True)`.
- [ ] **Step 2: Implement navigation:** `<<`/`>>` click → `PageSlide.start(old_tag, new_tag, ±width, time.perf_counter())` after drawing the new page at `±width`, update header text immediately, then tick with `root.after(10, self._tick)` while `slide.step(time.perf_counter())` is True (only one tick chain alive: guard with an `_ticking` flag). `>>` = incoming from the right (`distance = +width`), `<<` from the left (`-width`).
- [ ] **Step 3: Implement `show` / `hide` / `set_palette`** per Interfaces; position = `(right - w - margin, bottom - h - margin)` from `primary_work_area()` with margin `12 * scale`; corners via `apply_rounded_corners(GetParent(winfo_id()), w, h, round(8 * scale))` — use `ctypes.windll.user32.GetParent`.
- [ ] **Step 4: Verify** `python -m pyflakes src/calendar_window.py && python -m py_compile src/calendar_window.py` — Expected: no output.
- [ ] **Step 5: Commit** `git commit -m "Add single-canvas calendar window with slide animation"`.

---

### Task 7: Tray, app wiring, entry point, cleanup

**Files:**
- Create: `src/tray.py`, `src/app.py`
- Modify: `src/main.py` (rewrite), `requirements.txt`, `compile.bat` (unchanged command, verify), `.gitignore` (unchanged)
- Delete: `src/Calendar.py`, `src/CalendarApp.py`, `src/utils.py`

**Interfaces:**
- Consumes: everything above.
- Produces:
  - `tray.Tray(on_open, on_set_theme: Callable[[str], None], on_toggle_autostart, on_quit, get_theme: Callable[[], str], get_autostart: Callable[[], bool])` — callbacks are invoked on the pystray thread; `start()` (`run_detached`), `stop()`, `set_week(week: int, light_taskbar: bool)` (sets icon image and tooltip `WeekTrayMA – Week {n}`), `refresh_menu()` (`update_menu`). Menu: `Open Calendar` (default, invisible), `Theme` submenu `Automatic`/`Light`/`Dark` (`radio=True`, `checked=lambda _: get_theme() == value`), `Start with Windows` (`checked=lambda _: get_autostart()`), separator, `Quit`.
  - `app.App` — `__init__(self)`; `run(self) -> None`. Every tray callback is wrapped as `lambda *a: root.after(0, handler)`. Open handler: if visible → hide; elif `time.monotonic() - last_hidden_at < 0.3` → do nothing; else show. Theme handler saves settings and calls `set_palette(resolve(...))`. Autostart handler calls `set_autostart(not is_autostart_enabled())` then `refresh_menu()`. Quit: `tray.stop()`, `root.destroy()`. Poll every 2000 ms: week (`date.today().isocalendar()[1]`) or taskbar theme changed → `tray.set_week`; apps theme changed and setting `"auto"` → `set_palette`.
  - `main.main()` — `enable_dpi_awareness()`; exit if not `acquire_single_instance()`; `App().run()`. Scale = `root.winfo_fpixels("1i") / 96` computed in `App`.

- [ ] **Step 1: Implement `src/tray.py`, `src/app.py`, rewrite `src/main.py`.**
- [ ] **Step 2: Delete old modules; set `requirements.txt` to `pillow==12.0.0` and `pystray==0.19.5`.**
- [ ] **Step 3: Verify** `python -m pyflakes src && python -m py_compile src/*.py && python -m pytest` — Expected: no pyflakes output, all tests pass. Also `grep -rn "customtkinter\|win32api\|import utils" src` — Expected: no matches.
- [ ] **Step 4: Commit** `git commit -m "Wire tray, settings and calendar in single-thread Tk app"`.

---

### Task 8: README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README:** requirements Python ≥ 3.10; Usage in order (create venv → `pip install -r requirements.txt` → `python src/main.py`); new "Settings" section (tray right-click: Theme Automatic/Light/Dark, Start with Windows; settings file path); new "Build" section (`pip install -r requirements-dev.txt`, `compile.bat`, output `dist\WeekTrayMA.exe`); "Development" line (`python -m pytest`).
- [ ] **Step 2: Commit** `git commit -m "Update README for rewrite"` and push the branch.

---

### Handoff to owner

After Task 8, the owner runs the spec's 10-point manual checklist on Windows; issues found go back as fix tasks.
