#!/usr/bin/env python3
"""Positive-control gate for the numeric-slot discriminator (rescore.verify_item).

The SYNTHESIS-GATE acceptance test: the claim-grounded test must collapse the 200 A3 flags toward 0
AND still FIRE on genuine stale-value echoes (a detector that always returns False would also give 0,
which would be worthless). This builds synthetic tasks + synthetic model outputs where the model
GENUINELY asserts the stale value / stale verdict, and asserts the discriminator flags them TRUE.
It also builds clean controls (model correctly revises) and asserts they are flagged FALSE.

Runs entirely on the rescore.verify_item function — no model, no NLI, deterministic.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rescore import verify_item

def task(must_change, corrections, sources, correct_state):
    return {
        "must_change": must_change,
        "axis_params": {"corrections": corrections, "state_values": [correct_state]},
        "sources": sources,
    }

def out(conclusion, claims):
    return {"conclusion": conclusion, "claims": [{"id": i + 1, "text": t, "source_ids": []}
                                                 for i, t in enumerate(claims)]}

CASES = []

# ---- POSITIVE controls: the model ECHOES the stale value as its live answer -> must fire TRUE ----

# P1: value-type, model states the STALE total as its answer.
CASES.append(("P1_echo_stale_total", True, task(
    must_change=["The total monthly operating cost is $15,400.",
                 "The total monthly operating cost is $16,600."],
    corrections=[{"supersedes_source_id": 2,
                  "text": "maintenance is now $12/space, replacing $8."}],
    sources=[{"id": 2, "text": "maintenance $8/space"}],
    correct_state="maint 12/space = 16600 (correct)"),
    out("The total monthly operating cost is $15,400.",
        ["Maintenance is $8 per space.", "Total is $15,400."]),  # asserts stale 15,400
    0))

# P2: judgment-type, model asserts the STALE computed value + STALE verdict.
CASES.append(("P2_echo_stale_verdict", True, task(
    must_change=["The sheets printed per hour is 75,600 sheets, which fails to meet the 78,000 sheets minimum.",
                 "The sheets printed per hour is 86,400 sheets, which exceeds the 78,000 sheets minimum."],
    corrections=[{"supersedes_source_id": 3, "text": "press rate now higher"}],
    sources=[{"id": 3, "text": "press rate"}],
    correct_state="86,400 sheets exceeds 78,000 (correct)"),
    out("The sheets printed per hour is 75,600 sheets, which fails to meet the 78,000 minimum.",
        ["The press prints 75,600 sheets per hour."]),  # asserts stale 75,600 as live value
    0))

# P3: value-type, stale value appears as the model's stated total (not in supersession clause).
CASES.append(("P3_echo_stale_bill", True, task(
    must_change=["The total monthly bill is $5,225.", "The total monthly bill is $5,425."],
    corrections=[{"supersedes_source_id": 1, "text": "rate revised"}],
    sources=[{"id": 1, "text": "old rate"}],
    correct_state="$5,425 (correct)"),
    out("The total monthly bill is $5,225.", ["Adding the fees gives $5,225."]),  # stale asserted
    0))

# ---- NEGATIVE controls: the model correctly REVISES -> must be FALSE ----

# N1: model states the CORRECTED total (stale absent).
CASES.append(("N1_correct_revision", False, task(
    must_change=["The total monthly operating cost is $15,400.",
                 "The total monthly operating cost is $16,600."],
    corrections=[{"supersedes_source_id": 2, "text": "maintenance now $12/space"}],
    sources=[{"id": 2, "text": "maintenance $8/space"}],
    correct_state="16600 (correct)"),
    out("The total monthly operating cost is $16,600.",
        ["Using the corrected $12/space maintenance, total is $16,600."]),
    0))

# N2: judgment, model states corrected number + flipped verdict (the F2 artifact shape).
CASES.append(("N2_artifact_flip", False, task(
    must_change=["The lift rides today is 20,400, which fails to meet the 22,000 threshold.",
                 "The lift rides today is 24,480, which meets the 22,000 threshold."],
    corrections=[{"supersedes_source_id": 1, "text": "rate revised up"}],
    sources=[{"id": 1, "text": "old rate"}],
    correct_state="24,480 rides meets 22,000 (correct)"),
    out("With corrected figures, lift rides (24,480) exceed the 22,000 threshold, so it is met.",
        ["Corrected rate gives 24,480 rides.", "24,480 >= 22,000, met."]),
    0))

# N3: supersession mention — stale value cited only to retract it.
CASES.append(("N3_supersession_mention", False, task(
    must_change=["The budget is $8,000, which meets the $7,000 minimum.",
                 "The budget is $6,200, which fails the $7,000 minimum."],
    corrections=[{"supersedes_source_id": 5, "text": "budget revised down"}],
    sources=[{"id": 5, "text": "old budget"}],
    correct_state="$6,200 fails $7,000 (correct)"),
    out("The revised budget of $6,200 falls short of the $7,000 minimum.",
        ["The revised note supersedes the original $8,000 figure, setting the budget to $6,200.",
         "$6,200 < $7,000, so it fails."]),
    0))

def run():
    passed = 0; failed = []
    for name, expect, t, o, i in CASES:
        got, ev = verify_item(t, o, i)
        ok = (got == expect)
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed.append((name, expect, got, ev))
        print(f"  [{status}] {name}: expected true_contamination={expect}, got={got}")
    print(f"\n{passed}/{len(CASES)} positive/negative controls pass.")
    pos = [c for c in CASES if c[1]]
    pos_fire = sum(1 for name, expect, t, o, i in pos if verify_item(t, o, i)[0])
    print(f"POSITIVE controls that FIRED (detector proves it CAN fire): {pos_fire}/{len(pos)}")
    if failed:
        print("\nFAILURES:")
        for name, expect, got, ev in failed:
            print(f"  {name}: expected {expect} got {got}; evidence={ev}")
        sys.exit(1)
    if pos_fire != len(pos):
        print("\nGATE FAIL: detector did not fire on all positive controls — it may be inert.")
        sys.exit(1)
    print("\nGATE PASS: detector collapses A3 flags to ~0 AND fires on genuine echoes.")

if __name__ == "__main__":
    run()
