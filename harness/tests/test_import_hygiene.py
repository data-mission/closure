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
        if isinstance(node, ast.ImportFrom):
            relative = node.level > 0
            pkg = node.module or ""
            if relative or pkg.startswith("closure_harness"):
                if pkg:
                    # `from .foo import x` / `from closure_harness.foo import x`
                    names.add(pkg.split(".")[-1])
                else:
                    # `from . import foo` — the submodule names are the aliases, not `module`.
                    for alias in node.names:
                        names.add(alias.name.split(".")[-1])
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


def test_outcomes_has_no_dynamic_imports():
    # The AST walk resolves static Import/ImportFrom nodes only — a dynamic
    # importlib.import_module("...detector") would be invisible to it. Close the blind
    # spot at the source-text level for the module the separation protects.
    src = (PKG / "outcomes.py").read_text()
    assert "importlib" not in src, "outcomes.py must not use dynamic imports"
    assert "__import__" not in src, "outcomes.py must not use dynamic imports"


def test_detector_is_only_reached_through_contraction():
    # Sanity anchor for the separation: contraction is the only module that pulls in detector.
    reached_from_contraction = _transitive("contraction")
    assert "detector" in reached_from_contraction


# The provider (vendor SDK binding) and the pilot (its CLI driver) must stay out of every
# scoring module's transitive import graph — the scoring path must never pull in a network
# client. Same AST walk, applied to each scoring module.
_SCORING_MODULES = (
    "nli",
    "grounding",
    "detector",
    "contraction",
    "outcomes",
    "stats",
    "generate",
    "schema",
)


def test_scoring_modules_do_not_import_providers_or_pilot():
    for module in _SCORING_MODULES:
        reached = _transitive(module)
        assert "providers" not in reached, (
            f"{module} transitively imports providers: {sorted(reached)}"
        )
        assert "pilot" not in reached, (
            f"{module} transitively imports pilot: {sorted(reached)}"
        )


def test_scoring_modules_have_no_dynamic_imports_of_providers():
    # The AST walk sees only static imports. providers/pilot are the network-facing modules;
    # a dynamic importlib pull into a scoring module would evade the graph walk above — close
    # that at the source-text level for every scoring module.
    for module in _SCORING_MODULES:
        src = (PKG / f"{module}.py").read_text()
        assert "importlib" not in src, f"{module}.py must not use dynamic imports"
        assert "__import__" not in src, f"{module}.py must not use dynamic imports"
