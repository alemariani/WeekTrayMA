# WeekTrayMA – Lightweight Tk rewrite

Status: draft, awaiting approval
Date: 2026-10-21

## Intent

WeekTrayMA shows the ISO week number in the Windows tray and opens a small
month calendar on click. It works, but using it feels rough:

1. Opening the calendar draws the UI in two visible steps.
2. The month-change animation stutters at its start.
3. Changing month quickly leaves temporary visual artifacts.
4. There are no user settings: the theme can't be forced, and the app can't
   start with Windows.

The owner wants to keep Python, and wants the app to stay **light and fast**:
small executable, low memory, instant to open. The rewrite fixes the four
points above, adds rounded window corners, and simplifies the internals so
these problems don't come back.

## Goals

- **Instant, single-step open.** Clicking the tray icon shows the calendar
  already fully drawn. No partial frame is ever visible.
- **Smooth month animation.** The slide starts moving on the first frame,
  with time-based easing. No initial jerk.
- **No artifacts on rapid clicks.** Any click sequence on `<<` / `>>` leaves
  exactly one month visible when motion stops, and never shows overlapping or
  orphan frames during motion.
- **Theme setting:** Automatic (follows Windows app theme) / Light / Dark,
  chosen from the tray menu, persisted across restarts.
- **Start with Windows** setting, toggled from the tray menu.
- **Rounded window corners.**
- **Fewer, lighter dependencies** than today.

## Non-goals

- Switching UI toolkit (Qt, .NET, web). Discussed and rejected: heavier.
- Localization, first-day-of-week setting, a settings window, or any feature
  not listed in Goals.
- Multi-monitor placement beyond today's behavior (bottom-right of the
  primary monitor's work area).

## Anti-goals (it fails even if it "works")

- The app becomes heavier: more dependencies, bigger exe, slower open.
- The tray number becomes harder to read than today in either taskbar theme.
- The calendar looks noticeably worse than the current screenshots.

## Constraints

- Python ≥ 3.10 (Pillow 12 requirement), Windows 10 and 11.
- Standard python.org Windows build: tkinter with **threaded Tcl**, which
  makes Tk calls from other threads safe (they are marshaled to the Tk
  thread while `mainloop` runs).
- Packaged as a single exe with PyInstaller (`compile.bat`).
- Development happens in a Linux container without tkinter and without
  Windows: only pure-Python logic can be tested automatically. Everything
  GUI/Windows-specific is verified manually by the owner on Windows.
- Code, comments and identifiers in English.

## Decisions taken with the owner

- Stay on Python + tkinter.
- Light/fast over everything else.
- Theme options: Automatic / Light / Dark.
- Start with Windows option.
- Rounded window corners.

## Design

### Stack and dependencies

| Today | After | Why |
|---|---|---|
| customtkinter (+ darkdetect, packaging) | plain `tkinter` | one `Canvas` replaces all widgets; lighter and faster |
| pywin32 | `ctypes` + `winreg` (stdlib) | only a handful of Win32 calls are needed |
| pystray | pystray (kept) | small, ctypes-based, already handles Explorer restarts (`TaskbarCreated`) and radio/check menu items |
| Pillow | Pillow (kept) | draws the tray icon |

`requirements.txt` becomes `pillow` and `pystray` (pinned). A
`requirements-dev.txt` adds `pytest` and `pyinstaller`.

### Threading model

- **Tk runs in the main thread** and owns all UI state.
- pystray runs its own Win32 message loop via `icon.run_detached()` (it
  starts its own non-daemon thread).
- pystray callbacks (clicks, menu items) never touch app state directly:
  they only call `root.after(0, handler)`, which runs `handler` on the Tk
  thread.
- Quit: Tk thread calls `icon.stop()` then `root.destroy()`; the process
  exits when both loops end.
- This removes today's startup race (`icon.app` used before it exists) and
  the separate updater thread.

### Module layout (`src/`)

Lowercase module names (today `Calendar.py` differs from stdlib `calendar`
only by case).

- `main.py` – entry point: single-instance check, DPI awareness, builds and
  runs `App`.
- `app.py` – `App`: owns the Tk root, settings, tray, calendar window;
  periodic system check; wires callbacks.
- `calendar_window.py` – borderless popup window with one `tk.Canvas`
  drawing header, weekday row, week numbers, days, and the slide animation.
- `month_model.py` – **pure** logic, no tkinter import: month grid, week
  numbers, month arithmetic.
- `tray.py` – pystray wrapper: icon rendering, menu definition.
- `settings.py` – **pure** load/save of settings JSON.
- `theme.py` – **pure** palettes and theme resolution.
- `winapi.py` – Windows helpers (ctypes/winreg): registry theme reads, work
  area, DPI awareness, rounded corners, autostart registry, single-instance
  mutex.

