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


def test_run_e5_reaches_detector_only_through_contraction():
    # run_e5 builds Arm C exclusively via contraction.contract() (PROTOCOL §4 seam): it must NOT
    # import the detector directly. It may reach detector transitively through contraction (that
    # is where the contamination seam legitimately lives), but its own imports must not name it.
    run_e5_imports = _internal_imports(PKG / "run_e5.py")
    assert "detector" not in run_e5_imports, (
        f"run_e5 imports detector directly: {sorted(run_e5_imports)}"
    )
    # And no direct is_contaminated call in the run path (source-level guard for the seam).
    src = (PKG / "run_e5.py").read_text()
    assert "is_contaminated" not in src, "run_e5 must not call the detector directly"


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


def test_run_e5_is_a_runner_not_a_scoring_module():
    # run_e5 is a runner like pilot: it MAY import providers (it drives real generation). It is
    # therefore deliberately EXCLUDED from _SCORING_MODULES. This test records that intent so a
    # future edit that adds run_e5 to the scoring list (which would wrongly forbid its provider
    # use) fails loudly and forces the author to reconsider.
    assert "run_e5" not in _SCORING_MODULES
    # It gates its provider import behind a function-local `from .providers import make_provider`
    # (only reached on a real run), same as pilot: no top-level, module-scope providers import.
    # (The AST walk in _internal_imports cannot see import scope, so this checks the source text
    # for a module-level `from .providers` at column 0 — the thing that would pull the SDK in on
    # a bare `import closure_harness.run_e5`.)
    src = (PKG / "run_e5.py").read_text()
    assert "\nfrom .providers import" not in src, (
        "run_e5 should import providers lazily (function-local), like pilot"
    )


def test_scoring_modules_have_no_dynamic_imports_of_providers():
    # The AST walk sees only static imports. providers/pilot are the network-facing modules;
    # a dynamic importlib pull into a scoring module would evade the graph walk above — close
    # that at the source-text level for every scoring module.
    for module in _SCORING_MODULES:
        src = (PKG / f"{module}.py").read_text()
        assert "importlib" not in src, f"{module}.py must not use dynamic imports"
        assert "__import__" not in src, f"{module}.py must not use dynamic imports"
