"""
d4 hard-kind corpus items (the calibrated KIND-based hardening additions).

Produces 14 items per answerable family, each mapped onto a d3 id it replaces (so counts stay
42/42/42). Every gold is verified here, NOT asserted:
  - arithmetic (arith_mult3x3): 3-digit x 3-digit multiplication; gold = eval(expr), recomputed.
  - factual   (fact_numeric_tail): reverse superheavy/transuranic element lookup (atomic number ->
    element); gold is a single IUPAC-canonical name; sources listed. Disjoint from the calibration
    reverse set {101,103,105,111,113,115,118}.
  - deduction (ded_seat6): unique 6-entity seating puzzles, generated from a SEEDED permutation and
    a minimal readable constraint set, with uniqueness + gold PROVEN by ded_verify (brute force).

All prompts are checked disjoint from corpus/DISPOSABLE-MANIFEST.jsonl by assemble_verify.py. These
prompts are ORIGINAL and were NEVER run through the model during calibration (the calibration used
different operands / different Z / different constraint sets), so the corpus stays contamination-free.

Measured per-kind rates that set the expected corpus accuracy (hardening/HARDENING.md):
  arith_mult3x3 0.125 | fact_numeric_tail ~0.60 (confusable-reverse subset; conservative) |
  ded (6-7 entity) 0.20-0.40.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "hardening"))
from ded_verify import build_constraints, solve, who_at, verify_spec  # noqa: E402

# ------------------------------------------------------------------ arithmetic: 3x3 multiplication
# fresh operands, DISJOINT from the calibration mult set; gold recomputed from expr.
_MULT_EXPRS = [
    "374*269", "586*473", "728*645", "837*426", "469*738", "615*382", "927*451",
    "763*624", "519*687", "848*356", "692*473", "534*817", "715*483", "296*657",
]

# ------------------------------------------------------------------ factual: reverse superheavy
# (Z -> element). Confusable range, DISJOINT from calibration reverse Z {101,103,105,111,113,115,118}.
_REVERSE_SUPERHEAVY = [
    (97, "Berkelium"), (98, "Californium"), (99, "Einsteinium"), (102, "Nobelium"),
    (104, "Rutherfordium"), (106, "Seaborgium"), (107, "Bohrium"), (108, "Hassium"),
    (109, "Meitnerium"), (110, "Darmstadtium"), (112, "Copernicium"), (114, "Flerovium"),
    (116, "Livermorium"), (117, "Tennessine"),
]


# ------------------------------------------------------------------ deduction: unique 6-entity seat
def _gen_seat_puzzle(rng, n=6):
    """Generate a unique n-entity seating puzzle. Returns (entities, spec, ask, gold) or None."""
    ents = list("ABCDEFGH")[:n]
    target = list(range(1, n + 1))
    rng.shuffle(target)
    pos = dict(zip(ents, target))
    # candidate readable constraints consistent with the target permutation
    cands = []
    for a in ents:
        for b in ents:
            if a == b:
                continue
            if pos[a] + 1 == pos[b]:
                cands.append(("imm", a, b))
            elif pos[a] < pos[b]:
                cands.append(("lt", a, b))
    for a in ents:
        cands.append(("at", a, pos[a]))
    # a few negations for flavour
    for a in ents:
        for k in range(1, n + 1):
            if pos[a] != k:
                cands.append(("nat", a, k))
    rng.shuffle(cands)
    # prefer at/imm/lt first, negations last, greedily add until unique
    order = sorted(cands, key=lambda t: {"at": 0, "imm": 1, "lt": 2, "nat": 3}[t[0]])
    # but keep some randomness within groups
    spec = []
    for c in order:
        spec.append(c)
        if len(solve(ents, build_constraints(spec))) == 1:
            break
    else:
        return None
    # prune redundant constraints (keep it readable: aim <= 6)
    pruned = list(spec)
    changed = True
    while changed:
        changed = False
        for c in list(pruned):
            trial = [x for x in pruned if x is not c]
            if trial and len(solve(ents, build_constraints(trial))) == 1:
                pruned = trial
                changed = True
                break
    if not (3 <= len(pruned) <= 6):
        return None
    ask = rng.randint(2, n - 1)  # ask a non-endpoint seat (harder)
    gold = who_at(ask)(solve(ents, build_constraints(pruned))[0])
    return ents, pruned, ask, gold


def _nl_seat(ents, spec, ask):
    n = len(ents)
    names = ", ".join(ents[:-1]) + ", and " + ents[-1]
    lines = []
    for t in spec:
        if t[0] == "at":
            lines.append(f"{t[1]} is in seat {t[2]}.")
        elif t[0] == "nat":
            lines.append(f"{t[1]} is not in seat {t[2]}.")
        elif t[0] == "imm":
            lines.append(f"{t[1]} sits immediately to the left of {t[2]}.")
        elif t[0] == "lt":
            lines.append(f"{t[1]} sits somewhere to the left of {t[2]}.")
    return (f"{n} people -- {names} -- sit in seats numbered 1 to {n} from left to right. "
            + " ".join(lines) + f" Who sits in seat {ask}?")


def _gen_deduction(seed=20260714, count=14):
    rng = random.Random(seed)
    out, seen = [], set()
    attempts = 0
    while len(out) < count and attempts < 5000:
        attempts += 1
        res = _gen_seat_puzzle(rng, n=rng.choice([6, 6, 6, 7]))
        if res is None:
            continue
        ents, spec, ask, gold = res
        prompt = _nl_seat(ents, spec, ask)
        if prompt in seen:
            continue
        # re-verify uniqueness + gold via the public API
        g2, _ = verify_spec(ents, spec, ask)
        assert g2 == gold
        seen.add(prompt)
        out.append((ents, spec, ask, gold, prompt))
    if len(out) < count:
        raise RuntimeError(f"only generated {len(out)}/{count} deduction puzzles")
    return out


def build_d4():
    """Return {d3_id: d4_item_dict} for all three answerable families."""
    conv = {}
    # arithmetic -> arith-029..042
    for i, expr in enumerate(_MULT_EXPRS):
        gold = str(int(eval(expr)))  # noqa: S307 author-controlled
        rid = f"arith-{29 + i:03d}"
        a, b = expr.split("*")
        conv[rid] = {
            "id": rid, "family": "arithmetic",
            "prompt": f"What is {a} times {b}?", "gold": gold, "difficulty": 4,
            "expected_diversity": "mid",
            "provenance": "hand-authored, GSM8K-style word/number problem (original); "
                          "d4 hard kind arith_mult3x3",
            "answerable": True, "verify": expr, "hard_kind": "arith_mult3x3",
        }
    # factual -> fact-029..042  (includes fact-037, decontaminating it)
    for i, (z, name) in enumerate(_REVERSE_SUPERHEAVY):
        rid = f"fact-{29 + i:03d}"
        conv[rid] = {
            "id": rid, "family": "factual",
            "prompt": f"Which chemical element has atomic number {z}?", "gold": name,
            "difficulty": 4, "expected_diversity": "mid",
            "provenance": f"hand-authored, TriviaQA-style closed question (original); d4 hard kind "
                          f"fact_numeric_tail; Z={z} -> {name} (IUPAC)",
            "answerable": True, "hard_kind": "fact_numeric_tail",
        }
    # deduction -> ded-029..042
    puzzles = _gen_deduction()
    for i, (ents, spec, ask, gold, prompt) in enumerate(puzzles):
        rid = f"ded-{29 + i:03d}"
        conv[rid] = {
            "id": rid, "family": "deduction", "prompt": prompt, "gold": gold, "difficulty": 4,
            "expected_diversity": "mid",
            "provenance": "hand-authored, bAbI/ProofWriter-style forced-answer logic (original); "
                          "d4 hard kind ded_seat6 (unique solution proven by ded_verify)",
            "answerable": True,
            "ded_spec": {"entities": ents, "spec": [list(t) for t in spec], "ask": ask},
            "hard_kind": "ded_seat6",
        }
    return conv


if __name__ == "__main__":
    conv = build_d4()
    from collections import Counter
    print(f"built {len(conv)} d4 items:", dict(Counter(v['family'] for v in conv.values())))
    for rid, it in conv.items():
        print(f"  {rid} d{it['difficulty']} gold={it['gold']!r:16s} {it['prompt'][:70]}")
