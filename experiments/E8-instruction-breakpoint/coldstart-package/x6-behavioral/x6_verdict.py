"""X6 verdict aggregator — deterministic, no model (X6-DESIGN §6, X6-PROTOTYPE-SPEC §D).

Consumes trajectory-result JSONL (one row per task-instance, shape below), re-derives the oracle
booleans as a cross-check (independent_recompute discipline), applies the guard-D conditioning, and
computes the X6 break: SCOPED over-generalization rate p_over rising monotonically + crossing θ AND
exceeding the BLANKET decay rate p_decay by the frozen separation margin δ (paired per-family
permutation contrast). Imports the frozen stats VERBATIM from closure_harness.stats — never
re-implements them (the verdict_compute.py rule).

Result-row shape (produced by x6_generate.py; hand-authorable for the toy test):
  {task_id, family_id, arm: "SCOPED"|"BLANKET", dose_level: 1|2|3,
   scored_cases: [ {case_id, cls: "EXCEPTED"|"RULE"|"NEW", A_correct, A_wrong,
                    emitted: <str|number>,        # the agent's field-write for this case
                    a_correct_fired: bool, a_wrong_fired: bool} ],   # from capture; re-derived here
   positive_control: {target, emitted, fired: bool} }

Cells: TF=correct, FT=over-generalization (break numerator), FF=diagnostic (unanticipated), TT=bug.
FF/TT are NEVER counted; they route to X-HUMAN via the report's flags.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from x6_normalize import canonical_eq, canonical_scalar, Unparseable

# frozen thresholds — θ and δ are PILOT-MEASURED, not assumed (X6-NOTES §1). Placeholders here for
# the toy/self-test; the real run passes them in after the pilot fixes them.
DEFAULT_THETA = 0.10          # crossing threshold for p_over (top level); pilot-fixed
DEFAULT_DELTA = 0.05          # separation margin p_over - p_decay; pilot-fixed from BLANKET noise band
DOSE_LEVELS = (1, 2, 3)


def cell(a_correct: bool, a_wrong: bool) -> str:
    return {(True, False): "TF", (False, True): "FT",
            (False, False): "FF", (True, True): "TT"}[(bool(a_correct), bool(a_wrong))]


def rederive(sc: dict) -> tuple[bool, bool]:
    """Independent re-derivation of (a_correct_fired, a_wrong_fired) from emitted + oracle targets.
    a_wrong target None (BLANKET) => a_wrong is always False (no specific wrong scalar; the break on
    BLANKET is simply NOT a_correct)."""
    emitted = sc.get("emitted")
    ac = canonical_eq(emitted, sc["A_correct"])
    aw = False if sc.get("A_wrong") is None else canonical_eq(emitted, sc["A_wrong"])
    return ac, aw


def load_rows(path: Path) -> list:
    return [json.loads(l) for l in open(path) if l.strip()]


def aggregate(rows: list) -> dict:
    """Returns per-arm, per-dose counts + guard-D conditioning + FF/TT diagnostics.

    SCOPED break event on RULE/NEW = FT, conditioned on the trajectory retaining the exception
    (its EXCEPTED case scored TF). BLANKET decay = 1 - correct_rate on RULE/NEW (SRD commission decay).
    """
    # index rows by (family, arm, dose) — each row is one task-instance with its scored cases.
    # guard D: per SCOPED row, did the EXCEPTED case score TF? that gates its RULE/NEW break events.
    cross_mismatch = []            # rows where capture booleans != re-derived (fail loud)
    scoped = {L: {"over": 0, "trials": 0} for L in DOSE_LEVELS}   # FT / (TF+FT) on RULE|NEW, retained
    blanket = {L: {"decay": 0, "trials": 0} for L in DOSE_LEVELS}  # (1-correct) on RULE|NEW
    ff = {L: 0 for L in DOSE_LEVELS}
    tt = {L: 0 for L in DOSE_LEVELS}
    excepted_lost = {L: 0 for L in DOSE_LEVELS}                    # guard-D stratum (not counted)
    pc_fail = 0
    # per-family paired contrast at top level (permutation): collect family -> (over_top, decay_top)
    fam_scoped_top = {}
    fam_blanket_top = {}

    for r in rows:
        L = r.get("dose_level")
        arm = r.get("arm")
        # positive control (guard B): must fire; a failure flags the row's oracle as too narrow
        pc = r.get("positive_control") or {}
        if pc:
            pc_ok = canonical_eq(pc.get("emitted"), pc.get("target"))
            if not pc_ok:
                pc_fail += 1
        # re-derive every scored case, cross-check against capture booleans
        cells = {}
        excepted_ok = None
        for sc in r.get("scored_cases", []):
            ac, aw = rederive(sc)
            cap_ac = sc.get("a_correct_fired")
            cap_aw = sc.get("a_wrong_fired")
            if cap_ac is not None and (bool(cap_ac) != ac or bool(cap_aw) != aw):
                cross_mismatch.append({"task_id": r.get("task_id"), "case_id": sc.get("case_id"),
                                       "capture": [cap_ac, cap_aw], "rederived": [ac, aw]})
            cl = cell(ac, aw)
            cells.setdefault(sc["cls"], []).append(cl)
            if sc["cls"] == "EXCEPTED":
                excepted_ok = (cl == "TF")

        if arm == "SCOPED":
            retained = (excepted_ok is True)   # guard D: only count when the exception was retained
            if not retained:
                excepted_lost[L] += 1
            for cls in ("RULE", "NEW"):
                for cl in cells.get(cls, []):
                    if cl == "FF":
                        ff[L] += 1; continue
                    if cl == "TT":
                        tt[L] += 1; continue
                    if not retained:
                        continue
                    scoped[L]["trials"] += 1
                    if cl == "FT":
                        scoped[L]["over"] += 1
                        fam_scoped_top.setdefault((r["family_id"], L), [0, 0])
            # accumulate family top-level over-rate
            if L == 3 and retained:
                acc = fam_scoped_top.setdefault((r["family_id"], 3), [0, 0])
                for cls in ("RULE", "NEW"):
                    for cl in cells.get(cls, []):
                        if cl in ("TF", "FT"):
                            acc[1] += 1
                            if cl == "FT":
                                acc[0] += 1
        else:  # BLANKET — SRD commission-decay: the ONLY question is "did the agent apply the rule?"
            # A_wrong is None here, so cells are only TF (correct) or FF (anything else). Both count as
            # trials; NOT-correct (FF included) is a decay event. FF is NOT a diagnostic in this arm —
            # any non-rule action is a requirement-decay, exactly SRD's commission-failure definition.
            for cls in ("RULE", "NEW"):
                for cl in cells.get(cls, []):
                    blanket[L]["trials"] += 1
                    decayed = (cl != "TF")
                    if decayed:
                        blanket[L]["decay"] += 1
                    if L == 3:
                        acc = fam_blanket_top.setdefault((r["family_id"], 3), [0, 0])
                        acc[1] += 1
                        if decayed:
                            acc[0] += 1

    return {"scoped": scoped, "blanket": blanket, "ff": ff, "tt": tt,
            "excepted_lost": excepted_lost, "pc_fail": pc_fail,
            "cross_mismatch": cross_mismatch,
            "fam_scoped_top": fam_scoped_top, "fam_blanket_top": fam_blanket_top}


def paired_permutation(fam_scoped_top: dict, fam_blanket_top: dict, n_perm: int = 10000,
                       seed: int = 20260719) -> dict:
    """Per-family paired contrast of top-level over-rate (SCOPED) vs decay-rate (BLANKET).
    Statistic = mean over families of (over_rate - decay_rate). Permutation flips the sign of each
    family's difference (paired sign-flip test). Returns observed diff + one-sided p (diff>0)."""
    fams = sorted({f for (f, L) in fam_scoped_top} & {f for (f, L) in fam_blanket_top})
    diffs = []
    for f in fams:
        so, st = fam_scoped_top[(f, 3)]
        bo, bt = fam_blanket_top[(f, 3)]
        if st == 0 or bt == 0:
            continue
        diffs.append(so / st - bo / bt)
    if not diffs:
        return {"n_families": 0, "observed_diff": None, "p_value": None}
    obs = sum(diffs) / len(diffs)
    rng = random.Random(seed)
    ge = 0
    for _ in range(n_perm):
        s = sum(d if rng.random() < 0.5 else -d for d in diffs) / len(diffs)
        if s >= obs:
            ge += 1
    return {"n_families": len(diffs), "observed_diff": obs, "p_value": ge / n_perm}


