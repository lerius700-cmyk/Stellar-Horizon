"""Create GitHub release v1.2.0 with the .zip asset.

Usage: python tools/create_v1_2_0_release.py
"""
import os
import sys
from pathlib import Path

import urllib.request
import urllib.error
import json


def main() -> int:
    token = os.environ.get("STELLAR_HORIZON_TOKEN")
    if not token:
        print("ERROR: STELLAR_HORIZON_TOKEN not set", file=sys.stderr)
        return 1

    repo_root = Path(__file__).resolve().parent.parent
    notes_path = repo_root / "RELEASE_NOTES_v1.2.0.md"
    zip_path = repo_root / "releases" / "StellarHorizon-v1.2.0-win64.zip"

    if not notes_path.exists():
        print(f"ERROR: {notes_path} not found", file=sys.stderr)
        return 1
    if not zip_path.exists():
        print(f"ERROR: {zip_path} not found", file=sys.stderr)
        return 1

    release_body = notes_path.read_text(encoding="utf-8")

    # 1) Create the release (no asset yet)
    create_url = "https://api.github.com/repos/lerius700-cmyk/Stellar-Horizon/releases"
    payload = {
        "tag_name": "v1.2.0",
        "name": "Stellar Horizon v1.2.0 — Realistic destruction + visual polish",
        "body": release_body,
        "draft": False,
        "prerelease": False,
    }
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
    }

    req = urllib.request.Request(
        create_url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code}: {body}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    release_url = data.get("html_url", "")
    upload_url = data.get("upload_url", "").replace("{?name,label}", "")
    print(f"Release created: {release_url}")
    print(f"Upload URL: {upload_url}")

    # 2) Upload the .zip asset
    asset_name = zip_path.name
    asset_size = zip_path.stat().st_size
    with open(zip_path, "rb") as f:
        asset_bytes = f.read()

    upload_headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/zip",
    }
    upload_headers["Content-Length"] = str(asset_size)

    upload_req = urllib.request.Request(
        f"{upload_url}?name={asset_name}",
        data=asset_bytes,
        headers=upload_headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(upload_req, timeout=120) as resp:
            asset_data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"Asset upload HTTP {e.code}: {body}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Asset upload error: {e}", file=sys.stderr)
        return 1

    asset_url = asset_data.get("browser_download_url", "")
    print(f"Asset uploaded: {asset_url}")
    print(f"Total size: {asset_size / 1024 / 1024:.2f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
