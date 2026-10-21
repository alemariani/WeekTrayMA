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
