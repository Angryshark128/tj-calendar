"""Command-line interface for tj-calendar."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from tj_calendar.calendar import (
    get_calendar_info,
    is_trade_day,
    next_trade_day,
    prev_trade_day,
    trade_days_between,
)
from tj_calendar.errors import TianjiCalendarError
from tj_calendar.types import DEFAULT_MARKET, SUPPORTED_MARKETS
from tj_calendar.update import check_for_update, update_calendar


def _print_json(obj: object) -> None:
    print(json.dumps(obj, ensure_ascii=False, default=str))


def _today() -> date:
    return date.today()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tjcal",
        description="Offline-first China market trading calendar.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--market",
        default=DEFAULT_MARKET,
        choices=list(SUPPORTED_MARKETS),
        help=f"market (default: {DEFAULT_MARKET})",
    )
    common.add_argument("--json", action="store_true", help="output as JSON")

    sub.add_parser("today", parents=[common], help="show whether today is a trading day")
    sub.add_parser("info", parents=[common], help="show calendar info")
    sub.add_parser("check-update", parents=[common], help="check for a calendar update")
    sub.add_parser("update", parents=[common], help="update the calendar if needed")

    for name in ("check", "next", "prev"):
        p = sub.add_parser(name, parents=[common], help=f"query {name} trade day")
        p.add_argument("date", help="date as YYYY-MM-DD")
    p = sub.add_parser("range", parents=[common], help="list trade days in a range")
    p.add_argument("start", help="start date YYYY-MM-DD")
    p.add_argument("end", help="end date YYYY-MM-DD")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    market = args.market

    try:
        if args.command == "today":
            today = _today()
            result = is_trade_day(today, market=market)
            if args.json:
                _print_json({"date": today.isoformat(), "is_trade_day": result, "market": market})
            else:
                print(f"{today.isoformat()} is {'a' if result else 'not a'} trading day.")
            return 0

        if args.command == "info":
            info = get_calendar_info(market)
            if args.json:
                _print_json(info)
            else:
                for key, value in info.items():
                    print(f"{key}: {value}")
            return 0

        if args.command == "check-update":
            status = check_for_update()
            if args.json:
                _print_json(status)
            else:
                if status["update_needed"]:
                    print(
                        f"update available: {status['local_version']} -> {status['remote_version']}. "
                        "Run `tjcal update` to apply."
                    )
                else:
                    print(f"calendar is up to date ({status['local_version']}).")
            return 0

        if args.command == "update":
            status = update_calendar()
            if args.json:
                _print_json(status)
            else:
                if status["updated"]:
                    print(f"calendar updated: {status['local_version']} -> {status['remote_version']}.")
                else:
                    print(f"calendar already up to date ({status['remote_version']}).")
            return 0

        if args.command == "check":
            result = is_trade_day(args.date, market=market)
            if args.json:
                _print_json({"date": args.date, "is_trade_day": result, "market": market})
            else:
                print(f"{args.date} is {'a' if result else 'not a'} trading day.")
            return 0

        if args.command == "next":
            day = next_trade_day(args.date, market=market)
            if args.json:
                _print_json({"date": day.isoformat(), "market": market})
            else:
                print(day.isoformat())
            return 0

        if args.command == "prev":
            day = prev_trade_day(args.date, market=market)
            if args.json:
                _print_json({"date": day.isoformat(), "market": market})
            else:
                print(day.isoformat())
            return 0

        if args.command == "range":
            days = trade_days_between(args.start, args.end, market=market)
            if args.json:
                _print_json(
                    {"market": market, "start": args.start, "end": args.end, "dates": [d.isoformat() for d in days]}
                )
            else:
                for d in days:
                    print(d.isoformat())
            return 0
    except TianjiCalendarError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
