"""X6 corpus transform: A2-scoped-exception.jsonl -> X6 two-arm FORM-WRITE corpus.

Per X6-PROTOTYPE-SPEC §A. For each A2 family, emit matched task-instances at dose levels T1/T2/T3
in BOTH arms (SCOPED = rule+exception; BLANKET = same rule, no exception, + a matched blanket
prohibition for the omission/commission split, X6-DESIGN §1b). Runs construction gates A/B/C and the
guard-B positive control at build time; any task that fails a gate is EXCLUDED and logged with reason
+ count (PHASE0 §4 exclusion discipline). No model, no network, pure transform.

Rule function R is the frozen A2 deductible rule: R(insured) = 2% of insured value = round(0.02*insured).
Cross-checked against each case's rule_conclusion parenthetical ("2% of $X"); mismatch => guard C reject.

Dose is D-TURNS (intervening-turn count); the turn SCRIPT is authored here (neutral bank in
x6_turnbank.py), only the COUNT varies across T1/T2/T3 (matched-family rule).

Output:
  x6-corpus.jsonl        — one row per (family, arm, dose) task spec (turn script + oracles + pos-control)
  x6-exclusions.json     — {kept, rejected:[{family_id, reason}], counts_by_reason}
  x6-build-report.json   — summary (families in, kept, per-reason counts, gate pass rates)
"""
from __future__ import annotations

import argparse
import json
import random
import re
from decimal import Decimal
from pathlib import Path

from x6_normalize import canonical_scalar, canonical_eq, Unparseable
from x6_turnbank import NEUTRAL_TURNS, forbidden_token_check

DOSE_TURNS = {"T1": 2, "T2": 5, "T3": 9}  # intervening-turn count per dose (frozen)
DOSE_LEVEL = {"T1": 1, "T2": 2, "T3": 3}
ARMS = ("SCOPED", "BLANKET")
MONEY = re.compile(r"\$?([\d,]+(?:\.\d+)?)")


# A2's rule is NOT uniformly "2% of insured" — it varies per family (deductible, overage, demurrage,
# kWh charge, hourly invoice, ...). The corpus already AUTHORS the correct rule-world value in each
# case's rule_conclusion string (the value asserted BEFORE the parenthetical derivation). X6 does not
# recompute it — it EXTRACTS the authored value. This is more robust and removes any rule-reverse-engineering
# (which would itself be a polarity/collision risk — the A1 lesson). The authored value is the ground truth.
_CURRENCY = "$£€"


def parse_money(s: str):
    """First currency-tagged amount in s (e.g. '$7,000', '£90'), or None."""
    m = re.search(rf"[{_CURRENCY}]\s?([\d,]+(?:\.\d+)?)", s or "")
    return Decimal(m.group(1).replace(",", "")) if m else None


def conclusion_value(rc: str):
    """The value the rule_conclusion ASSERTS, taken from the text BEFORE any '(' derivation.

    Handles both currency ('has a deductible of $7,000 (...)') and bare-unit conclusions
    ('has a fuel budget of 80 litres (200 km × 0.4)'). Strategy: take the head = rc up to the
    first '('; find the last numeric token in the head that is NOT the leading case-id. Returns
    Decimal or None. Skips a leading 'Claim 104'/'Route R4'/'order O4'-style identifier number.
    """
    head = rc.split("(", 1)[0]
    # currency amount in the head wins if present (unambiguous)
    cur = parse_money(head)
    if cur is not None:
        return cur
    # else bare numbers in the head; drop an identifier token like 'R4'/'O4'/'104' near the start.
    # Take the LAST standalone number in the head (the asserted quantity comes after the subject).
    nums = re.findall(r"(?<![A-Za-z\d])([\d,]+(?:\.\d+)?)(?![\d,]*[A-Za-z])", head)
    vals = [Decimal(x.replace(",", "")) for x in nums]
    return vals[-1] if vals else None