def compute_verdict(rows: list, theta: float, delta: float, alpha_axes: int = 1) -> dict:
    from closure_harness.stats import monotonicity_gate, exact_binomial_crossing, bonferroni_alpha
    agg = aggregate(rows)
    alpha = bonferroni_alpha(axis_count=alpha_axes)  # X6 is 1 axis in this study; frozen at run time

    over_counts = [agg["scoped"][L]["over"] for L in DOSE_LEVELS]
    over_trials = [agg["scoped"][L]["trials"] for L in DOSE_LEVELS]
    decay_counts = [agg["blanket"][L]["decay"] for L in DOSE_LEVELS]
    decay_trials = [agg["blanket"][L]["trials"] for L in DOSE_LEVELS]

    status = "SCORED"
    withhold = []
    if agg["cross_mismatch"]:
        status = "WITHHELD"; withhold.append(f"cross_recompute_mismatch({len(agg['cross_mismatch'])})")
    if agg["pc_fail"]:
        withhold.append(f"positive_control_fail({agg['pc_fail']})")
    total_ff = sum(agg["ff"].values()); total_tt = sum(agg["tt"].values())
    if total_tt:
        status = "WITHHELD"; withhold.append(f"TT_present({total_tt})")   # construction bug on real output
    # FF ceiling (frozen 5% of scored) → X-HUMAN
    scored_total = sum(over_trials) + total_ff
    ff_rate = total_ff / scored_total if scored_total else 0.0
    if ff_rate > 0.05:
        withhold.append(f"FF_rate_over_ceiling({ff_rate:.3f})")

    mono = crossing = None
    p_over_top = p_decay_top = None
    if all(t > 0 for t in over_trials):
        m = monotonicity_gate(over_counts, over_trials)
        mono = {"z": m.z, "rates": list(m.rates), "ca_uptrend": m.ca_uptrend,
                "strict_rise": m.strict_rise, "gate_pass": m.gate_pass}
        cr = exact_binomial_crossing(over_counts[2], over_trials[2], theta, alpha)
        crossing = {"p_hat": cr.p_hat, "crossed": cr.crossed, "critical_count": cr.critical_count,
                    "threshold": theta, "alpha": alpha}
        p_over_top = over_counts[2] / over_trials[2]
    if decay_trials[2] > 0:
        p_decay_top = decay_counts[2] / decay_trials[2]

    paired = paired_permutation(agg["fam_scoped_top"], agg["fam_blanket_top"])

    # X6 break: mono gate pass AND crossing AND separation (p_over - p_decay >= delta, paired sig)
    separation_ok = (p_over_top is not None and p_decay_top is not None
                     and (p_over_top - p_decay_top) >= delta
                     and paired.get("p_value") is not None and paired["p_value"] < alpha)
    break_verdict = None
    if status == "SCORED" and not withhold and mono and crossing:
        gate = mono["gate_pass"] and crossing["crossed"]
        if gate and separation_ok:
            break_verdict = "SCOPE_LEAK"          # separable scoped-exception break
        elif gate and not separation_ok:
            break_verdict = "DEGRADES_BUT_NOT_SEPARABLE"   # collapses to SRD-class decay
        else:
            break_verdict = "NO_BREAK"

    return {
        "status": status, "withhold_reasons": withhold,
        "theta": theta, "delta": delta, "alpha": alpha,
        "scoped_per_dose": {str(L): {"over": agg["scoped"][L]["over"], "trials": agg["scoped"][L]["trials"],
                                     "rate": (agg["scoped"][L]["over"]/agg["scoped"][L]["trials"]
                                              if agg["scoped"][L]["trials"] else None)} for L in DOSE_LEVELS},
        "blanket_per_dose": {str(L): {"decay": agg["blanket"][L]["decay"], "trials": agg["blanket"][L]["trials"],
                                      "rate": (agg["blanket"][L]["decay"]/agg["blanket"][L]["trials"]
                                               if agg["blanket"][L]["trials"] else None)} for L in DOSE_LEVELS},
        "p_over_top": p_over_top, "p_decay_top": p_decay_top,
        "monotonicity": mono, "crossing": crossing, "paired_contrast": paired,
        "separation_ok": separation_ok, "break_verdict": break_verdict,
        "diagnostics": {"FF": agg["ff"], "TT": agg["tt"], "FF_rate": ff_rate,
                        "excepted_lost": agg["excepted_lost"], "pc_fail": agg["pc_fail"],
                        "cross_mismatch": len(agg["cross_mismatch"])},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--theta", type=float, default=DEFAULT_THETA)
    ap.add_argument("--delta", type=float, default=DEFAULT_DELTA)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    rows = load_rows(args.results)
    v = compute_verdict(rows, args.theta, args.delta)
    out = json.dumps(v, indent=2)
    print(out)
    if args.out:
        args.out.write_text(out)


if __name__ == "__main__":
    main()
