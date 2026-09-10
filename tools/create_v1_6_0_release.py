"""Create the GitHub release for Stellar Horizon v1.6.0.

Per memory rule 2026-08-31: NEVER print the GitHub token, even
masked. The token is read from the STELLAR_HORIZON_TOKEN env var
and used silently. If the auth fails, the API returns a JSON error
which we log; we do NOT log the token.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


GITHUB_API = "https://api.github.com"
REPO = "lerius700-cmyk/Stellar-Horizon"
TAG = "v1.7.2"
ZIP_PATH = Path("StellarHorizon-v1.7.2-win64.zip")
NOTES_PATH = Path("RELEASE_NOTES_v1.7.2.md")


def _check_status(resp: urllib.request.addinfourl) -> dict:
    raw = resp.read().decode("utf-8", errors="replace")
    if resp.status >= 400:
        sys.stderr.write(
            f"GitHub API error {resp.status} {resp.reason}\n{raw}\n"
        )
        raise SystemExit(1)
    if not raw:
        return {}
    return json.loads(raw)


def _auth_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "StellarHorizon-release-script",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _read_token_from_registry() -> str:
    """Read STELLAR_HORIZON_TOKEN from HKCU\\Environment via
    PowerShell. Returns '' if not set. This is the ground truth;
    os.environ may be stale (cached in the calling process).
    """
    import subprocess
    ps_cmd = (
        "[System.Environment]::GetEnvironmentVariable("
        "'STELLAR_HORIZON_TOKEN', 'User')"
    )
    try:
        out = subprocess.check_output(
            ["powershell.exe", "-NoProfile", "-NonInteractive",
             "-Command", ps_cmd],
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
            FileNotFoundError):
        return ""
    return out.decode("utf-8", errors="replace").strip()


def main() -> int:
    # 2026-09-08: prefer the env var (for CI / containers), but
    # fall back to HKCU\Environment so a stale in-memory cache
    # after `setx` doesn't block the release.
    token = os.environ.get("STELLAR_HORIZON_TOKEN", "")
    source = "env"
    if not token:
        token = _read_token_from_registry()
        source = "registry"
    if not token:
        sys.stderr.write(
            "STELLAR_HORIZON_TOKEN not found (env or HKCU\\Environment). "
            "Value is never printed.\n"
        )
        return 1
    sys.stdout.write(
        f"Authenticating with GitHub (token len={len(token)}, "
        f"source={source}).\n"
    )
    if not ZIP_PATH.exists():
        sys.stderr.write(f"Missing: {ZIP_PATH}\n")
        return 1
    if not NOTES_PATH.exists():
        sys.stderr.write(f"Missing: {NOTES_PATH}\n")
        return 1
    notes = NOTES_PATH.read_text(encoding="utf-8")
    sys.stdout.write(f"Release notes: {len(notes)} chars\n")
    # 1. Create the release.
    body = json.dumps({
        "tag_name": TAG,
        "name": "Stellar Horizon v1.7.2 -- Ring Pickup SFX",
        "body": notes,
        "draft": False,
        "prerelease": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{GITHUB_API}/repos/{REPO}/releases",
        data=body, method="POST",
        headers={
            **_auth_headers(token),
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            release = _check_status(resp)
    except urllib.error.HTTPError as e:
        # e.g., 422 if the tag already has a release.
        body = e.read().decode("utf-8", errors="replace")
        sys.stderr.write(f"Release POST failed: {e.code} {e.reason}\n{body}\n")
        return 1
    upload_url = release.get("upload_url", "")
    if not upload_url:
        sys.stderr.write("Release created but no upload_url returned.\n")
        return 1
    # The upload_url ends with `{?name,label}` -- strip the suffix.
    if "{" in upload_url:
        upload_url = upload_url.split("{", 1)[0]
    sys.stdout.write(f"Release created: id={release.get('id')}\n")
    # 2. Upload the .zip asset.
    zip_bytes = ZIP_PATH.read_bytes()
    sys.stdout.write(f"Uploading {ZIP_PATH} ({len(zip_bytes):,} bytes)\n")
    asset_req = urllib.request.Request(
        f"{upload_url}?name={ZIP_PATH.name}",
        data=zip_bytes, method="POST",
        headers={
            **_auth_headers(token),
            "Content-Type": "application/zip",
        },
    )
    try:
        with urllib.request.urlopen(asset_req) as resp:
            asset = _check_status(resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        sys.stderr.write(f"Asset upload failed: {e.code} {e.reason}\n{body}\n")
        return 1
    sys.stdout.write(
        f"Asset uploaded: {asset.get('browser_download_url', '<no url>')}\n"
    )
    sys.stdout.write("DONE\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