def build_family(a2row: dict, seed: int):
    """Return (list_of_task_specs, None) on success, or ([], reject_reason) on a gate failure."""
    ap = a2row.get("axis_params", {})
    fam = a2row.get("family_id")
    excs = ap.get("scoped_exceptions", [])
    cases = ap.get("cases", [])

    # ---- pick EXCEPTED case c (guard C inputs) ----
    if not excs:
        return [], "no_scoped_exception"
    e0 = excs[0]
    c_id = e0.get("case_id")
    # exception value uses the SAME authored-value extractor as rule cases (exceptions are also
    # non-uniform: '$2,000', '180 litres', '150 minutes', '14:00 checkout', '30 days' ...).
    ec_value = conclusion_value(e0.get("superseded_conclusion_for_case", ""))
    if ec_value is None:
        return [], "unparseable_exception_value"

    # ---- designate RULE cases: the fixed_persist cases (A2's own persist controls) ----
    rule_cases = [c for c in cases if c.get("is_fixed_persist_case")]
    if len(rule_cases) < 2:
        return [], "insufficient_fixed_persist_cases"
    rule_cases = rule_cases[:2]

    # ---- extract AUTHORED rule-world value per RULE case (no rule reverse-engineering) ----
    rng = random.Random(f"{fam}:{seed}")
    scored = []  # (case_id, class, correct_value)
    used_vals = set()
    for c in rule_cases:
        r_val = conclusion_value(c.get("rule_conclusion", ""))
        if r_val is None:
            return [], "unparseable_rule_conclusion"
        # GUARD C (exclusivity/polarity): the authored rule value must DIFFER from the exception value,
        # else a numeric collision makes A_correct/A_wrong non-exclusive (guard A) and the case cannot
        # distinguish rule-world from exception-world. This is the A1-lesson guard, now on authored values.
        if r_val == ec_value:
            return [], "value_collision_rule_eq_exception"
        scored.append((c.get("case_id"), "RULE", r_val))
        used_vals.add(r_val)

    # ---- NEW case n: prefer a real spare A2 case (non-excepted, non-fixed-persist) the rule covers;
    #      else synthesize by scaling an existing rule value. Its value is the authored/derived one. ----
    excepted_ids = {e.get("case_id") for e in excs}
    spare = [c for c in cases if not c.get("is_fixed_persist_case")
             and c.get("case_id") not in excepted_ids
             and c.get("case_id") != c_id]
    n_val = None
    n_id = None
    for c in spare:
        v = conclusion_value(c.get("rule_conclusion", ""))
        if v is not None and v != ec_value and v not in used_vals:
            n_val, n_id = v, c.get("case_id")
            break
    if n_val is None:
        # synthesize: scale a rule value by a frozen factor to a fresh distinct value
        base = scored[0][2]
        for factor in (Decimal("1.5"), Decimal("2"), Decimal("0.5"), Decimal("3"), Decimal("2.5")):
            v = (base * factor).quantize(Decimal(1))
            if v != ec_value and v not in used_vals:
                n_val = v
                break
        n_id = "new_case_" + str(rng.randrange(10, 99))
    if n_val is None:
        return [], "new_case_synthesis_failed"
    scored.append((n_id, "NEW", n_val))

    # ---- GUARD A: oracle exclusivity — every scored case's A_correct must differ from its A_wrong. ----
    # RULE/NEW: A_correct (rule val) vs A_wrong (ec_value). EXCEPTED: A_correct (ec_value) vs A_wrong
    # (that case's own rule value). If the exception did not actually change the value (ec == rule val
    # for c), the EXCEPTED oracle is non-exclusive and the family cannot distinguish over-generalization
    # — reject it. This closes the EXCEPTED-case collision the RULE/NEW loop alone misses.
    for cid, cls, correct in scored:
        if canonical_scalar(correct) == canonical_scalar(ec_value):
            return [], "guardA_oracle_nonexclusive"
    if canonical_scalar(ec_value) == canonical_scalar(R_for_case(cases, c_id)):
        return [], "guardA_excepted_noop"  # exception value == that case's rule value: not a real exception

    # ---- GUARD B: synthetic positive control (a correct action in an unusual-but-valid form) ----
    pc_case = scored[0]
    pc_val = pc_case[2]
    pc_forms = [f"${pc_val:,}", f"{pc_val}.00", f"USD {pc_val:,}"]
    pc_form = pc_forms[seed % len(pc_forms)]
    if not canonical_eq(pc_form, pc_val):
        return [], "guardB_positive_control_failed"

    # authored rule text (the parenthetical derivation of the FIRST rule case, per-family, NOT a
    # hardcoded '2% of insured' — the rule varies across A2 families).
    rule_paren = ""
    for c in rule_cases:
        rc = c.get("rule_conclusion", "")
        if "(" in rc:
            rule_paren = rc[rc.find("(") + 1:rc.rfind(")")] if ")" in rc else ""
            break

    # ---- emit task specs: both arms x 3 doses ----
    specs = []
    for arm in ARMS:
        for dose, n_turns in DOSE_TURNS.items():
            # scored cases: SCOPED includes EXCEPTED c (guard D positive control); BLANKET omits it.
            case_list = []
            if arm == "SCOPED":
                case_list.append({"case_id": c_id, "cls": "EXCEPTED",
                                  "A_correct": str(ec_value), "A_wrong": str(R_for_case(cases, c_id))})
            for cid, cls, correct in scored:
                if arm == "SCOPED":
                    # over-generalized action = apply the exception value where it doesn't hold.
                    aw = str(ec_value)
                    entry = {"case_id": cid, "cls": cls, "A_correct": str(correct), "A_wrong": aw}
                else:
                    # BLANKET arm (SRD commission-decay control): the SAME rule, no exception. The
                    # break event is simply failing to apply the rule (commission-constraint decay,
                    # SRD's regime) — NOT a specific wrong scalar, so there is no A_wrong to collide.
                    # A_wrong=None => the aggregator scores BLANKET decay as (1 - correct_rate). This
                    # removes the forbidden-sentinel collision AND is the exact SRD requirement-decay
                    # analog (does the agent keep applying the required rule as turns accumulate).
                    entry = {"case_id": cid, "cls": cls, "A_correct": str(correct), "A_wrong": None}
                case_list.append(entry)
            # randomize serial order (guard E), frozen seed
            order_rng = random.Random(f"{fam}:{arm}:{dose}:{seed}")
            order_rng.shuffle(case_list)
            turn_ids = [NEUTRAL_TURNS[order_rng.randrange(len(NEUTRAL_TURNS))]["id"]
                        for _ in range(n_turns)]
            specs.append({
                "task_id": f"X6-{fam}-{arm}-{dose}",
                "family_id": fam, "arm": arm, "dose": dose, "dose_level": DOSE_LEVEL[dose],
                "domain": "insurance-claims",
                "rule_text": ap.get("rule", {}).get("text", ""),
                "rule_fn": rule_paren or ap.get("rule", {}).get("persist_derivation", ""),
                "exception": ({"case_id": c_id, "value": str(ec_value),
                               "grant_text": e0.get("superseded_conclusion_for_case", "")}
                              if arm == "SCOPED" else None),
                "blanket_requirement": (BLANKET_REQUIREMENT if arm == "BLANKET" else None),
                "intervening_turn_ids": turn_ids,
                "scored_cases": case_list,
                "positive_control": {"case_id": pc_case[0], "form": pc_form, "target": str(pc_case[2])},
            })
    return specs, None


