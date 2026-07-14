"""Import-hygiene (0007 separation).

outcomes.py scores every arm against ground-truth annotations and must never touch the
detector that built Arm C — otherwise an arm is scored by the instrument that selected it.
This test walks the transitive import graph of closure_harness.outcomes and asserts
closure_harness.detector is absent.
"""

from __future__ import annotations

import ast
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent / "src" / "closure_harness"


def _internal_imports(module_file: Path) -> set[str]:
    tree = ast.parse(module_file.read_text())
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            # relative (level>0) or absolute closure_harness.*
            mod = node.module
            if node.level > 0 or mod.startswith("closure_harness"):
                names.add(mod.split(".")[-1])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("closure_harness"):
                    names.add(alias.name.split(".")[-1])
    return names


def _transitive(start: str) -> set[str]:
    seen: set[str] = set()
    stack = [start]
    while stack:
        mod = stack.pop()
        if mod in seen:
            continue
        seen.add(mod)
        f = PKG / f"{mod}.py"
        if f.exists():
            stack.extend(_internal_imports(f) - seen)
    return seen


def test_outcomes_does_not_import_detector():
    reached = _transitive("outcomes")
    assert "detector" not in reached, f"outcomes transitively imports: {sorted(reached)}"


def test_detector_is_only_reached_through_contraction():
    # Sanity anchor for the separation: contraction is the only module that pulls in detector.
    reached_from_contraction = _transitive("contraction")
    assert "detector" in reached_from_contraction
