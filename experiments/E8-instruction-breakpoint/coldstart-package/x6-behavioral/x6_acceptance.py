"""X6 real-data acceptance checks — run on the completed pilot results BEFORE trusting the verdict.

These are the instrument-validity gates (X6-DESIGN §6, X6-NOTES). A FAIL routes to X-HUMAN / withholds
the verdict; it never silently proceeds. Three checks:

  AC1  POSITIVE CONTROLS FIRED (guard B). Every task's synthetic positive control (a correct action in
       an unusual-but-valid form) must have A_correct fire. A miss means the oracle is too narrow for
       real output → the instrument cannot be trusted to detect a correct action, so FF/over counts are
       suspect. Threshold: pc_fire_rate must be 1.0 (any miss is a finding).

  AC2  FF/TT CELLS WITHIN CEILING. FF = unanticipated action (SCOPED arm); TT = non-exclusive oracle
       (construction bug on real output). Frozen ceilings: FF_rate ≤ 0.05 of SCOPED scored; TT count = 0.
       Over ceiling → the action oracles didn't anticipate the real action space → X-HUMAN adjudication
       before any verdict.

  AC3  SRD-GAP REPRODUCTION on the BLANKET arm. The BLANKET arm is our in-harness SRD control. SRD's
       verified anchor (arXiv:2604.20911): omission/requirement compliance DECAYS with turn depth for
       SRD-susceptible models (73%→33% turns 5→16), while for the immune cluster it holds ~100%. We do
       NOT assert a specific magnitude (claude-sonnet-5 was not in SRD's 12; the floor is model-specific,
       X6-NOTES §1). We assert the DIRECTION-CONSISTENCY the design relies on: the BLANKET decay rate is
       monotone NON-DECREASING across dose (decay at T1 ≤ T2 ≤ T3, tolerance TOL). This confirms the
       control behaves as an SRD-class requirement-decay measurement (either it decays with turns =
       SRD-susceptible-like, or it's flat/immune — both are valid SRD outcomes; a DECREASING curve would
       mean the control is measuring something incoherent and the paired contrast is unsound). Reports
       the observed BLANKET curve alongside SRD's anchor for the writeup, flags but does not fail on a
       flat/immune curve (that is a legitimate SRD outcome and still gives a valid δ floor).

Exit 0 iff AC1 and AC2 pass (AC3 is diagnostic/reported, non-fatal unless the curve is DECREASING beyond
tolerance, which is incoherent). Emits x6-acceptance.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from x6_verdict import aggregate, load_rows

FF_CEILING = 0.05
TT_CEILING = 0
SRD_MONOTONE_TOL = 0.02   # allow small non-monotone wobble before calling the BLANKET curve incoherent
SRD_ANCHOR = {"paper": "arXiv:2604.20911", "omission_turn5": 0.73, "omission_turn16": 0.33,
              "commission": 1.00, "note": "verified from PDF; model-specific, not a target magnitude"}


def run(rows: list) -> dict:
    agg = aggregate(rows)
    L = (1, 2, 3)

    # AC1 positive controls
    n_pc = sum(1 for r in rows if r.get("positive_control"))
    n_pc_fired = sum(1 for r in rows if (r.get("positive_control") or {}).get("fired"))
    pc_rate = (n_pc_fired / n_pc) if n_pc else 1.0
    ac1 = {"n": n_pc, "fired": n_pc_fired, "rate": round(pc_rate, 4), "pass": pc_rate >= 1.0}

    # AC2 FF/TT
    ff_total = sum(agg["ff"].values())
    tt_total = sum(agg["tt"].values())
    scoped_scored = sum(agg["scoped"][l]["trials"] for l in L) + ff_total
    ff_rate = (ff_total / scoped_scored) if scoped_scored else 0.0
    ac2 = {"ff_total": ff_total, "ff_rate": round(ff_rate, 4), "ff_ceiling": FF_CEILING,
           "tt_total": tt_total, "tt_ceiling": TT_CEILING,
           "pass": (ff_rate <= FF_CEILING and tt_total <= TT_CEILING)}

    # AC3 SRD-gap reproduction: BLANKET decay curve across dose
    decay = []
    for l in L:
        b = agg["blanket"][l]
        decay.append((b["decay"] / b["trials"]) if b["trials"] else None)
    non_decreasing = all(
        (decay[i] is None or decay[i + 1] is None or decay[i + 1] >= decay[i] - SRD_MONOTONE_TOL)
        for i in range(len(decay) - 1))
    curve_kind = ("decaying-with-turns (SRD-susceptible-like)"
                  if (decay[0] is not None and decay[2] is not None and decay[2] - decay[0] > SRD_MONOTONE_TOL)
                  else "flat/immune (SRD immune-cluster-like)")
    ac3 = {"blanket_decay_curve": [None if d is None else round(d, 4) for d in decay],
           "non_decreasing_within_tol": non_decreasing, "curve_kind": curve_kind,
           "srd_anchor": SRD_ANCHOR,
           "pass": non_decreasing,   # only a DECREASING curve is incoherent (control unsound)
           "note": "flat/immune is a valid SRD outcome (still yields a valid δ floor); only a decreasing "
                   "BLANKET curve would make the paired contrast unsound."}

    overall = ac1["pass"] and ac2["pass"] and ac3["pass"]
    return {"AC1_positive_controls": ac1, "AC2_ff_tt_cells": ac2,
            "AC3_srd_gap_reproduction": ac3,
            "overall_pass": overall,
            "verdict_gate": ("PROCEED" if overall else "WITHHOLD -> X-HUMAN")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    rows = load_rows(args.results)
    r = run(rows)
    out = json.dumps(r, indent=2)
    print(out)
    if args.out:
        args.out.write_text(out)
    sys.exit(0 if r["overall_pass"] else 2)


if __name__ == "__main__":
    main()
