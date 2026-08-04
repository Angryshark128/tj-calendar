"""Online calendar update with metadata-based pre-check.

Flow:
1. Fetch a tiny `metadata.json` (remote version + sha256 + bundle URL).
2. Compare against the local calendar_version; skip the download if up to date.
3. Otherwise fetch the bundle, verify its sha256, and atomically replace the
   local file. A failed update never destroys the currently usable calendar.

The update source is configured by the user, never hardcoded:
the `TIANJI_CALENDAR_METADATA_URL` env var (or `TIANJI_CALENDAR_MIRROR_URLS`,
a colon-separated list of fallback mirrors) must be set to use online updates.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from tj_calendar.errors import CalendarDataError, CalendarUpdateError
from tj_calendar.loader import BUNDLED_PATH, local_bundle_path, local_metadata_path


def _metadata_urls() -> list[str]:
    """Configured metadata URLs, or raise if none are set."""
    mirror_var = os.environ.get("TIANJI_CALENDAR_MIRROR_URLS")
    if mirror_var:
        urls = [u.strip() for u in mirror_var.split(":") if u.strip()]
    else:
        single = os.environ.get("TIANJI_CALENDAR_METADATA_URL")
        urls = [single.strip()] if single and single.strip() else []
    if not urls:
        raise CalendarUpdateError(
            "no update source configured; set TIANJI_CALENDAR_METADATA_URL "
            "to the metadata.json URL (or TIANJI_CALENDAR_MIRROR_URLS for mirrors)"
        )
    return urls


def _fetch_text(url: str, timeout: float = 15.0) -> str:
    """Fetch a URL's text content, raising CalendarUpdateError on failure."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
            return resp.read().decode("utf-8")
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise CalendarUpdateError(f"failed to fetch {url}: {exc}") from exc


def _read_bundle_version(path: Path) -> str | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        version = data.get("calendar_version")
        return version if isinstance(version, str) and version else None
    except (OSError, json.JSONDecodeError):
        return None


def _local_version() -> str | None:
    """Best-effort current calendar version.

    Priority: local metadata -> local bundle -> bundled data. The bundled data
    is the effective version before any update, so it must be included.
    """
    for path in (local_metadata_path(), local_bundle_path(), BUNDLED_PATH):
        version = _read_bundle_version(path)
        if version:
            return version
    return None


def _parse_metadata(text: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CalendarUpdateError(f"remote metadata.json is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise CalendarUpdateError("remote metadata.json must be a JSON object")
    for key in ("calendar_version", "sha256", "bundle_url"):
        if not isinstance(data.get(key), str) or not data.get(key):
            raise CalendarUpdateError(f"remote metadata.json missing valid '{key}'")
    return data


def check_for_update(metadata_urls: list[str] | None = None) -> dict[str, Any]:
    """Fetch remote metadata and report whether an update is needed.

    Returns a dict with the remote metadata and a boolean ``update_needed``.
    Raises CalendarUpdateError if no source is configured or all mirrors fail.
    """
    urls = metadata_urls or _metadata_urls()
    local = _local_version()

    errors: list[str] = []
    for url in urls:
        try:
            meta = _parse_metadata(_fetch_text(url))
            remote = meta.get("calendar_version", "")
            return {
                **meta,
                "local_version": local,
                "remote_version": remote,
                "update_needed": remote != local,
            }
        except CalendarUpdateError as exc:
            errors.append(str(exc))
    raise CalendarUpdateError("all update mirrors failed:\n  " + "\n  ".join(errors))


def update_calendar(metadata_urls: list[str] | None = None) -> dict[str, Any]:
    """Check for and apply a calendar update if needed. Returns a status dict."""
    result = check_for_update(metadata_urls)
    if not result["update_needed"]:
        return {
            "updated": False,
            "reason": "already up to date",
            "local_version": result["local_version"],
            "remote_version": result["remote_version"],
        }

    bundle_url = result["bundle_url"]
    expected_sha256 = result["sha256"]
    try:
        body = _fetch_text(bundle_url)
    except CalendarUpdateError as exc:
        raise CalendarUpdateError(f"failed to download bundle: {exc}") from exc

    actual = hashlib.sha256(body.encode("utf-8")).hexdigest()
    if actual != expected_sha256:
        raise CalendarUpdateError(
            f"sha256 mismatch: expected {expected_sha256}, got {actual}; bundle may be corrupt or from a bad mirror"
        )

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise CalendarUpdateError(f"downloaded bundle is not valid JSON: {exc}") from exc

    # Validate before replacing: corrupt data must never clobber the working file.
    _validate_bundle(data)

    out = local_bundle_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    tmp.write_text(body, encoding="utf-8")
    os.replace(tmp, out)

    meta_out = local_metadata_path()
    meta_out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "updated": True,
        "local_version": result["local_version"],
        "remote_version": result["remote_version"],
    }


def ensure_fresh(metadata_urls: list[str] | None = None) -> dict[str, Any]:
    """Ensure the calendar is up to date before querying.

    Safe to call on every run: it fetches only the small metadata file and
    downloads the full bundle only when the version differs. Silent when the
    data is already current.
    """
    return update_calendar(metadata_urls)


def _validate_bundle(data: Any) -> None:
    """Lightweight structural validation of a downloaded bundle."""
    if not isinstance(data, dict):
        raise CalendarDataError("bundle must be a JSON object")
    if not isinstance(data.get("calendar_version"), str) or not data["calendar_version"]:
        raise CalendarDataError("bundle missing valid 'calendar_version'")
    markets = data.get("markets")
    if not isinstance(markets, dict) or not markets:
        raise CalendarDataError("bundle missing non-empty 'markets'")