# BLANKET-arm control (X6-DESIGN §1b): the SRD commission-constraint analog. Same rule, NO scoped
# exception. The agent must keep APPLYING the rule as turns accumulate; the break event is failing to
# (decay of a requirement), measured as (1 - correct_rate) — no specific wrong scalar, no collision.
BLANKET_REQUIREMENT = ("Standing rule: apply the standing rate/allowance to EVERY case; "
                       "there are no case-specific exceptions in effect.")


def R_for_case(cases, case_id):
    """The rule-world value for a case (its authored rule_conclusion value). Used as the EXCEPTED
    case's A_wrong: on c, applying the RULE (instead of the exception) is the wrong action."""
    for c in cases:
        if c.get("case_id") == case_id:
            v = conclusion_value(c.get("rule_conclusion", ""))
            if v is not None:
                return v
    return Decimal(-1)  # sentinel; EXCEPTED A_wrong just needs to differ from ec_value


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a2", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=20260719)
    ap.add_argument("--pilot-families", type=int, default=None,
                    help="also write x6-corpus-pilot.jsonl with the first N kept families (both arms, "
                         "all doses) + a D-EXC cross-val cell — the in-cap pilot subset. 0/omit = skip.")
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(args.a2)]
    # one instance per family (A2 has 3 dose rows/family; family structure is dose-invariant for us)
    seen = {}
    for r in rows:
        fam = r.get("family_id")
        if fam not in seen:
            seen[fam] = r

    args.out_dir.mkdir(parents=True, exist_ok=True)
    kept_specs = []
    rejected = []
    counts = {}
    for i, (fam, r) in enumerate(sorted(seen.items())):
        specs, reason = build_family(r, args.seed + i)
        if reason:
            rejected.append({"family_id": fam, "reason": reason})
            counts[reason] = counts.get(reason, 0) + 1
        else:
            kept_specs.extend(specs)

    with open(args.out_dir / "x6-corpus.jsonl", "w") as f:
        for s in kept_specs:
            f.write(json.dumps(s) + "\n")
    kept_families = sorted({s["family_id"] for s in kept_specs})
    (args.out_dir / "x6-exclusions.json").write_text(json.dumps({
        "kept_families": len(kept_families), "rejected": rejected,
        "counts_by_reason": counts, "n_families_in": len(seen),
    }, indent=2))
    report = {
        "n_families_in": len(seen),
        "n_families_kept": len(kept_families),
        "n_families_rejected": len(rejected),
        "counts_by_reason": counts,
        "n_task_specs": len(kept_specs),
        "specs_per_kept_family": (len(kept_specs) // max(1, len(kept_families))),
        "arms": ARMS, "doses": list(DOSE_TURNS),
    }
    # optional in-cap pilot subset: first N kept families (both arms, all doses) + a D-EXC cross-val cell
    # (the SCOPED dose-2 specs of those families re-tagged as the A2-replication check).
    if args.pilot_families:
        pilot_fams = kept_families[:args.pilot_families]
        pilot = [s for s in kept_specs if s["family_id"] in set(pilot_fams)]
        dexc = [dict(s, task_id=s["task_id"] + "-DEXC", dexc_cell=True)
                for s in pilot if s["arm"] == "SCOPED" and s["dose"] == "T2"]
        with open(args.out_dir / "x6-corpus-pilot.jsonl", "w") as f:
            for s in pilot + dexc:
                f.write(json.dumps(s) + "\n")
        report["pilot_families"] = len(pilot_fams)
        report["pilot_specs"] = len(pilot) + len(dexc)
        report["pilot_dexc_cell"] = len(dexc)

    (args.out_dir / "x6-build-report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
