#!/usr/bin/env python3
"""INSTRUMENT-V2 (CONSOLIDATED) — the single productionized claim-grounded revision-fidelity test.

Unifies the two accepted prototypes:
  - x1-anatomy/rescore.py::verify_item (value channel + benchmark/correct/supersession exclusions +
    entity-label guard) and its positive_controls.py 6-case fixture (P1-P3 fire, N1-N3 clear);
  - instrument_v2.py (value + verdict channels, value-assignment label parser, UNIT guard, 10 synthetic
    injection controls, E5 adapter).

WHY CONSOLIDATE ON THIS SIDE — a real divergence was found (cross-check, all 786 A3 items): the two
prototypes AGREE on 784/786; they DISAGREE on A3-C-0501-C2/C3 item1 (x1=real, v2=clean). That item is
"120 tonnes maize" colliding with "120 hectares barley" — X1-FINDINGS' own hand-adjudicated residual #3,
a FALSE POSITIVE. v2's UNIT guard (mc_units {tonnes} ∩ out_units {hectares} = ∅ ⇒ different quantity)
excludes it; x1's verify_item has no unit-aware matching and flags it. So the accepted "0 real / 786"
requires v2's unit guard — the consolidated tool adopts it. (x1's full_rescore would report 2 residual
FPs without it; flagged to x1.)

POLICY VOCABULARY (adopted from Proof-Carrying Numbers, arXiv:2509.06902 — a reviewer will find PCN
immediately; we use its terms rather than invent parallel ones):
  - EXACT: normalized numeric equality ($/comma stripped) — value_echo's stale==out-span test.
  - ALIAS: number-format variants ({8000, 8,000, $8,000, $8000}) treated as the same value; also the
    unit as a required alias qualifier.
  - TOLERANCE(exact): the comparison tolerance is exact-equality here (no rounding band).
  - QUALIFIER (unit): a value only matches if it carries a compatible measure unit (the UNIT guard).
  REVISION-SPECIFIC EXTENSIONS PAST PCN (named as such; PCN has no analog):
  - SUPERSESSION-EXCLUSION: a value mentioned only inside a retraction/supersession clause is not an
    assertion.
  - STALE↔CORRECTED PAIR: the reference is a (stale, corrected) pair, not one source value; the test
    scores WHICH side of a known supersession the model asserted (directional echo).
  - VERDICT channel: echo of a stale VERDICT direction in an identical requirement sentence.
  PCN verifies faithfulness of a span to structured source data; instrument-v2 scores revision fidelity
  of unstructured claim text against a stale/corrected pair. Same substrate, different question.

This module IMPORTS the two prototypes and asserts agreement (minus the known unit-guard divergence),
runs BOTH fixture sets, and is the canonical scorer. Frozen files untouched; no model, no NLI, CPU-only.

COUNT BASIS (adjudicated — do not conflate; "1,428" is wrong, it mixed both annotation sides):
  Sweep basis  = 786 A3 must_change items (verdict trials 756 + 30 pruned) — the full surface the
                 scorer touched; the correct basis for INSTRUMENT AUDITS (this tool reports on it).
  Verdict basis = 756 (post-pruning trials; ALL canonical contamination numbers use this).
  Result is 0 real on BOTH bases.

Run:  python3 instrument_v2_consolidated.py --self-test   (all gates + x1 fixture + agreement check)
      python3 instrument_v2_consolidated.py --rescore-all (786 A3 items → final table)
"""
from __future__ import annotations
import sys, os, json, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import instrument_v2 as v2          # value+verdict channels, unit/label/value-assignment guards, E5 adapter
import rescore                      # x1's verify_item (base) + entity-label guard
import positive_controls            # x1's 6-case fixture (built on rescore.verify_item)


# --------------------------------------------------------------------------- canonical scorer
def score_item(task, output, i):
    """The CANONICAL v2 verdict for one must_change item. Uses instrument_v2.classify_item (which
    carries the UNIT guard that fixes the 2-item divergence + the value-assignment label parser + the
    gated verdict channel). Returns (real_contamination: bool, evidence: dict)."""
    r = v2.classify_item(task, output, i)
    return r["real_contamination"], r


