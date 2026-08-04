"""Exceptions for tj-calendar."""

from __future__ import annotations


class TianjiCalendarError(Exception):
    """Base error for tj-calendar."""


class CalendarRangeError(TianjiCalendarError):
    """Raised when a date is outside the market's coverage range."""


class CalendarDataError(TianjiCalendarError):
    """Raised when a calendar bundle is malformed, corrupt, or fails validation."""


class CalendarUpdateError(TianjiCalendarError):
    """Raised when importing or updating calendar data fails."""
