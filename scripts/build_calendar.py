"""Build the calendar-bundle.json for tj-calendar.

Two modes:
- offline (default): encode the curated holiday list plus weekday approximation.
- live (--fetch): additionally pull already-published trade days from AkShare
  (Sina interface) for the published years, overriding the approximation for
  those years, and mark the bundle as merged in `sources`.

Coverage window 2000-2035. AkShare only knows about already-published years
(China publishes next year's holidays in late December), so unpublished future
years always fall back to the curated/approximate path.

Usage:
  uv run python scripts/build_calendar.py                 # offline
  uv run python scripts/build_calendar.py --fetch         # merge AkShare
"""

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

# Curated A-share holiday closures (trading suspended), inclusive ranges.
# Used for published years when AkShare is unavailable, and as a fallback.
HOLIDAYS: dict[int, list[tuple[str, str]]] = {
    2019: [
        ("2019-01-01", "2019-01-01"),
        ("2019-02-04", "2019-02-10"),
        ("2019-04-05", "2019-04-07"),
        ("2019-05-01", "2019-05-04"),
        ("2019-06-07", "2019-06-09"),
        ("2019-09-13", "2019-09-15"),
        ("2019-10-01", "2019-10-07"),
    ],
    2020: [
        ("2020-01-01", "2020-01-01"),
        ("2020-01-24", "2020-02-02"),  # Spring Festival + COVID extension
        ("2020-04-04", "2020-04-06"),
        ("2020-05-01", "2020-05-05"),
        ("2020-06-25", "2020-06-27"),
        ("2020-10-01", "2020-10-08"),
    ],
    2021: [
        ("2021-01-01", "2021-01-03"),
        ("2021-02-11", "2021-02-17"),
        ("2021-04-03", "2021-04-05"),
        ("2021-05-01", "2021-05-05"),
        ("2021-06-12", "2021-06-14"),
        ("2021-09-19", "2021-09-21"),
        ("2021-10-01", "2021-10-07"),
    ],
    2022: [
        ("2022-01-01", "2022-01-03"),
        ("2022-01-31", "2022-02-06"),
        ("2022-04-03", "2022-04-05"),
        ("2022-04-30", "2022-05-04"),
        ("2022-06-03", "2022-06-05"),
        ("2022-09-10", "2022-09-12"),
        ("2022-10-01", "2022-10-07"),
    ],
    2023: [
        ("2023-01-02", "2023-01-02"),
        ("2023-01-23", "2023-01-29"),
        ("2023-04-05", "2023-04-05"),
        ("2023-05-01", "2023-05-03"),
        ("2023-06-22", "2023-06-24"),
        ("2023-09-29", "2023-10-06"),
    ],
    2024: [
        ("2024-01-01", "2024-01-01"),
        ("2024-02-09", "2024-02-17"),  # Feb 9 (Fri) adjusted holiday
        ("2024-04-04", "2024-04-06"),
        ("2024-05-01", "2024-05-05"),
        ("2024-06-10", "2024-06-10"),
        ("2024-09-15", "2024-09-17"),
        ("2024-10-01", "2024-10-07"),
    ],
    2025: [
        ("2025-01-01", "2025-01-01"),
        ("2025-01-28", "2025-02-04"),
        ("2025-04-04", "2025-04-06"),
        ("2025-05-01", "2025-05-05"),
        ("2025-05-31", "2025-06-02"),
        ("2025-10-01", "2025-10-08"),
    ],
    2026: [
        ("2026-01-01", "2026-01-01"),
        ("2026-02-16", "2026-02-24"),  # Spring Festival approx, best-effort
        ("2026-04-05", "2026-04-07"),
        ("2026-05-01", "2026-05-05"),
        ("2026-06-19", "2026-06-21"),
        ("2026-10-01", "2026-10-08"),
    ],
    2027: [
        ("2027-01-01", "2027-01-03"),
        ("2027-02-08", "2027-02-16"),  # approx
        ("2027-04-03", "2027-04-05"),
        ("2027-05-01", "2027-05-03"),
        ("2027-06-10", "2027-06-12"),
        ("2027-10-01", "2027-10-07"),
    ],
}

# Coverage: full history from the earliest Shanghai Stock Exchange trading day.
COVERAGE_START = "1990-12-19"
COVERAGE_END = "2035-12-31"
BSE_START = "2021-11-15"


def default_calendar_version() -> str:
    """Candidate version for a fresh build: today's date (YYYY.MM.DD).

    The publish pipeline only uses this when content actually changed; if the
    bundle is unchanged it reuses the remote version so no new folder is made.
    """
    from datetime import date as _date

    return _date.today().strftime("%Y.%m.%d")


def _days_in_year(year: int) -> int:
    return 366 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 365


def _is_closed(day: date) -> bool:
    closures = HOLIDAYS.get(day.year, [])
    for start, end in closures:
        s = date.fromisoformat(start)
        e = date.fromisoformat(end)
        if s <= day <= e:
            return True
    return False


def _trade_days(start: date, end: date) -> list[int]:
    """Weekdays minus encoded holiday closures (weekend/closure => no trade)."""
    result: list[int] = []
    day = start
    while day <= end:
        if day.weekday() < 5 and not _is_closed(day):
            result.append(day.year * 10000 + day.month * 100 + day.day)
        day += timedelta(days=1)
    return result