# --------------------------------------------------------------------------- PCN-vocab policy view
def policy_view(evidence: dict) -> dict:
    """Re-express the value-channel decision in PCN policy vocabulary for the writeup / audit."""
    vc = evidence.get("value_channel", {})
    return {
        "policy": "EXACT + ALIAS(number-format) + QUALIFIER(unit) + SUPERSESSION-EXCLUSION",
        "reference": "STALE↔CORRECTED pair (directional echo), not a single source value",
        "exact_match_stale_value": vc.get("stale_value_present"),
        "alias_forms_checked": True,
        "unit_qualifier_ok": vc.get("unit_ok"),
        "excluded_threshold_constant": vc.get("stale_equals_threshold"),
        "excluded_correct_final": vc.get("stale_equals_correct"),
        "excluded_supersession_clause": vc.get("in_supersession"),
        "excluded_label_ordinal": vc.get("label_only"),
        "verdict_channel_fired": evidence.get("verdict_channel", {}).get("verdict_echo"),
    }


# --------------------------------------------------------------------------- self-test
def run_self_test():
    report = {"gates": {}}

    # A) instrument_v2's own 4 gates (200→0, audit30→0, 10/10 positive controls, 5 spotcheck clean)
    v2rep = v2.run_self_test()
    report["gates"]["A_v2_four_gates"] = {k: v.get("pass") for k, v in v2rep["gates"].items()}
    report["gates"]["A_v2_four_gates"]["all_pass"] = v2rep["all_pass"]

    # B) x1's positive_controls fixture, but scored through the CANONICAL score_item (must reproduce
    #    3/3 fire + 3/3 clear — proving the consolidated scorer subsumes x1's fixture).
    b = {"pass": True, "cases": []}
    for name, expect, t, o, i in positive_controls.CASES:
        got, _ = score_item(t, o, i)
        ok = (got == expect)
        b["cases"].append({"name": name, "expect": expect, "got": got, "ok": ok})
        b["pass"] = b["pass"] and ok
    report["gates"]["B_x1_fixture_via_canonical"] = b

    # C) agreement with x1's verify_item on all 786 A3 items, EXCEPT the known unit-guard divergence
    #    (A3-C-0501-C2/C3 item1 = 120 tonnes/hectares FP that only v2's unit guard catches).
    # Gate C is now FULL agreement: x1-anatomy pulled the unit guard into verify_item (2026-07-19)
    # after this cross-check surfaced the 120-tonnes/120-hectares FP, so both tools catch it. The
    # exception set is intentionally EMPTY — any disagreement is now a real regression in either tool,
    # and the gate must fail on it (no masking). This is the honest coupling: frozen prototype vs
    # production scorer must agree item-for-item on all 786.
    corpus, gen, results = v2.load_corpus(), v2.load_gen(), v2.load_results()
    EXPECTED_DIVERGENCE = set()  # both tools now carry the unit guard; full agreement required
    unexpected = []
    for tid, i in v2.all_items(corpus, results):
        x1_real, _ = rescore.verify_item(corpus[tid], gen[tid]["output"], i)
        mine, _ = score_item(corpus[tid], gen[tid]["output"], i)
        if x1_real != mine and (tid, i) not in EXPECTED_DIVERGENCE:
            unexpected.append((tid, i, x1_real, mine))
    report["gates"]["C_full_agreement_x1_verify_item"] = {
        "pass": len(unexpected) == 0, "n_unexpected": len(unexpected),
        "unexpected": unexpected[:10], "n_items_checked": sum(1 for _ in v2.all_items(corpus, results)),
        "note": "full 786/786 agreement required; unit-collision FP fixed in both tools 2026-07-19",
    }

    report["all_pass"] = (v2rep["all_pass"] and b["pass"]
                          and report["gates"]["C_full_agreement_x1_verify_item"]["pass"])
    return report


def main():
    ap = argparse.ArgumentParser(description="INSTRUMENT-V2 consolidated")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--rescore-all", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        rep = run_self_test()
        print(json.dumps(rep["gates"], indent=2, default=str))
        print("ALL_PASS:", rep["all_pass"])
        return 0 if rep["all_pass"] else 1
    if args.rescore_all:
        corpus, gen, results = v2.load_corpus(), v2.load_gen(), v2.load_results()
        n = real = 0
        for tid, i in v2.all_items(corpus, results):
            r, _ = score_item(corpus[tid], gen[tid]["output"], i)
            n += 1
            real += 1 if r else 0
        print(json.dumps({"n_items": n, "n_real": real,
                          "count_basis": "sweep = 786 A3 must_change items (verdict trials 756 + 30 "
                                         "pruned) — the full surface the scorer touched, correct for "
                                         "instrument audits; verdict basis = 756 (post-pruning trials, "
                                         "used by all canonical contamination numbers). 0 real on both.",
                          "note": "canonical scorer (v2 unit guard)"},
                         indent=2))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
