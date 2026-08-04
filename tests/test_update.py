"""Tests for tj-calendar online update."""

from __future__ import annotations

import hashlib
import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from tj_calendar import CalendarUpdateError
from tj_calendar.loader import config_dir, local_bundle_path, local_metadata_path
from tj_calendar.update import check_for_update, update_calendar

BUNDLED_VERSION = "2026.08.04"
REMOTE_VERSION = "2026.08.05"

BUNDLE_JSON = {
    "schema_version": 1,
    "calendar_version": REMOTE_VERSION,
    "bundle_id": "tj-calendar-test",
    "timezone": "Asia/Shanghai",
    "markets": {
        "CN_A_SHARE": {
            "coverage_start": "2000-01-01",
            "coverage_end": "2035-12-31",
            "years": {"2026": [20260803, 20260804, 20260805]},
        },
    },
}


class _Handler(BaseHTTPRequestHandler):
    remote_meta: dict = {}
    bundle_body: bytes = b""
    hits: dict = {"metadata": 0, "bundle": 0}

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002  # silence stderr
        pass

    def do_GET(self) -> None:  # noqa: N802
        if self.path.endswith("metadata.json"):
            self.__class__.hits["metadata"] += 1
            body = json.dumps(self.__class__.remote_meta).encode()
            self._send(body, "application/json")
        elif self.path.endswith("calendar-bundle.json"):
            self.__class__.hits["bundle"] += 1
            self._send(self.__class__.bundle_body, "application/json")
        else:
            self.send_error(404)

    def _send(self, body: bytes, ctype: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture()
def server() -> Iterator[HTTPServer]:
    httpd = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd
    httpd.shutdown()
    httpd.server_close()


@pytest.fixture()
def base_url(server: HTTPServer) -> str:
    addr = server.server_address
    return f"http://{addr[0]}:{addr[1]}"


@pytest.fixture()
def make_metadata(base_url: str):
    def _make(version: str = REMOTE_VERSION, sha: str | None = None) -> dict:
        body = json.dumps(BUNDLE_JSON, ensure_ascii=False).encode()
        _Handler.bundle_body = body
        _Handler.remote_meta = {
            "schema_version": 1,
            "calendar_version": version,
            "bundle_id": f"tj-calendar-{version}",
            "sha256": sha or hashlib.sha256(body).hexdigest(),
            "bundle_url": f"{base_url}/tj-calendar/v{version}/calendar-bundle.json",
        }
        return _Handler.remote_meta

    return _make


@pytest.fixture()
def reset_hits():
    _Handler.hits = {"metadata": 0, "bundle": 0}
    return _Handler.hits


@pytest.fixture(autouse=True)
def clear_calendar_cache():
    """TradingCalendar is lru_cached per market; clear it across tests so a
    freshly updated local bundle is actually observed."""
    import tj_calendar.calendar as cal

    cal._get_calendar.cache_clear()
    yield
    cal._get_calendar.cache_clear()


@pytest.fixture()
def isolated_tianji_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point TIANJI_HOME at a temp dir and reset cached paths."""
    monkeypatch.setenv("TIANJI_HOME", str(tmp_path))
    return tmp_path


def _pkg_version() -> str:
    import tj_calendar

    return tj_calendar.__version__


# --- check_for_update ---


def test_no_update_when_version_matches(make_metadata, isolated_tianji_home, base_url):
    make_metadata(version=BUNDLED_VERSION)
    status = check_for_update([f"{base_url}/metadata.json"])
    assert status["update_needed"] is False
    assert status["local_version"] == BUNDLED_VERSION
    assert status["remote_version"] == BUNDLED_VERSION


def test_update_needed_when_version_differs(make_metadata, isolated_tianji_home, base_url):
    make_metadata(version=REMOTE_VERSION)
    status = check_for_update([f"{base_url}/metadata.json"])
    assert status["update_needed"] is True
    assert status["local_version"] == BUNDLED_VERSION
    assert status["remote_version"] == REMOTE_VERSION


def test_all_mirrors_fail_raises(isolated_tianji_home):
    with pytest.raises(CalendarUpdateError):
        check_for_update(["http://127.0.0.1:1/metadata.json"])


def test_second_mirror_used_when_first_fails(make_metadata, isolated_tianji_home, base_url):
    make_metadata(version=REMOTE_VERSION)
    status = check_for_update(["http://127.0.0.1:1/x.json", f"{base_url}/metadata.json"])
    assert status["update_needed"] is True


# --- update_calendar ---


def test_update_downloads_only_when_needed(make_metadata, reset_hits, isolated_tianji_home, base_url):
    # Same version: must NOT hit the bundle endpoint.
    make_metadata(version=BUNDLED_VERSION)
    update_calendar([f"{base_url}/metadata.json"])
    assert _Handler.hits["bundle"] == 0

    # New version: must hit metadata then bundle.
    make_metadata(version=REMOTE_VERSION)
    update_calendar([f"{base_url}/metadata.json"])
    assert _Handler.hits["bundle"] == 1

    # Local file now written and loadable.
    local = local_bundle_path()
    assert local.is_file()
    data = json.loads(local.read_text(encoding="utf-8"))
    assert data["calendar_version"] == REMOTE_VERSION

    meta = local_metadata_path()
    assert meta.is_file()


def test_update_skips_repeated_same_version(make_metadata, reset_hits, isolated_tianji_home, base_url):
    make_metadata(version=REMOTE_VERSION)
    update_calendar([f"{base_url}/metadata.json"])
    first_bundle_hits = _Handler.hits["bundle"]
    assert first_bundle_hits == 1  # first run downloads the bundle

    update_calendar([f"{base_url}/metadata.json"])
    assert _Handler.hits["bundle"] == first_bundle_hits  # second run skips it


def test_update_sha256_mismatch_rejected(make_metadata, isolated_tianji_home, base_url):
    make_metadata(version=REMOTE_VERSION, sha="deadbeef" * 8)
    with pytest.raises(CalendarUpdateError, match="sha256 mismatch"):
        update_calendar([f"{base_url}/metadata.json"])
    # Nothing written; old data preserved.
    assert not local_bundle_path().exists()


def test_update_failed_download_keeps_old_data(make_metadata, isolated_tianji_home, base_url):
    make_metadata(version=REMOTE_VERSION)
    # First apply a real update so there is local data to preserve.
    update_calendar([f"{base_url}/metadata.json"])
    before = local_bundle_path().read_bytes()

    # Newer remote version, but its bundle URL is unavailable (404).
    _Handler.remote_meta = {
        **_Handler.remote_meta,
        "calendar_version": "2026.09.01",
        "bundle_url": f"{base_url}/missing-bundle",
    }
    with pytest.raises(CalendarUpdateError):
        update_calendar([f"{base_url}/metadata.json"])
    assert local_bundle_path().read_bytes() == before


def test_update_writes_usable_bundle(make_metadata, isolated_tianji_home, base_url):
    make_metadata(version=REMOTE_VERSION)
    update_calendar([f"{base_url}/metadata.json"])
    # The freshly written bundle parses and serves queries.
    from tj_calendar import is_trade_day

    assert is_trade_day("2026-08-04") is True
    assert is_trade_day("2026-08-06") is False  # outside the test bundle's data


def test_env_config_dir_honored(isolated_tianji_home):
    assert config_dir() == isolated_tianji_home
    assert local_bundle_path().parent == isolated_tianji_home / "calendar"
    assert _pkg_version() == "0.1.0"


def test_version_constant() -> None:
    import tj_calendar

    assert tj_calendar.__version__ == "0.1.0"
