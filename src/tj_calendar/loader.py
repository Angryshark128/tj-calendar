"""Loading and validation of calendar bundles.

Priority: user-local data (~/.tianji/calendar/calendar-bundle.json) first,
falling back to the bundled data file inside the package.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any

from tj_calendar.errors import CalendarDataError
from tj_calendar.types import MarketCalendar, _check_market, _parse_date

BUNDLED_PATH = Path(__file__).parent / "data" / "calendar-bundle.json"


def config_dir() -> Path:
    """Return the Tianji config dir, honoring TIANJI_HOME if set."""
    override = Path(__import__("os").environ.get("TIANJI_HOME", ""))
    return override if str(override) else Path.home() / ".tianji"


def local_bundle_path() -> Path:
    return config_dir() / "calendar" / "calendar-bundle.json"


def local_metadata_path() -> Path:
    return config_dir() / "calendar" / "metadata.json"


def read_calendar_version(bundle: dict[str, Any]) -> str | None:
    """Return the calendar_version from a parsed bundle, if present."""
    version = bundle.get("calendar_version")
    return version if isinstance(version, str) and version else None


def parse_bundle(data: Any) -> dict[str, MarketCalendar]:
    """Validate a calendar bundle into per-market MarketCalendar objects."""
    if not isinstance(data, dict):
        raise CalendarDataError("calendar bundle must be a JSON object")

    markets = data.get("markets")
    if not isinstance(markets, dict):
        raise CalendarDataError("calendar bundle missing 'markets' object")

    bundle_id = data.get("bundle_id")
    if not isinstance(bundle_id, str) or not bundle_id:
        raise CalendarDataError("calendar bundle missing valid 'bundle_id'")

    result: dict[str, MarketCalendar] = {}
    for market, spec in markets.items():
        _check_market(market)
        if not isinstance(spec, dict):
            raise CalendarDataError(f"market {market!r} must be an object")

        coverage_start = _parse_date(spec.get("coverage_start"), "coverage_start")
        coverage_end = _parse_date(spec.get("coverage_end"), "coverage_end")
        years = spec.get("years")
        if not isinstance(years, dict):
            raise CalendarDataError(f"market {market!r} missing valid 'years'")

        dates: set[int] = set()
        for year, day_list in years.items():
            if not isinstance(day_list, list):
                raise CalendarDataError(f"market {market!r} year {year!r} is not a list")
            for d in day_list:
                if not isinstance(d, int):
                    raise CalendarDataError(f"invalid trade date {d!r} in market {market!r}")
                dates.add(d)

        if not dates:
            raise CalendarDataError(f"market {market!r} has no trade dates")

        result[market] = MarketCalendar(
            market=market,
            coverage_start=coverage_start,
            coverage_end=coverage_end,
            trade_dates=frozenset(dates),
        )

    if not result:
        raise CalendarDataError("calendar bundle contains no markets")
    return result


def load_bundle() -> tuple[dict[str, MarketCalendar], str]:
    """Load the best available bundle. Returns (markets, source_label).

    Local data wins when it parses cleanly; a corrupt local file falls back
    to bundled data with a warning.
    """
    local = local_bundle_path()
    if local.is_file():
        try:
            with local.open("r", encoding="utf-8") as f:
                data = json.load(f)
            markets = parse_bundle(data)
            return markets, str(local)
        except (OSError, json.JSONDecodeError, CalendarDataError) as exc:
            warnings.warn(
                f"local calendar data is invalid ({exc}); falling back to bundled data",
                stacklevel=2,
            )

    with BUNDLED_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    markets = parse_bundle(data)
    return markets, "bundled"


def load_market(market: str) -> MarketCalendar:
    """Load a single market's calendar, or raise for unknown markets."""
    markets, _ = load_bundle()
    return markets[market]
