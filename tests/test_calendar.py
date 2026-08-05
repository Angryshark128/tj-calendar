"""Test suite for tj-calendar."""

from datetime import date

import pytest

from tj_calendar import (
    CalendarRangeError,
    __version__,
    get_calendar_info,
    is_trade_day,
    next_trade_day,
    prev_trade_day,
    trade_days_between,
)
from tj_calendar.calendar import TradingCalendar


def test_version() -> None:
    assert __version__ == "0.1.0"


# --- Known A-share holidays (should NOT be trade days) ---
@pytest.mark.parametrize(
    "day",
    [
        "2020-01-01",  # New Year
        "2020-01-24",  # Spring Festival eve closure
        "2020-01-31",  # COVID extended Spring Festival closure
        "2021-02-12",  # Spring Festival
        "2022-10-01",  # National Day
        "2024-02-10",  # Spring Festival 2024
        "2025-05-01",  # Labour Day
        "2025-10-01",  # National Day
    ],
)
def test_known_holidays_are_not_trade_days(day: str) -> None:
    assert is_trade_day(day) is False


@pytest.mark.parametrize(
    "day",
    [
        "2020-02-03",  # first trading day after COVID extension
        "2024-01-02",  # Tuesday
        "2024-06-03",  # Monday
        "2025-07-01",  # Tuesday
        "2026-08-04",  # Tuesday
    ],
)
def test_regular_weekdays_are_trade_days(day: str) -> None:
    assert is_trade_day(day) is True


def test_weekend_is_not_trade_day() -> None:
    assert is_trade_day("2026-08-08") is False  # Saturday
    assert is_trade_day("2026-08-09") is False  # Sunday


# --- Date input forms ---
def test_date_input_forms() -> None:
    assert is_trade_day("2024-01-02") is True
    assert is_trade_day(date(2024, 1, 2)) is True
    assert is_trade_day(20240102) is True


# --- Range errors ---
def test_out_of_range_raises() -> None:
    with pytest.raises(CalendarRangeError):
        is_trade_day("2036-01-05")
    with pytest.raises(CalendarRangeError):
        is_trade_day("1989-12-31")  # before coverage start (1990-12-19)


def test_before_market_exists_raises() -> None:
    with pytest.raises(CalendarRangeError):
        is_trade_day("2018-01-02", market="BSE")


def test_bse_start_is_covered() -> None:
    assert is_trade_day("2021-11-15", market="BSE") is True


# --- next / prev ---
def test_next_trade_day() -> None:
    assert next_trade_day("2026-08-04") == date(2026, 8, 5)
    # Friday -> Monday
    assert next_trade_day("2026-08-07") == date(2026, 8, 10)


def test_prev_trade_day() -> None:
    assert prev_trade_day("2026-08-04") == date(2026, 8, 3)
    # Monday -> Friday
    assert prev_trade_day("2026-08-10") == date(2026, 8, 7)


def test_next_skips_holiday() -> None:
    # 2025-10-01 is National Day; the next trade day should be after Oct 8
    assert next_trade_day("2025-09-30") == date(2025, 10, 9)


# --- range ---
def test_trade_days_between() -> None:
    days = trade_days_between("2026-08-03", "2026-08-07")
    assert days == [date(2026, 8, 3), date(2026, 8, 4), date(2026, 8, 5), date(2026, 8, 6), date(2026, 8, 7)]


def test_trade_days_between_reversed_raises() -> None:
    with pytest.raises(CalendarRangeError):
        trade_days_between("2026-08-07", "2026-08-03")


def test_trade_days_between_includes_endpoints() -> None:
    days = trade_days_between("2026-08-04", "2026-08-04")
    assert days == [date(2026, 8, 4)]


# --- info ---
def test_get_calendar_info() -> None:
    info = get_calendar_info()
    assert info["market"] == "CN_A_SHARE"
    assert info["coverage_start"] == "1990-12-19"
    assert info["coverage_end"] == "2035-12-31"
    assert info["trade_day_count"] > 0


def test_bse_info_start() -> None:
    info = get_calendar_info(market="BSE")
    assert info["coverage_start"] == "2021-11-15"


# --- object interface ---
def test_trading_calendar_object() -> None:
    cal = TradingCalendar.load("CN_A_SHARE")
    assert cal.is_trade_day("2026-08-04") is True
    assert cal.next_trade_day("2026-08-04") == date(2026, 8, 5)
    assert cal.prev_trade_day("2026-08-04") == date(2026, 8, 3)
