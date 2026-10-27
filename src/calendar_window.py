import calendar
import time
import tkinter as tk
from datetime import date

import winapi
from animation import PageSlide
from month_model import month_grid, shift_month, needs_redraw

# layout sizes in logical pixels, multiplied by the DPI scale at runtime
WIDTH = 300
SIDE_PADDING = 14
HEADER_HEIGHT = 44
WEEKDAY_ROW_HEIGHT = 24
WEEK_ROW_HEIGHT = 26
BOTTOM_PADDING = 8
SCREEN_MARGIN = 5
WINDOW_CORNER_RADIUS = 8
TODAY_CORNER_RADIUS = 10
NAV_BUTTON_WIDTH = 30
NAV_BUTTON_HEIGHT = 28
NAV_BUTTON_GAP = 8
NAV_CORNER_RADIUS = 6
TITLE_FONT_SIZE = 16
BODY_FONT_SIZE = 12

TICK_MS = 10
COLUMN_HEADERS = ("Wk", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


class CalendarWindow:
    '''
    Borderless month calendar drawn on a single canvas.
    It is built once and then only shown/hidden, so opening it is instant.
    The week rows of a month form a "page" (canvas items sharing a tag);
    changing month slides the old page out and the new one in.
    '''

    def __init__(self, root, palette, scale):
        self.root = root
        self.palette = palette
        self.scale = scale
        self.last_hidden_at = 0.0

        self.width = self._px(WIDTH)
        self.height = self._px(HEADER_HEIGHT + WEEKDAY_ROW_HEIGHT + 6 * WEEK_ROW_HEIGHT + BOTTOM_PADDING)
        self.grid_top = self._px(HEADER_HEIGHT + WEEKDAY_ROW_HEIGHT)
        self.column_width = (self.width - 2 * self._px(SIDE_PADDING)) / len(COLUMN_HEADERS)
        self.title_font = ("Arial", -self._px(TITLE_FONT_SIZE))
        self.body_font = ("Arial", -self._px(BODY_FONT_SIZE))

        root.overrideredirect(True)
        root.attributes("-topmost", True)
        self.canvas = tk.Canvas(root, width=self.width, height=self.height, highlightthickness=0, bd=0)
        self.canvas.pack()

        self.slide = PageSlide(lambda tag, dx: self.canvas.move(tag, dx, 0), self.canvas.delete)
        self._ticking = False
        self._page_count = 0

        today = date.today()
        self.year, self.month = today.year, today.month
        self.drawn_today = today
        self._redraw()

        root.bind("<FocusOut>", self._on_focus_out)
        root.withdraw()

    @property
    def is_visible(self):
        return bool(self.root.winfo_viewable())

    def show(self):
        today = date.today()
        if needs_redraw((self.year, self.month), self.drawn_today, today):
            self.year, self.month = today.year, today.month
            self._redraw()
        self._place()
        # Tk paints a window only once it is mapped: map it fully transparent,
        # let it paint and get its rounded corners, then make it opaque,
        # so it never appears half drawn
        self.root.attributes("-alpha", 0.0)
        self.root.deiconify()
        self.root.update()
        winapi.apply_rounded_corners(winapi.toplevel_hwnd(self.root.winfo_id()),
                                     self.width, self.height, self._px(WINDOW_CORNER_RADIUS))
        self.root.attributes("-alpha", 1.0)
        self.root.focus_force()

    def hide(self):
        self.slide.finish()
        self.root.withdraw()
        self.last_hidden_at = time.monotonic()

    def set_palette(self, palette):
        self.palette = palette
        self._redraw()

    def _px(self, value):
        return round(value * self.scale)

    def _on_focus_out(self, event):
        if event.widget is self.root and self.is_visible:
            self.hide()

    def _place(self):
        _, _, right, bottom = winapi.primary_work_area()
        margin = self._px(SCREEN_MARGIN)
        x = right - self.width - margin
        y = bottom - self.height - margin
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")

    def _redraw(self):
        self.slide.finish()
        self.canvas.delete("all")
        self.root.configure(bg=self.palette.bg)
        self.canvas.configure(bg=self.palette.bg)
        self._draw_static()
        self.page = self._draw_page(self.year, self.month, 0)

    def _column_center(self, column):
        return self._px(SIDE_PADDING) + self.column_width * (column + 0.5)

    def _rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        # corner points are doubled so smoothing only rounds the corners
        r = radius
        points = [x1 + r, y1, x1 + r, y1, x2 - r, y1, x2 - r, y1, x2, y1,
                  x2, y1 + r, x2, y1 + r, x2, y2 - r, x2, y2 - r, x2, y2,
                  x2 - r, y2, x2 - r, y2, x1 + r, y2, x1 + r, y2, x1, y2,
                  x1, y2 - r, x1, y2 - r, x1, y1 + r, x1, y1 + r, x1, y1]
        return self.canvas.create_polygon(points, smooth=True, **kwargs)

    def _draw_static(self):
        p = self.palette
        header_middle = self._px(HEADER_HEIGHT) / 2
        self.title_item = self.canvas.create_text(
            self._px(SIDE_PADDING), header_middle, anchor="w",
            font=self.title_font, fill=p.text, text=self._title())

        button_width = self._px(NAV_BUTTON_WIDTH)
        next_right = self.width - self._px(SIDE_PADDING)
        prev_right = next_right - button_width - self._px(NAV_BUTTON_GAP)
        self._draw_nav_button("nav-prev", "<<", prev_right, header_middle, -1)
        self._draw_nav_button("nav-next", ">>", next_right, header_middle, +1)

        weekday_middle = self._px(HEADER_HEIGHT) + self._px(WEEKDAY_ROW_HEIGHT) / 2
        for column, header in enumerate(COLUMN_HEADERS):
            self.canvas.create_text(self._column_center(column), weekday_middle,
                                    font=self.body_font, fill=p.muted, text=header)

    def _draw_nav_button(self, tag, label, right, middle, delta):
        half_height = self._px(NAV_BUTTON_HEIGHT) / 2
        left = right - self._px(NAV_BUTTON_WIDTH)
        background = self._rounded_rect(left, middle - half_height, right, middle + half_height,
                                        self._px(NAV_CORNER_RADIUS), fill=self.palette.bg, tags=(tag,))
        self.canvas.create_text((left + right) / 2, middle, font=self.body_font,
                                fill=self.palette.text, text=label, tags=(tag,))
        self.canvas.tag_bind(tag, "<Enter>", lambda e: self.canvas.itemconfigure(background, fill=self.palette.bg2))
        self.canvas.tag_bind(tag, "<Leave>", lambda e: self.canvas.itemconfigure(background, fill=self.palette.bg))
        self.canvas.tag_bind(tag, "<Button-1>", lambda e: self._navigate(delta))

    def _title(self):
        return f"{calendar.month_name[self.month]} {self.year}"

    def _draw_page(self, year, month, x_offset):
        p = self.palette
        self._page_count += 1
        tag = f"page-{self._page_count}"
        self.drawn_today = date.today()

        row_height = self._px(WEEK_ROW_HEIGHT)
        highlight_half_width = self.column_width / 2 - self._px(2)
        highlight_half_height = row_height / 2 - self._px(2)
        highlight_radius = min(self._px(TODAY_CORNER_RADIUS), highlight_half_height)

        for row, week in enumerate(month_grid(year, month, self.drawn_today)):
            y = self.grid_top + row_height * (row + 0.5)
            self.canvas.create_text(self._column_center(0) + x_offset, y, font=self.body_font,
                                    fill=p.muted, text=str(week.number), tags=(tag,))
            for column, day in enumerate(week.days, start=1):
                x = self._column_center(column) + x_offset
                if day.is_today:
                    self._rounded_rect(x - highlight_half_width, y - highlight_half_height,
                                       x + highlight_half_width, y + highlight_half_height,
                                       highlight_radius, fill=p.accent, tags=(tag,))
                    color = p.bg
                else:
                    color = p.text if day.in_month else p.muted
                self.canvas.create_text(x, y, font=self.body_font, fill=color,
                                        text=str(day.date.day), tags=(tag,))
        return tag

    def _navigate(self, delta):
        self.year, self.month = shift_month(self.year, self.month, delta)
        self.canvas.itemconfigure(self.title_item, text=self._title())
        # next month comes in from the right, previous month from the left
        distance = self.width * delta
        outgoing = self.page
        self.page = self._draw_page(self.year, self.month, distance)
        self.slide.start(outgoing, self.page, distance, time.perf_counter())
        if not self._ticking:
            self._ticking = True
            self._tick()

    def _tick(self):
        if self.slide.step(time.perf_counter()):
            self.root.after(TICK_MS, self._tick)
        else:
            self._ticking = False
