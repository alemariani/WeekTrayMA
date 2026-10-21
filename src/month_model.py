from dataclasses import dataclass
from datetime import date, timedelta

WEEKS_PER_GRID = 6


@dataclass(frozen=True)
class Day:
    date: date
    in_month: bool
    is_today: bool


@dataclass(frozen=True)
class Week:
    number: int
    days: tuple[Day, ...]


def month_grid(year, month, today):
    '''
    Return 6 Monday-first weeks covering the given month.
    The grid starts at the Monday on or before the 1st of the month.
    '''
    first = date(year, month, 1)
    start = first - timedelta(days=first.weekday())
    weeks = []
    for w in range(WEEKS_PER_GRID):
        monday = start + timedelta(weeks=w)
        days = tuple(
            Day(d, d.month == month, d == today)
            for d in (monday + timedelta(days=i) for i in range(7))
        )
        weeks.append(Week(monday.isocalendar()[1], days))
    return weeks


def shift_month(year, month, delta):
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def needs_redraw(shown, drawn_today, today):
    return shown != (today.year, today.month) or drawn_today != today
