"""Publish a calendar bundle to Tencent Cloud COS.

Automates the whole release flow so no manual download/verify/upload is needed:

1. Rebuild the bundle (offline or with AkShare fetch).
2. Validate it locally.
3. Upload versioned artifacts to `<prefix>/v<version>/`.
4. Re-fetch the uploaded bundle and compare its sha256 (verify the upload).
5. Finally update `<prefix>/latest/metadata.json` pointing at the new version.

The `latest` pointer is written LAST so users never download a half-published
release. Credentials come from environment variables, never from files:

  TIANJI_COS_BUCKET      bucket name (default: tj-1310342032)
  TIANJI_COS_REGION      region (default: ap-beijing)
  TIANJI_COS_PREFIX      key prefix inside the bucket (default: calendar)
  TIANJI_COS_SECRET_ID   Tencent Cloud SecretId
  TIANJI_COS_SECRET_KEY  Tencent Cloud SecretKey

Requires the optional `cos-python-sdk-v5` package:
  uv run --with cos-python-sdk-v5 python scripts/publish.py --fetch
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from build_calendar import build_bundle, content_hash
from validate_calendar import validate

ROOT = Path(__file__).resolve().parent.parent

BUCKET = os.environ.get("TIANJI_COS_BUCKET", "tj-1310342032")
REGION = os.environ.get("TIANJI_COS_REGION", "ap-beijing")
PREFIX = os.environ.get("TIANJI_COS_PREFIX", "calendar").strip("/")
SECRET_ID = os.environ.get("TIANJI_COS_SECRET_ID", "")
SECRET_KEY = os.environ.get("TIANJI_COS_SECRET_KEY", "")


def _key(path: str) -> str:
    return f"{PREFIX}/{path}" if PREFIX else path


def _require_secrets() -> None:
    if not SECRET_ID or not SECRET_KEY:
        print(
            "error: TIANJI_COS_SECRET_ID and TIANJI_COS_SECRET_KEY must be set",
            file=sys.stderr,
        )
        raise SystemExit(2)


def _client():
    from qcloud_cos import CosConfig, CosS3Client  # type: ignore[import-not-found]

    config = CosConfig(Region=REGION, SecretId=SECRET_ID, SecretKey=SECRET_KEY)
    return CosS3Client(config), config


def _remote_url(key: str) -> str:
    return f"https://{BUCKET}.cos.{REGION}.myqcloud.com/{key}"


def _upload_bytes(client, key: str, body: bytes, content_type: str) -> None:
    client.put_object(Bucket=BUCKET, Key=key, Body=body, ContentType=content_type)
    print(f"  uploaded {key} ({len(body)} bytes)")


def _remote_sha256(client, key: str) -> str:
    resp = client.get_object(Bucket=BUCKET, Key=key)
    body = resp["Body"].get_raw_stream().read()
    return hashlib.sha256(body).hexdigest()


def _remote_metadata(client) -> dict | None:
    """Fetch the current latest/metadata.json, or None if absent."""
    try:
        resp = client.get_object(Bucket=BUCKET, Key=_key("latest/metadata.json"))
        body = resp["Body"].get_raw_stream().read()
        data = json.loads(body)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _remote_version_sha256(client, key: str) -> str | None:
    """Read the sha256 file for a versioned bundle, or None if absent."""
    try:
        resp = client.get_object(Bucket=BUCKET, Key=key)
        text = resp["Body"].get_raw_stream().read().decode("utf-8").strip()
        return text if text else None
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true", help="merge live AkShare trade days")
    parser.add_argument("--dry-run", action="store_true", help="build + validate but skip upload")
    args = parser.parse_args()

    if not args.dry_run:
        _require_secrets()

    print("1/5 building bundle...")
    # Build with a candidate version (today's date); the real version is
    # decided below based on whether calendar content actually changed.
    bundle = build_bundle(fetch=args.fetch)
    body = json.dumps(bundle, indent=2, ensure_ascii=False).encode("utf-8")
    full_sha = hashlib.sha256(body).hexdigest()

    print("2/5 validating bundle...")
    errors = validate(bundle)
    if errors:
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        print("validation FAILED; aborting", file=sys.stderr)
        return 1

    # Decide the version. content_hash excludes calendar_version/bundle_id, so
    # a daily run with unchanged data produces the same hash -> keep the remote
    # version and skip the upload (no new folder). Only when the calendar data
    # actually differs do we stamp today's date as a new version.
    if not args.dry_run:
        client, _ = _client()
        remote_meta = _remote_metadata(client)
    else:
        client, remote_meta = None, None

    chash = content_hash(bundle)
    if remote_meta and remote_meta.get("content_sha256") == chash:
        version = remote_meta["calendar_version"]
        print(f"  content unchanged ({chash[:12]}...); keeping version {version}")
    else:
        version = bundle["calendar_version"]  # today's date
        print(f"  content changed; new version {version}")

    bundle["calendar_version"] = version
    bundle["bundle_id"] = f"tj-calendar-{version}"
    body = json.dumps(bundle, indent=2, ensure_ascii=False).encode("utf-8")
    full_sha = hashlib.sha256(body).hexdigest()

    print("3/5 preparing artifacts...")
    version_dir = _key(f"v{version}")
    artifacts: list[tuple[str, bytes, str]] = [
        (f"{version_dir}/calendar-bundle.json", body, "application/json"),
        (f"{version_dir}/calendar-bundle.json.sha256", (full_sha + "\n").encode(), "text/plain"),
    ]
    metadata = {
        "schema_version": 1,
        "calendar_version": version,
        "bundle_id": bundle["bundle_id"],
        "sha256": full_sha,
        "content_sha256": chash,
        "bundle_url": _remote_url(f"{version_dir}/calendar-bundle.json"),
        "generated_at": bundle["generated_at"],
    }
    metadata_body = json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8")

    if args.dry_run:
        print("dry-run: artifacts ready (skipping upload)")
        print(f"  version={version} sha256={full_sha[:16]}... content={chash[:12]}...")
        for key, body, _ in artifacts:
            print(f"  {key} ({len(body)} bytes)")
        print(f"  {_key('latest/metadata.json')} ({len(metadata_body)} bytes)")
        return 0

    print("4/5 checking remote state...")
    if remote_meta and remote_meta.get("calendar_version") == version:
        remote_sha = _remote_version_sha256(client, f"{version_dir}/calendar-bundle.json.sha256")
        if remote_sha == full_sha:
            print(f"  already published: {version} with matching sha256; nothing to do")
            # Backfill content_sha256 on legacy metadata so future runs can
            # detect content changes correctly (transition from old format).
            if not remote_meta.get("content_sha256"):
                print("  backfilling content_sha256 in latest metadata")
                _upload_bytes(client, _key("latest/metadata.json"), metadata_body, "application/json")
            return 0
        print("  version exists but sha256 differs; re-publishing versioned artifacts")

    print("uploading versioned artifacts...")
    for key, data, ctype in artifacts:
        _upload_bytes(client, key, data, ctype)

    # Verify upload by re-fetching and comparing sha256.
    remote_sha = _remote_sha256(client, f"{version_dir}/calendar-bundle.json")
    if remote_sha != full_sha:
        print(
            f"error: uploaded bundle sha256 mismatch ({remote_sha} != {full_sha}); not updating latest",
            file=sys.stderr,
        )
        return 1
    print(f"  verified: remote bundle sha256 matches ({remote_sha[:16]}...)")

    print("5/5 updating latest metadata...")
    _upload_bytes(client, _key("latest/metadata.json"), metadata_body, "application/json")

    print("publish OK:", _remote_url(f"{version_dir}/calendar-bundle.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
