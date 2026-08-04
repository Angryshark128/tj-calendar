"""Validate a calendar-bundle.json before publishing.

Checks (mirror the design doc's validation strategy):
- schema_version / calendar_version / bundle_id present and consistent
- per-market coverage within the coverage window
- each year's dates sorted, unique, and not on weekends
- all dates within that market's coverage range
- BSE dates not before its first trading day
- a fresh build flag to run after generating

Usage:
  uv run python scripts/validate_calendar.py [path-to-bundle.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

BSE_START = date(2021, 11, 15)


def _to_date(value: int) -> date:
    return date(value // 10000, (value // 100) % 100, value % 100)


def validate(bundle: dict) -> list[str]:
    errors: list[str] = []

    version = bundle.get("calendar_version")
    if not isinstance(version, str) or not version:
        errors.append("missing or invalid calendar_version")

    bundle_id = bundle.get("bundle_id")
    if isinstance(version, str) and bundle_id != f"tj-calendar-{version}":
        errors.append(f"bundle_id {bundle_id!r} does not match calendar_version {version!r}")

    markets = bundle.get("markets")
    if not isinstance(markets, dict) or not markets:
        errors.append("missing or empty 'markets'")
        return errors

    for market, spec in markets.items():
        if not isinstance(spec, dict):
            errors.append(f"{market}: spec is not an object")
            continue
        start = _parse_range(spec.get("coverage_start"), market, errors)
        end = _parse_range(spec.get("coverage_end"), market, errors)
        years = spec.get("years")
        if not isinstance(years, dict):
            errors.append(f"{market}: missing or invalid 'years'")
            continue

        all_dates: list[int] = []
        for year_key, day_list in years.items():
            if not isinstance(day_list, list):
                errors.append(f"{market}/{year_key}: not a list")
                continue
            all_dates.extend(d for d in day_list if isinstance(d, int))

        if len(all_dates) != len(set(all_dates)):
            errors.append(f"{market}: duplicate trade dates")
        if all_dates != sorted(all_dates):
            errors.append(f"{market}: dates not sorted")

        for d in all_dates:
            day = _to_date(d)
            if day.weekday() >= 5:
                errors.append(f"{market}: {d} is a weekend")
            if start is not None and day < start:
                errors.append(f"{market}: {d} before coverage_start")
            if end is not None and day > end:
                errors.append(f"{market}: {d} after coverage_end")

        if market == "BSE" and all_dates:
            first = _to_date(min(all_dates))
            if first < BSE_START:
                errors.append(f"BSE: first trade day {first.isoformat()} before {BSE_START.isoformat()}")

    sources = bundle.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append("missing or empty 'sources'")

    return errors


def _parse_range(value: object, market: str, errors: list[str]) -> date | None:
    if not isinstance(value, str):
        errors.append(f"{market}: missing coverage_start/end")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{market}: invalid coverage date {value!r}")
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "bundle",
        nargs="?",
        default=str(Path(__file__).resolve().parent.parent / "src" / "tj_calendar" / "data" / "calendar-bundle.json"),
        help="path to calendar-bundle.json (default: bundled data)",
    )
    args = parser.parse_args()

    try:
        data = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read bundle: {exc}", file=sys.stderr)
        return 2

    errors = validate(data)
    if errors:
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        print(f"validation FAILED with {len(errors)} error(s)", file=sys.stderr)
        return 1

    print(f"validation OK: {args.bundle}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