def _fetch_akshare_trade_days() -> dict[int, set[int]]:
    """Pull published trade days from AkShare's Sina interface.

    Returns {year: set[int]} for the years AkShare reports. Imports are lazy:
    AkShare is an optional dependency (install via `pip install tj-calendar[data]`).
    """
    try:
        import akshare as ak  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "AkShare is required for live fetch. Install with `pip install tj-calendar[akshare]`."
        ) from exc

    df = ak.tool_trade_date_hist_sina()
    dates: dict[int, set[int]] = {}
    for raw in df["trade_date"].tolist():
        try:
            day = date.fromisoformat(str(raw))
        except ValueError:
            continue
        dates.setdefault(day.year, set()).add(day.year * 10000 + day.month * 100 + day.day)
    return dates


def _by_year(days: list[int]) -> dict[str, list[int]]:
    grouped: dict[str, list[int]] = {}
    for d in days:
        grouped.setdefault(str(d // 10000), []).append(d)
    for vals in grouped.values():
        vals.sort()
    return {str(y): grouped[str(y)] for y in sorted(int(y) for y in grouped)}


def _merge_with_live(base: list[int], live: dict[int, set[int]]) -> tuple[list[int], list[int]]:
    """Replace approximation days with AkShare days for published years.

    Live data may extend before/after the coverage window (AkShare goes back
    to 1990); clamp it to [COVERAGE_START, COVERAGE_END].

    Returns (merged_days, years_covered_by_live).
    """
    lo = date.fromisoformat(COVERAGE_START)
    hi = date.fromisoformat(COVERAGE_END)
    lo_int = lo.year * 10000 + lo.month * 100 + lo.day
    hi_int = hi.year * 10000 + hi.month * 100 + hi.day

    live_years: list[int] = []
    merged = set(base)
    for year in sorted(live):
        kept = {d for d in live[year] if lo_int <= d <= hi_int}
        if not kept:
            continue
        # Remove the approximation for that year, then add the authoritative set.
        merged = {d for d in merged if d // 10000 != year}
        merged |= kept
        live_years.append(year)
    return sorted(merged), live_years


def content_hash(bundle: dict) -> str:
    """Hash of the actual calendar content, excluding version metadata.

    calendar_version / bundle_id are stamped at publish time and must not
    influence change detection, otherwise every daily run looks "changed".
    Only markets + sources reflect real data changes.
    """
    import hashlib

    payload = json.dumps(
        {"markets": bundle["markets"], "sources": bundle.get("sources", [])},
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_bundle(fetch: bool = False, version: str | None = None) -> dict:
    start = date.fromisoformat(COVERAGE_START)
    end = date.fromisoformat(COVERAGE_END)
    cn_days = _trade_days(start, end)

    live_years: list[int] = []
    if fetch:
        live = _fetch_akshare_trade_days()
        cn_days, live_years = _merge_with_live(cn_days, live)

    calendar_version = version or default_calendar_version()
    bundle_id = f"tj-calendar-{calendar_version}"

    sources: list[dict] = [
        {
            "name": "manual",
            "description": (
                "Encoded public exchange holiday schedules for 2019-2027; "
                "other years use a weekday approximation and are best-effort."
            ),
        }
    ]
    if live_years:
        sources.append(
            {
                "name": "akshare_sina",
                "description": (
                    "Trade days for published years fetched from AkShare "
                    "(Sina tool_trade_date_hist_sina); years: "
                    f"{', '.join(str(y) for y in live_years)}."
                ),
            }
        )

    return {
        "schema_version": 1,
        "calendar_version": calendar_version,
        "bundle_id": bundle_id,
        "timezone": "Asia/Shanghai",
        "generated_at": "2026-08-04T00:00:00+08:00",
        "markets": {
            "CN_A_SHARE": {
                "name": "China A-share market",
                "coverage_start": COVERAGE_START,
                "coverage_end": COVERAGE_END,
                "years": _by_year(cn_days),
            },
            "SSE": {
                "name": "Shanghai Stock Exchange",
                "coverage_start": COVERAGE_START,
                "coverage_end": COVERAGE_END,
                "years": _by_year(cn_days),
            },
            "SZSE": {
                "name": "Shenzhen Stock Exchange",
                "coverage_start": COVERAGE_START,
                "coverage_end": COVERAGE_END,
                "years": _by_year(cn_days),
            },
            "BSE": {
                "name": "Beijing Stock Exchange",
                "coverage_start": BSE_START,
                "coverage_end": COVERAGE_END,
                "years": _by_year([d for d in cn_days if d >= 20211115]),
            },
        },
        "special_closures": [
            {
                "date": 20200131,
                "market": "CN_A_SHARE",
                "reason": "COVID-19 extended Spring Festival holiday",
            }
        ],
        "sources": sources,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true", help="merge live AkShare trade days")
    parser.add_argument(
        "--out",
        default=str(Path(__file__).resolve().parent.parent / "src" / "tj_calendar" / "data" / "calendar-bundle.json"),
        help="output path",
    )
    args = parser.parse_args()

    bundle = build_bundle(fetch=args.fetch)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
