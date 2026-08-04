"""Type hints and shared constants for tj-calendar."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from tj_calendar.errors import CalendarDataError

DEFAULT_MARKET = "CN_A_SHARE"

SUPPORTED_MARKETS = ("CN_A_SHARE", "SSE", "SZSE", "BSE")


@dataclass(frozen=True)
class MarketCalendar:
    """Trading days and coverage for a single market."""

    market: str
    coverage_start: date
    coverage_end: date
    trade_dates: frozenset[int]


def _check_market(market: str) -> None:
    if market not in SUPPORTED_MARKETS:
        raise ValueError(f"unknown market {market!r}; supported: {', '.join(SUPPORTED_MARKETS)}")


def _parse_date(value: object, field: str) -> date:
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise CalendarDataError(f"invalid {field} {value!r}") from None
    raise CalendarDataError(f"invalid {field} {value!r}")
