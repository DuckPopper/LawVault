"""Calendar rendering: overlap layout, escaping of user text, month grid shape."""
import datetime as dt
from views import calendar_grid as grid

DAY = dt.date(2026, 11, 19)


def _ev(h0, h1, title="x", kind="event"):
    base = dt.datetime.combine(DAY, dt.time(0)).timestamp()
    return dict(start=base + h0 * 3600, end=base + h1 * 3600, title=title, kind=kind)


def test_overlapping_events_share_the_column():
    placed = grid.layout_day([_ev(10, 11, "A"), _ev(10.5, 12, "B"), _ev(13, 14, "C")], DAY)
    cols = {e["title"]: (c, n) for e, _, _, c, n in placed}
    assert cols["A"] == (0, 2) and cols["B"] == (1, 2)
    assert cols["C"] == (0, 1)  # not overlapping -> full width


def test_free_column_is_reused():
    placed = grid.layout_day([_ev(9, 12, "long"), _ev(9, 10, "a"), _ev(10.5, 11, "b")], DAY)
    cols = {e["title"]: (c, n) for e, _, _, c, n in placed}
    assert cols["a"][0] == cols["b"][0] == 1 and cols["long"] == (0, 2)


def test_event_titles_are_html_escaped():
    html = grid.time_grid([DAY], [_ev(10, 11, '<img src=x onerror=alert(1)>')], now=0)
    assert "<img" not in html and "&lt;img" in html
    html = grid.month_grid(2026, 11, [_ev(10, 11, "<script>")], today=DAY)
    assert "<script>" not in html


def test_hour_range_grows_for_early_and_late_events():
    assert grid.hour_range([_ev(10, 11)], [DAY]) == grid.DEFAULT_HOURS
    assert grid.hour_range([_ev(5.5, 6), _ev(22, 23.5)], [DAY]) == (5, 24)


def test_month_grid_is_six_monday_first_weeks():
    days = grid.month_days(2026, 11)
    assert len(days) == 42 and days[0].weekday() == 0 and days[0] <= dt.date(2026, 11, 1)
    assert dt.date(2026, 11, 30) in days
