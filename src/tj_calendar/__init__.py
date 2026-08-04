"""Tianji Calendar — offline-first China market trading calendar."""

from tj_calendar.calendar import (
    get_calendar_info,
    is_trade_day,
    next_trade_day,
    prev_trade_day,
    trade_days_between,
)
from tj_calendar.errors import (
    CalendarDataError,
    CalendarRangeError,
    CalendarUpdateError,
    TianjiCalendarError,
)
from tj_calendar.update import check_for_update, ensure_fresh, update_calendar

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "is_trade_day",
    "next_trade_day",
    "prev_trade_day",
    "trade_days_between",
    "get_calendar_info",
    "check_for_update",
    "update_calendar",
    "ensure_fresh",
    "TianjiCalendarError",
    "CalendarRangeError",
    "CalendarDataError",
    "CalendarUpdateError",
]
