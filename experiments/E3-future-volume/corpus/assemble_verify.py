"""
assemble_verify.py -- the commit-grade proof that corpus/candidates.jsonl is well-formed, decontam-
inated, and correctly labeled. Re-runnable; exits non-zero on any failure. Verifies:

  1. SCHEMA    : every row has the required fields; family in the 5; difficulty in {1,2,3,4};
                 expected_diversity in {low,mid,high}; id prefix matches family; answerable ==
                 (gold is not None); open families (enumeration/creative) have gold null.
  2. COUNTS    : family totals 42/42/42/37/37; total 200; answerable subset 126; and each answerable
                 family is difficulty-CROSSED (>= 3 distinct difficulty levels present).
  3. NO DUPES  : no two corpus prompts are identical (normalized).
  4. ARITH GOLD: every item carrying a `verify` expression -> eval(verify) == the numeric gold
                 (arithmetic recomputed from scratch, never asserted). Every arithmetic item MUST
                 carry `verify` (total recompute coverage).
  5. DED GOLD  : every item carrying a `ded_spec` -> ded_verify proves a UNIQUE solution and its
                 seat==gold (deduction re-derived by brute force).
  6. DECONTAM  : ZERO contamination hits vs corpus/DISPOSABLE-MANIFEST.jsonl (decontaminate.audit);
                 reports the global max token-Jaccard (the residual generic-frame ceiling).

Usage:  python assemble_verify.py   (stdlib only; imports ded_verify from ../hardening)
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "hardening"))
CANDIDATES = HERE / "candidates.jsonl"

import decontaminate  # noqa: E402
from ded_verify import verify_spec  # noqa: E402

FAMILIES = {"arithmetic", "factual", "deduction", "enumeration", "creative"}
OPEN_FAMILIES = {"enumeration", "creative"}
PREFIX = {"arithmetic": "arith", "factual": "fact", "deduction": "ded",
          "enumeration": "enum", "creative": "crea"}
EXPECTED_COUNTS = {"arithmetic": 42, "factual": 42, "deduction": 42,
                   "enumeration": 37, "creative": 37}
REQUIRED = {"id", "family", "prompt", "gold", "difficulty", "expected_diversity",
            "provenance", "answerable"}


class V:
    def __init__(self):
        self.fail = []
        self.ok = []

    def check(self, cond, msg):
        (self.ok if cond else self.fail).append(msg)
        return cond


def load():
    return [json.loads(l) for l in CANDIDATES.read_text().splitlines() if l.strip()]


def main():
    rows = load()
    v = V()

    # 1. schema
    schema_bad = 0
    for r in rows:
        miss = REQUIRED - set(r)
        if miss:
            schema_bad += 1
            v.fail.append(f"{r.get('id','?')}: missing fields {miss}")
            continue
        fam = r["family"]
        if fam not in FAMILIES:
            schema_bad += 1; v.fail.append(f"{r['id']}: bad family {fam}")
        if r["difficulty"] not in (1, 2, 3, 4):
            schema_bad += 1; v.fail.append(f"{r['id']}: bad difficulty {r['difficulty']}")
        if r["expected_diversity"] not in ("low", "mid", "high"):
            schema_bad += 1; v.fail.append(f"{r['id']}: bad expected_diversity")
        if not r["id"].startswith(PREFIX.get(fam, "?")):
            schema_bad += 1; v.fail.append(f"{r['id']}: id prefix != family {fam}")
        if (r["gold"] is None) != (fam in OPEN_FAMILIES):
            schema_bad += 1
            v.fail.append(f"{r['id']}: gold/openness mismatch (gold={r['gold']!r}, fam={fam})")
        if r["answerable"] != (r["gold"] is not None):
            schema_bad += 1; v.fail.append(f"{r['id']}: answerable != (gold is not None)")
    v.check(schema_bad == 0, f"schema: {len(rows)-schema_bad}/{len(rows)} rows valid")

    # 2. counts + difficulty-crossed
    by_fam = Counter(r["family"] for r in rows)
    v.check(dict(by_fam) == EXPECTED_COUNTS, f"family counts {dict(by_fam)} == {EXPECTED_COUNTS}")
    v.check(len(rows) == 200, f"total rows == 200 (got {len(rows)})")
    answerable = [r for r in rows if r["answerable"]]
    v.check(len(answerable) == 126, f"answerable subset == 126 (got {len(answerable)})")
    for fam in ("arithmetic", "factual", "deduction"):
        diffs = {r["difficulty"] for r in rows if r["family"] == fam}
        v.check(len(diffs) >= 3, f"{fam} difficulty-crossed: {sorted(diffs)} (>=3 levels)")

    # 3. no duplicate prompts
    norm = [re.sub(r"\s+", " ", r["prompt"].strip().lower()) for r in rows]
    dupes = [p for p, c in Counter(norm).items() if c > 1]
    v.check(not dupes, f"no duplicate prompts (found {len(dupes)})")
    if dupes:
        for d in dupes[:5]:
            v.fail.append(f"  dup prompt: {d!r}")

    # 4. arithmetic gold recompute (+ any verify-carrying item)
    arith_missing = [r["id"] for r in rows if r["family"] == "arithmetic" and "verify" not in r]
    v.check(not arith_missing,
            f"every arithmetic item carries `verify` ({len(arith_missing)} missing)")
    bad_gold = []
    n_verified = 0
    for r in rows:
        if "verify" in r:
            n_verified += 1
            got = eval(r["verify"])  # noqa: S307 -- corpus-authored expressions only
            want = float(re.sub(r"[^0-9.\-]", "", str(r["gold"])))
            if abs(float(got) - want) > 1e-9:
                bad_gold.append(f"{r['id']}: verify {r['verify']} -> {got} != gold {r['gold']}")
    v.check(not bad_gold, f"gold recompute: {n_verified} items, {len(bad_gold)} mismatches")
    v.fail.extend(bad_gold)

    # 5. deduction gold re-derivation
    ded_bad = []
    n_ded = 0
    for r in rows:
        if "ded_spec" in r:
            n_ded += 1
            spec = r["ded_spec"]
            tuples = [tuple(t) for t in spec["spec"]]
            try:
                gold, _ = verify_spec(spec["entities"], tuples, spec["ask"])
                if gold != r["gold"]:
                    ded_bad.append(f"{r['id']}: derived {gold} != gold {r['gold']}")
            except AssertionError as e:
                ded_bad.append(f"{r['id']}: {e}")
    v.check(not ded_bad, f"deduction re-derivation: {n_ded} puzzles, {len(ded_bad)} bad")
    v.fail.extend(ded_bad)

    # 6. decontamination
    hits, (gmax, gpair) = decontaminate.audit(rows)
    v.check(not hits, f"decontamination: {len(hits)} contamination hits vs disposable manifest")
    for h in hits[:10]:
        v.fail.append(f"  contaminated {h[0]}: {h[2]} vs [{h[5]}] {h[6]!r}")

    # report
    print("=== assemble_verify ===")
    for m in v.ok:
        print(f"  PASS  {m}")
    print(f"  INFO  global max token-Jaccard vs disposable = {gmax:.3f}")
    if gpair:
        print(f"        argmax: {gpair[0]} {gpair[1]!r}")
        print(f"                vs [{gpair[2]}] {gpair[3]!r}")
    print(f"  INFO  difficulty distribution: {dict(Counter(r['difficulty'] for r in rows))}")
    print(f"  INFO  d4 hard items: {sum(1 for r in rows if r['difficulty'] == 4)} "
          f"({dict(Counter(r['hard_kind'] for r in rows if r.get('hard_kind')))})")
    if v.fail:
        print(f"\n  {len(v.fail)} FAILURE(S):")
        for m in v.fail:
            print(f"  FAIL  {m}")
        print("\nRESULT: FAIL")
        sys.exit(1)
    print("\nRESULT: PASS")


if __name__ == "__main__":
    main()
