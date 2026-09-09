"""Read-only GitHub auth check that reads the token from the
Windows registry (HKCU\\Environment\\STELLAR_HORIZON_TOKEN) so
the check is not affected by a stale env var in the calling
process. Per memory rule 2026-09-08: never print the token,
only its length.

If the env var IS set in the current process, that wins (useful
for CI / container scenarios where setx is not used). Otherwise
fall back to the registry via PowerShell.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request


def _read_token_from_registry() -> str:
    """Read STELLAR_HORIZON_TOKEN from HKCU\\Environment via
    PowerShell. Returns '' if the var is not set.
    """
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
    # 2026-09-08 v1.6.0 release flow: always read the token from the
    # registry (HKCU\Environment\STELLAR_HORIZON_TOKEN) so a stale
    # in-memory env var (e.g. one set before the user regenerated
    # the PAT) does not mask the freshly-setx'd value. The
    # `os.environ` cache can be hours old; the registry is the
    # ground truth.
    token = _read_token_from_registry()
    source = "registry"
    sys.stdout.write(
        f"token len={len(token)} (source={source})\n"
    )
    if not token:
        sys.stderr.write(
            "NO STELLAR_HORIZON_TOKEN (env or HKCU\\Environment)\n"
        )
        return 1
    req = urllib.request.Request(
        "https://api.github.com/repos/lerius700-cmyk/Stellar-Horizon"
        "/releases/tags/v1.6.0",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "StellarHorizon-auth-check",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            sys.stdout.write(
                f"OK status={resp.status} tag={data.get('tag_name')} "
                f"assets={len(data.get('assets', []))}\n"
            )
            for a in data.get("assets", []):
                sys.stdout.write(
                    f"  asset: {a.get('name')}  "
                    f"{a.get('size'):,} bytes  "
                    f"downloads={a.get('download_count', 0)}\n"
                )
        return 0
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        sys.stderr.write(f"AUTH FAILED: {e.code} {e.reason}\n{body[:500]}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
