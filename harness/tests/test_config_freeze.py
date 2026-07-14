"""Config-freeze fixtures (0006).

The frozen config serializes deterministically and its SHA-256 matches the committed hash file
(the pre-registration freeze token). Any drift in a frozen field changes the hash and the
committed check fails.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from closure_harness.config import CONFIG, config_hash, config_json

HASH_FILE = Path(__file__).resolve().parent.parent / "config.sha256"


def test_config_json_is_sorted_and_deterministic():
    a = config_json()
    b = config_json()
    assert a == b
    parsed = json.loads(a)
    assert json.dumps(parsed, sort_keys=True, separators=(",", ":")) == a


def test_hash_matches_committed_file():
    assert HASH_FILE.exists()
    assert config_hash() == HASH_FILE.read_text().strip()


def test_field_change_changes_hash():
    drifted = replace(CONFIG, detector=replace(CONFIG.detector, grounding_floor=0.71))
    assert config_hash(drifted) != config_hash(CONFIG)