`tests/` – pytest for the pure modules. (Note: `.gitignore` currently
ignores `test`; `tests/` is unaffected.)

### Month model

- `month_grid(year, month, today) -> list[Week]`, always **6 weeks**,
  Monday-first, starting from the Monday on or before the 1st.
- `Week`: ISO week number (from its Monday) and 7 `Day`s.
- `Day`: `date`, `in_month: bool`, `is_today: bool`.
- `shift_month(year, month, delta) -> (year, month)`.

Always 6 rows keeps the window height constant across months (today 5-week
and 6-week months need different heights, and a 6-week month may not fit
the fixed 300×200 window).

### Calendar window

- One `tk.Toplevel` (the hidden root can be the window itself or a parent;
  builder's choice), `overrideredirect(True)`, `-topmost`.
- **Built once at startup**, drawn while withdrawn, then only shown/hidden.
- Layout drawn on a single `Canvas`, in this order top to bottom: header
  (month + year on the left, `<<` `>>` on the right), weekday row
  (`Wk Mon … Sun`), 6 week rows. Week-number column on the left, muted.
  Today = filled rounded rectangle in accent color with background-colored
  text. Days outside the month muted. Same palette, fonts and proportions as
  the current screenshots, except "Wee" becomes "Wk".
- `<<` / `>>` are canvas items with hover background (bg2 color) and click
  bindings.
- **Open:** if the visible month isn't the current month, or "today" changed
  since the last draw, redraw without animation. Then compute position,
  `update_idletasks()`, `deiconify()`, `focus_force()`. Acceptance: no
  partially drawn frame is ever visible.
- **Hide:** on `<FocusOut>` or `<Escape>`.
- **Tray click while open closes it.** The focus-out caused by clicking the
  tray hides the window first; the click then arrives. Record the hide time;
  a tray click within ~300 ms after a focus-out hide is ignored.
- **Position:** bottom-right of the primary monitor work area
  (`SystemParametersInfoW(SPI_GETWORKAREA)`), with a 5 px (logical, scaled)
  margin from the right and bottom edges (owner request). Recomputed on
  every open.

### Slide animation

- The grid area (weekday row is static; only week rows + week numbers slide)
  is drawn as a **page**: a set of canvas items sharing a tag.
- On `<<`/`>>`: draw the incoming page off-screen (left or right of the
  visible area), update the header text immediately, then move both pages
  with `canvas.move(tag, dx, 0)` driven by `after(...)` ticks.
- Time-based: position computed from elapsed time (`time.perf_counter()`),
  ease-out cubic, total duration 350 ms (slowed down from 180 ms at the
  owner's request). The first tick happens immediately after the page is
  drawn.
- **Interruption:** a click during an animation finishes it instantly
  (outgoing page deleted, incoming page snapped to place) and starts the next
  one from that clean state. At most two pages exist at any time.
- Pages must never be visible over the header: they only move horizontally
  within the grid band; anything outside the canvas is clipped by the
  canvas.

### Rounded corners

- Windows 11: `DwmSetWindowAttribute(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE=33,
  DWMWCP_ROUND=2)` on the window's top-level HWND
  (`GetParent(winfo_id())`). Gives antialiased native corners.
- Windows 10 (DWM call fails or has no effect): `SetWindowRgn` with
  `CreateRoundRectRgn`, radius 8 px logical. Edges are not antialiased; this
  is accepted.
- Applied after the window is first mapped and re-applied if geometry
  changes (region must match the size).

### DPI

- `main.py` calls `SetProcessDpiAwareness(1)` (system-aware) before creating
  Tk, falling back to `SetProcessDPIAware()`.
- Scale factor = `root.winfo_fpixels('1i') / 96`, computed at startup. All
  pixel sizes (window, paddings, radii, margins) are logical values × scale.
  Fonts are specified in points so Tk scales them itself.
- A DPI change while running is picked up on next app start (accepted).

### Theme

- `theme.py` holds the two palettes from today's code:
  - light: bg `#f9ecec`, bg2 `#edc5c5`, accent `#E85F5C`, text `#020222`,
    muted `#73738c`
  - dark: bg `#232234`, bg2 `#3e3c5d`, accent `#00fefe`, text `#EEEEFF`,
    muted `#686868`
- `resolve(setting, apps_light: bool) -> palette`: Automatic uses
  `HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize\AppsUseLightTheme`.
- The **tray icon color** always follows the taskbar
  (`SystemUsesLightTheme`): black digits on a light taskbar, white on dark,
  independent of the calendar theme setting.
- Changing theme from the menu redraws the calendar immediately.

### Periodic system check

A Tk `after` timer every 2 s reads the two registry values and today's
date. If the week or the taskbar theme changed → update tray icon. If the
apps theme changed and setting is Automatic → redraw calendar. Cost is two
registry reads; no thread. (Event-based `WM_SETTINGCHANGE` handling was
considered and rejected: it needs subclassing a window procedure for little
gain.)

### Tray icon

- Rendered with Pillow at 64×64 RGBA, transparent background, exactly as
  the original app: `arial.ttf` at a constant 60 px, centered with
  `anchor="mm"`, same digit size for every week (owner-tested and approved;
  two-digit numbers may touch the edges). Fallback font:
  `ImageFont.load_default(size=60)`.
- Tooltip: `WeekTrayMA – Week {n}` (fixes today's "WeekTrayAM").
- Menu:
  - `Open Calendar` (default, invisible; triggered by left click)
  - `Theme` ▸ `Automatic` / `Light` / `Dark` (radio)
  - `Start with Windows` (check)
  - separator
  - `Quit`
- Menu checked states read live values via pystray `checked=` callables.
  pystray rebuilds the menu itself right after a menu callback returns, so
  the theme and autostart callbacks update that state synchronously on the
  pystray thread (attribute assignment / registry write); only saving the
  settings file and redrawing are forwarded to the Tk thread. The app never
  calls `update_menu()` itself.

### Settings

- File: `%APPDATA%\WeekTrayMA\settings.json`, e.g. `{"theme": "auto"}`.
  Without `APPDATA`: `<home>\AppData\Roaming\WeekTrayMA\settings.json`;
  without a home directory either: `WeekTrayMA\settings.json` next to the
  program.
- Missing/corrupt file or unknown values → defaults (`theme: "auto"`),
  never a crash. Written atomically (temp file + `os.replace`).
- **Autostart is not stored in JSON**: the registry is the source of truth.
  `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` (created if missing),
  value `WeekTrayMA`:
  - frozen exe: `"<sys.executable>"`
  - from source: `"<pythonw.exe next to sys.executable>" "<abs path of main.py>"`
- The menu check reflects whether the value exists. If the exe moved, the
  check still shows enabled; toggling off and on rewrites the path
  (accepted).

### Single instance

Named mutex `Local\WeekTrayMA` via `CreateMutexW`; if it already exists,
exit silently. Prevents two icons when autostart is on and the user also
launches the exe manually.

### Packaging

`compile.bat`: same PyInstaller one-file, windowed build, icon unchanged.
`.gitignore` unchanged.

### README

Fix the Usage steps order (venv → install → run), state Python ≥ 3.10, add
a "Build" section (`pip install -r requirements-dev.txt`, `compile.bat`),
document the tray menu settings.

## Testing

Automated (pytest, Linux, no tkinter):
- `month_grid`: 6 weeks always; correct ISO week numbers including year
  boundaries (e.g. Dec 2026 / Jan 2027, years with week 53 like 2026);
  `in_month` / `is_today` flags.
- `shift_month` across year boundaries.
- `settings`: defaults on missing/corrupt file, round-trip, unknown theme
  value falls back.
- `theme.resolve` for all setting × system combinations.
- Tray icon font fitting: "53" and "88" fit within 64×64 (Pillow available).

Manual checklist on Windows (owner):
1. Open/close from tray repeatedly: no two-step drawing; clicking the icon
   while open closes it.
2. `<<` / `>>` single clicks: smooth from first frame.
3. Rapid clicking / holding: no overlapping months or leftovers.
4. Theme menu: each option applies immediately and survives restart;
   Automatic follows Windows app theme changes within ~2 s.
5. Taskbar light/dark switch: tray digits stay readable.
6. Start with Windows: toggle on → reboot/sign-in → icon present; toggle off
   → not started.
7. Rounded corners on Windows 11 (and Windows 10 if available).
8. 125 %/150 % display scaling: crisp, correctly sized, correct position.
9. Second launch while running: no second icon.
10. Restart Explorer: tray icon reappears.

## Left to the builder

- Exact canvas coordinates and paddings (match the current look).
- Whether the Tk root is the calendar window or a hidden parent.
- Tick interval for animation (`after(8)`–`after(16)`).
- Internal APIs between modules.

## Risks

- **DWM corners on a borderless (`overrideredirect`) window** on Windows 11
  are expected to work but can't be verified here. Fallback: `SetWindowRgn`
  on all versions.
- **No Windows/tkinter in the dev environment**: GUI code is written blind
  and verified only through the manual checklist; expect one round of fixes
  after the owner's first test.
