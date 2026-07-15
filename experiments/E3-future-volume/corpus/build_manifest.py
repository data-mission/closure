"""
Build corpus/DISPOSABLE-MANIFEST.jsonl -- every throwaway prompt ever used in the E3 program, one
JSON object per line, tagged with its source. This is the single decontamination reference the
corpus must be disjoint from (assemble_verify.py checks against it).

Sources (all THROWAWAY / DISPOSABLE, none may ever enter corpus/candidates.jsonl):
  - spike-20    : spike/run_spike.py       THROWAWAY_PROMPTS (20 strings)
  - pilot-30    : pilot/run_pilot.py       PROMPTS           (30 (kind, prompt) tuples)
  - rehearsal-41: rehearsal/run_rehearsal.py PROMPTS         (41 (kind, diff, prompt, gold) tuples)
  - calib-*     : hardening/calib_prompts.py ALL_ROUNDS      (all calibration rounds' prompts)

Extraction is by AST literal-eval of the specific list/dict assignment in each source file, so this
script does NOT import mlx or load any model -- it only reads the prompt strings. The calibration
prompts are imported directly (calib_prompts.py has no heavy imports).

Re-runnable: overwrites the manifest deterministically (sorted within source, sources in fixed order).
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
E3 = HERE.parent  # experiments/E3-future-volume
MANIFEST = HERE / "DISPOSABLE-MANIFEST.jsonl"


def _assign_value(pyfile: Path, name: str):
    """Return the Python value of the module-level assignment `name = <literal>` via literal_eval."""
    tree = ast.parse(pyfile.read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == name:
                    return ast.literal_eval(node.value)
    raise KeyError(f"{name} not found in {pyfile}")


def spike_prompts():
    vals = _assign_value(E3 / "spike" / "run_spike.py", "THROWAWAY_PROMPTS")
    return [{"source": "spike-20", "prompt": p} for p in vals]


def pilot_prompts():
    vals = _assign_value(E3 / "pilot" / "run_pilot.py", "PROMPTS")
    return [{"source": "pilot-30", "kind": kind, "prompt": p} for (kind, p) in vals]


def rehearsal_prompts():
    vals = _assign_value(E3 / "rehearsal" / "run_rehearsal.py", "PROMPTS")
    return [{"source": "rehearsal-41", "kind": k, "difficulty": d, "prompt": p, "gold": g}
            for (k, d, p, g) in vals]


def calib_prompts():
    sys.path.insert(0, str(E3 / "hardening"))
    import calib_prompts as cp
    out = []
    for rnd in sorted(cp.ALL_ROUNDS):
        for it in cp.ALL_ROUNDS[rnd]:
            out.append({"source": f"calib-r{rnd}", "kind": it["kind"], "family": it["family"],
                        "prompt": it["prompt"], "gold": it["gold"]})
    return out


def build():
    records = []
    for fn in (spike_prompts, pilot_prompts, rehearsal_prompts, calib_prompts):
        recs = fn()
        # stable order within a source
        recs.sort(key=lambda r: r["prompt"])
        records.extend(recs)
    # duplicate-prompt guard across the whole manifest (a prompt may legitimately recur across
    # sources -- e.g. a spike item reused verbatim -- so we only warn, never drop)
    seen = {}
    for r in records:
        seen.setdefault(r["prompt"], []).append(r["source"])
    dups = {p: s for p, s in seen.items() if len(s) > 1}
    with MANIFEST.open("w") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    from collections import Counter
    by_src = Counter(r["source"] for r in records)
    print(f"[manifest] wrote {len(records)} disposable prompts to {MANIFEST.name}")
    print(f"[manifest] by source: {dict(by_src)}")
    if dups:
        print(f"[manifest] NOTE {len(dups)} prompt(s) appear in >1 source: {dups}")
    return records


if __name__ == "__main__":
    build()
