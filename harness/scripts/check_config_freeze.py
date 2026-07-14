"""Fail (nonzero) if the live frozen config drifts from the committed hash.

The committed hash (config.sha256) is the pre-registration freeze token (0006). Any edit to a
frozen field in config.py changes config_hash() and this check fails until the hash file and
the OSF registration are deliberately updated together — which, post-data, requires a new
registration, not an in-place edit.

Runnable now: `uv run python scripts/check_config_freeze.py`. Wiring it into a pre-commit hook
can come later; the check itself must exist and pass.
"""

from __future__ import annotations

import sys
from pathlib import Path

from closure_harness.config import config_hash

HASH_FILE = Path(__file__).resolve().parent.parent / "config.sha256"


def main() -> int:
    live = config_hash()
    if not HASH_FILE.exists():
        print(f"FAIL: committed hash file missing: {HASH_FILE}", file=sys.stderr)
        return 1
    committed = HASH_FILE.read_text().strip()
    if live != committed:
        print("FAIL: config hash drift", file=sys.stderr)
        print(f"  committed: {committed}", file=sys.stderr)
        print(f"  live:      {live}", file=sys.stderr)
        return 1
    print(f"OK: config frozen at {live}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
