"""Core trading-calendar query logic."""

from __future__ import annotations

import bisect
from datetime import date
from functools import lru_cache

from tj_calendar.errors import CalendarRangeError
from tj_calendar.loader import load_market
from tj_calendar.types import DEFAULT_MARKET

DateInput = str | date | int


def _to_date(value: DateInput) -> date:
    """Normalize a date input (ISO str, date, or YYYYMMDD int) to date."""
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise CalendarRangeError(f"invalid date {value!r}") from None
    if isinstance(value, int):
        year, month, day = value // 10000, (value // 100) % 100, value % 100
        try:
            return date(year, month, day)
        except ValueError:
            raise CalendarRangeError(f"invalid date {value!r}") from None
    raise CalendarRangeError(f"unsupported date input {value!r}")


class TradingCalendar:
    """A market-bound trading calendar."""

    def __init__(self, market: str = DEFAULT_MARKET) -> None:
        self._calendar = load_market(market)
        self._dates = sorted(self._calendar.trade_dates)

    @classmethod
    def load(cls, market: str = DEFAULT_MARKET) -> TradingCalendar:
        return cls(market)

    @property
    def market(self) -> str:
        return self._calendar.market

    def _to_int(self, day: date) -> int:
        return day.year * 10000 + day.month * 100 + day.day

    def _check_range(self, day: date) -> None:
        start, end = self._calendar.coverage_start, self._calendar.coverage_end
        if day < start or day > end:
            raise CalendarRangeError(
                f"{day.isoformat()} is outside {self.market} calendar range {start.isoformat()} to {end.isoformat()}."
            )

    def is_trade_day(self, value: DateInput) -> bool:
        day = _to_date(value)
        self._check_range(day)
        return self._to_int(day) in self._calendar.trade_dates

    def next_trade_day(self, value: DateInput) -> date:
        day = _to_date(value)
        self._check_range(day)
        int_day = self._to_int(day)
        idx = bisect.bisect_right(self._dates, int_day)
        if idx >= len(self._dates):
            raise CalendarRangeError(f"no trade day after {day.isoformat()} in {self.market} coverage.")
        return self._from_int(self._dates[idx])

    def prev_trade_day(self, value: DateInput) -> date:
        day = _to_date(value)
        self._check_range(day)
        int_day = self._to_int(day)
        idx = bisect.bisect_left(self._dates, int_day) - 1
        if idx < 0:
            raise CalendarRangeError(f"no trade day before {day.isoformat()} in {self.market} coverage.")
        return self._from_int(self._dates[idx])

    def trade_days_between(self, start: DateInput, end: DateInput) -> list[date]:
        start_day, end_day = _to_date(start), _to_date(end)
        self._check_range(start_day)
        self._check_range(end_day)
        if start_day > end_day:
            raise CalendarRangeError(f"start {start_day.isoformat()} is after end {end_day.isoformat()}.")
        lo = bisect.bisect_left(self._dates, self._to_int(start_day))
        hi = bisect.bisect_right(self._dates, self._to_int(end_day))
        return [self._from_int(d) for d in self._dates[lo:hi]]

    def info(self) -> dict:
        return {
            "market": self.market,
            "coverage_start": self._calendar.coverage_start.isoformat(),
            "coverage_end": self._calendar.coverage_end.isoformat(),
            "trade_day_count": len(self._dates),
        }

    def _from_int(self, value: int) -> date:
        return date(value // 10000, (value // 100) % 100, value % 100)


@lru_cache(maxsize=16)
def _get_calendar(market: str) -> TradingCalendar:
    return TradingCalendar.load(market)


def is_trade_day(value: DateInput, market: str = DEFAULT_MARKET) -> bool:
    return _get_calendar(market).is_trade_day(value)


def next_trade_day(value: DateInput, market: str = DEFAULT_MARKET) -> date:
    return _get_calendar(market).next_trade_day(value)


def prev_trade_day(value: DateInput, market: str = DEFAULT_MARKET) -> date:
    return _get_calendar(market).prev_trade_day(value)


def trade_days_between(start: DateInput, end: DateInput, market: str = DEFAULT_MARKET) -> list[date]:
    return _get_calendar(market).trade_days_between(start, end)


def get_calendar_info(market: str = DEFAULT_MARKET) -> dict:
    return _get_calendar(market).info()
