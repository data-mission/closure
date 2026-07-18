"""E8 VERDICT COMPUTE — the canonical verdict instrument (verdict_compute-plan.md, executable).

Given the three axes' Stage-2 results dirs (~/e8-run/<axis>-stage2/results/, or the registered
<axis>-filter/results/), the filter reports, and the _oracle_result.json files, this computes the
E8 verdict EXACTLY per verdict_compute-plan.md and fills VERDICT-skeleton.md's named placeholders +
emits verdict-numbers.json. NO model, CPU file-reading only — it consumes score_worker-shaped result
JSONs (produced by batched_stage2_scorer.py or the registered score_worker.py; identical shape).

FROZEN STATS — imported VERBATIM from closure_harness.stats, never re-implemented (file:line):
  - monotonicity_gate(counts, trials)                 stats.py:191-227 → z, p_value, rates,
        ca_uptrend, strict_rise, gate_pass (Cochran-Armitage Z + strict observed rise)
  - exact_binomial_crossing(count, trials, threshold, alpha_corrected)  stats.py:138-170 →
        p_hat, critical_count, p_value, crossed (one-sided exact binomial upper tail)
  - bonferroni_alpha(axis_count)                      stats.py:249-259 → 0.05/axis_count
  - break_verdict = monotonicity_gate.gate_pass AND crossing.crossed   (plan §3 line 98; the three
        conjuncts = ca_uptrend, strict_rise, crossed — README verdict condition (a))

AGGREGATION (plan §2 lines 48-63, VERBATIM logic). Per axis X, break_side S, dose level L (1/2/3):
  for each result JSON with routing.dose_level == L:
      vi = routing.verdict_item                       # list[bool], parallel to ORIGINAL break_side items
      kept = kept_change_indices if S=="must_change" else range(len(vi))  # must_persist NOT pruned
      for i in range(len(vi)):
          if not vi[i]: continue                       # not verdict-bearing
          if S=="must_change" and i not in kept: continue  # pruned (must_change only)
          trials_L += 1
          asserted = arms[B].must_change_asserted_by_index[str(i)] if S=="must_change"
                     else arms[B].must_persist_asserted[i]
          count_L  += 1 if asserted else 0
  rate_L = count_L / trials_L

BREAK SIDE + θ per axis (skeleton headers + plan §3 line 88):
  A1 dependency-depth   → must_change, θ=0.05, dose label D
  A2 scoped-exception   → must_persist, θ=0.10, dose label S
  A3 accumulated-corr   → must_change, θ=0.05, dose label C

TWO TRAPS (honored explicitly):
  (1) _-prefixed files EXCLUDED from the results glob (oracle_verify.py:46-47 rule) — the
      _oracle_result.json is NOT a per-task record; including it would crash aggregation.
  (2) must_persist is NEVER pruned (score_worker build_annotations: keep applies to must_change
      only; plan §7 confirmed) — so A2's kept = range(len(vi)), no pruning filter.

§5 VALIDITY GATE: read <results>/_oracle_result.json. verdict != "PASS" OR the file MISSING →
  the axis's break_verdict is WITHHELD (reported "ORACLE FAIL/MISSING, verdict withheld"), never
  silently computed as final (plan §5, skeleton "Validity gate").

§0 DISCLOSURES: n_families / n_excluded / n_pruned per axis from filter-report.json + pruned-items.json.

AXIS-NOT-YET-SCORED: an axis whose results/ dir is empty/absent is reported as explicit PENDING
  (status:"PENDING", no numbers), NEVER silently skipped.

PARTIAL-AXIS GUARD (--<a>-expect-n, default A1 450 / A2 390 / A3 336 = full corpus row counts): a
  results/ dir being written LIVE has fewer files than the axis expects. Partial aggregation yields
  wrong-but-plausible pooled counts indistinguishable from a complete axis, so if fewer than the
  expected task count are present the axis is PARTIAL_WITHHELD (numbers computed for disclosure, break
  NEVER final). Set --<a>-expect-n 0 to disable for an intentional subset run.

CLI:
  cd ~/repos/closure/harness && HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run python -u ~/e8-driver/verdict_compute.py \
      --a1-results ~/e8-run/A1-stage2/results --a1-filter-report ~/e8-run/A1-filter/filter-report.json \
        --a1-pruned ~/e8-run/A1-filter/pruned-items.json \
      --a2-results ~/e8-run/A2-stage2/results --a2-filter-report ... --a2-pruned ... \
      --a3-results ~/e8-run/A3-stage2/results --a3-filter-report ... --a3-pruned ... \
      --out-dir ~/e8-run/verdict-prep --skeleton ~/e8-run/verdict-prep/VERDICT-skeleton.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# axis config: (break_side, theta, dose_label_prefix)
AXES = {
    "A1": {"break_side": "must_change", "theta": 0.05, "dose_prefix": "d"},
    "A2": {"break_side": "must_persist", "theta": 0.10, "dose_prefix": "s"},
    "A3": {"break_side": "must_change", "theta": 0.05, "dose_prefix": "c"},
}
DOSE_LEVELS = (1, 2, 3)  # routing.dose_level is int 1/2/3 (verified in all 3 corpora)


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(msg: str) -> None:
    print(f"[{_ts()}] {msg}", flush=True)


# --------------------------------------------------------------------------- IO
def load_results(results_dir: Path) -> dict:
    """Per-task result JSONs, EXCLUDING _-prefixed files (trap 1). Returns {task_id: rec} or {}."""
    res = {}
    if not results_dir or not results_dir.exists():
        return res
    for p in sorted(results_dir.glob("*.json")):
        if p.name.startswith("_"):
            continue  # trap 1: _oracle_result.json is not a per-task record
        res[p.stem] = json.loads(p.read_text())
    return res


def load_oracle(results_dir: Path) -> dict | None:
    """The §5 validity gate record, or None if absent."""
    if not results_dir:
        return None
    p = results_dir / "_oracle_result.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


def load_json(path: Path | None):
    if not path or not path.exists():
        return None
    return json.loads(path.read_text())


# --------------------------------------------------------------------------- aggregation (plan §2)
def _canon_dose(raw, tid: str) -> int:
    """Canonicalize dose_level to int 1/2/3. Corpus is int (verified), but older drafts used
    'D3'/'C2'/'S1' strings (score_worker.py:118-120) — map trailing digits, same as
    filter_stage.top_level_per_family's dose_key. Fail LOUD on an unmappable value rather than
    silently bucketing it apart (which would drop it from the 1/2/3 pooled counts)."""
    if isinstance(raw, bool):  # bool is an int subclass — reject explicitly
        raise ValueError(f"task {tid}: dose_level is bool ({raw}); expected int 1/2/3")
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        digits = "".join(ch for ch in raw if ch.isdigit())
        if digits:
            return int(digits)
    raise ValueError(f"task {tid}: unmappable dose_level {raw!r}; expected int 1/2/3 or 'D#'/'C#'/'S#'")


def aggregate_axis(results: dict, break_side: str, arm: str = "B"):
    """Pooled (count, trials) per dose level per plan §2, VERBATIM. Returns:
      {dose_level: (count, trials)} and a per-task diagnostic count for the cross-check."""
    per_dose = {L: [0, 0] for L in DOSE_LEVELS}  # [count, trials]
    seen_doses = set()
    for tid, rec in results.items():
        routing = rec.get("routing", {})
        L = _canon_dose(routing.get("dose_level"), tid)
        seen_doses.add(L)
        if L not in per_dose:
            # a dose level outside 1/2/3 — surface it, do not silently drop
            per_dose.setdefault(L, [0, 0])
        vi = routing.get("verdict_item") or []
        arm_rec = rec.get("arms", {}).get(arm, {})
        if break_side == "must_change":
            kept = set(rec.get("kept_change_indices", []))
            asserted_map = arm_rec.get("must_change_asserted_by_index", {})
        else:  # must_persist — NEVER pruned (trap 2): kept = all indices
            kept = set(range(len(vi)))
            asserted_list = arm_rec.get("must_persist_asserted", [])
        for i in range(len(vi)):
            if not vi[i]:
                continue  # not verdict-bearing
            if break_side == "must_change" and i not in kept:
                continue  # pruned (must_change only)
            per_dose[L][1] += 1  # trials
            if break_side == "must_change":
                asserted = bool(asserted_map.get(str(i), False))
            else:
                asserted = bool(asserted_list[i]) if i < len(asserted_list) else False
            # count the VIOLATION (the break-bearing event), NOT raw assertion:
            #   must_change (A1/A3): violation = STILL ASSERTED = contamination (the model kept an
            #       item it should have dropped). count += asserted.
            #   must_persist (A2):   violation = NOT ASSERTED = the DROP (the model dropped a rule
            #       conclusion it should have retained — over-generalization). count += not asserted.
            #       PHASE0 §1 (l.30) "the break is read on the must_persist side"; §3 (l.73-74)
            #       "persist-violation floor is 5.83% ... identically 1 - 0.9417 completeness" —
            #       i.e. the break rate is 1 - retention = the drop rate, NOT retention. Counting
            #       `asserted` here (retention ~0.95) ran monotonicity/crossing on the WRONG side
            #       (red-team finding 2026-07-18): a real A2 break could never fire (retention
            #       falling => ca_uptrend false). Fixed to count the drop.
            violation = asserted if break_side == "must_change" else (not asserted)
            per_dose[L][0] += 1 if violation else 0  # count = violations on the break side
    return {L: (c, t) for L, (c, t) in per_dose.items()}, sorted(x for x in seen_doses if x is not None)


# --------------------------------------------------------------------------- per-axis verdict
@dataclass
class AxisVerdict:
    axis: str
    status: str  # "SCORED" | "PENDING" | "ORACLE_WITHHELD"
    break_side: str
    theta: float
    per_dose: dict            # {L: (count, trials)}
    mono: dict | None         # monotonicity_gate fields
    crossing: dict | None     # exact_binomial_crossing fields (top level)
    break_verdict: bool | None
    oracle: dict              # {verdict, n_sampled, mismatches, present}
    disclosures: dict         # n_families/n_excluded/n_pruned
    notes: list


def compute_axis(axis: str, results_dir: Path, filter_report_path: Path, pruned_path: Path,
                 alpha_corrected: float, require_n_tasks: int | None = None) -> AxisVerdict:
    from closure_harness.stats import monotonicity_gate, exact_binomial_crossing

    cfg = AXES[axis]
    break_side, theta = cfg["break_side"], cfg["theta"]
    results = load_results(results_dir)
    oracle = load_oracle(results_dir)
    filter_report = load_json(filter_report_path)
    pruned = load_json(pruned_path)

    disclosures = _disclosures(filter_report, pruned)
    notes = []

    # PENDING: no results yet (explicit, never silent skip)
    if not results:
        notes.append(f"{axis}: results dir empty or absent ({results_dir}) — axis not yet scored")
        return AxisVerdict(axis, "PENDING", break_side, theta, {}, None, None, None,
                           {"present": oracle is not None,
                            "verdict": (oracle or {}).get("verdict")},
                           disclosures, notes)

    # PARTIAL guard: a results dir being written LIVE has fewer files than the axis expects. Partial
    # aggregation produces wrong-but-plausible pooled counts that this script cannot distinguish from
    # a complete axis — so if fewer than require_n_tasks result files are present, WITHHOLD (compute
    # for disclosure, never final). This is the --*-expect-n hardening (team-lead 2026-07-18).
    n_present = len(results)
    partial = require_n_tasks is not None and n_present < require_n_tasks
    if partial:
        notes.append(f"{axis}: PARTIAL — {n_present}/{require_n_tasks} expected result files present "
                     "(results dir likely still being written); break_verdict WITHHELD, numbers "
                     "computed for disclosure only. Re-run when the axis is complete.")

    per_dose, seen = aggregate_axis(results, break_side)
    # cross-check: every dose level 1/2/3 must be present
    missing_levels = [L for L in DOSE_LEVELS if per_dose.get(L, (0, 0))[1] == 0]
    if missing_levels:
        notes.append(f"{axis}: dose level(s) {missing_levels} have 0 trials — a dropped/empty level "
                     "VOIDS the axis (PHASE0 §3/§4); break_verdict withheld")

    counts = [per_dose[L][0] for L in DOSE_LEVELS]
    trials = [per_dose[L][1] for L in DOSE_LEVELS]

    mono = crossing = None
    break_verdict = None
    if not missing_levels:
        m = monotonicity_gate(counts, trials)  # frozen stats.py:191
        mono = {"z": m.z, "p_value": m.p_value, "rates": list(m.rates),
                "ca_uptrend": m.ca_uptrend, "strict_rise": m.strict_rise, "gate_pass": m.gate_pass}
        top_count, top_trials = per_dose[3]
        cr = exact_binomial_crossing(top_count, top_trials, theta, alpha_corrected)  # stats.py:138
        crossing = {"p_hat": cr.p_hat, "critical_count": cr.critical_count,
                    "p_value": cr.p_value, "crossed": cr.crossed,
                    "threshold": theta, "alpha_corrected": alpha_corrected}
        break_verdict = bool(m.gate_pass and cr.crossed)  # plan §3 line 98

    # status precedence (any non-SCORED state = NOT final; numbers kept for disclosure):
    #   PARTIAL_WITHHELD (incomplete results) and/or ORACLE_WITHHELD (§5) — both can apply.
    status = "SCORED"
    oracle_ok = oracle is not None and oracle.get("verdict") == "PASS"
    withhold_reasons = []
    if partial:
        withhold_reasons.append(f"PARTIAL({n_present}/{require_n_tasks})")
    if not oracle_ok:
        reason = "MISSING" if oracle is None else oracle.get("verdict")
        withhold_reasons.append(f"ORACLE_{reason}")
        notes.append(f"{axis}: oracle {reason} — break_verdict WITHHELD pending re-score (§5); "
                     "numbers computed for disclosure but NOT final")
    if withhold_reasons:
        # PARTIAL takes the status label when present (it's the harder "don't trust these numbers"
        # signal — the aggregation itself is incomplete, not just unverified); else oracle-withheld.
        status = "PARTIAL_WITHHELD" if partial else "ORACLE_WITHHELD"

    return AxisVerdict(
        axis, status, break_side, theta, per_dose, mono, crossing, break_verdict,
        {"present": oracle is not None, "verdict": (oracle or {}).get("verdict"),
         "n_sampled": (oracle or {}).get("n_sampled_tasks"),
         "n_mismatches": (oracle or {}).get("n_mismatches"),
         "n_present": n_present, "n_expected": require_n_tasks,
         "withhold_reasons": withhold_reasons},
        disclosures, notes,
    )


def _disclosures(filter_report: dict | None, pruned: list | None) -> dict:
    """§0: n_families / n_excluded / n_pruned from the filter report + pruned register."""
    if filter_report is None:
        return {"n_families": None, "n_excluded": None, "n_pruned": None,
                "note": "filter-report.json absent"}
    return {
        "n_families": filter_report.get("n_families"),
        "n_passed": filter_report.get("n_passed"),
        "n_excluded": filter_report.get("n_excluded"),
        "n_pruned": (len(pruned) if isinstance(pruned, list)
                     else filter_report.get("n_pruned_items")),
    }


# --------------------------------------------------------------------------- program-level
def program_verdict(axis_verdicts: dict) -> dict:
    """README verdict conditions (a)/(b). Only axes with a FINAL (not withheld/pending) break_verdict
    count. Broke = final break_verdict True. If any axis is pending/withheld, the program verdict is
    itself PENDING (cannot declare (b) NO-BREAK while an axis is unscored/unverified)."""
    final = {a: v for a, v in axis_verdicts.items()
             if v.status == "SCORED" and v.break_verdict is not None}
    non_final = [a for a, v in axis_verdicts.items() if a not in final]
    axes_broke = [a for a, v in final.items() if v.break_verdict]
    if non_final:
        return {"status": "PENDING", "reason": f"axes not final: {non_final}",
                "axes_broke": axes_broke, "block_a_fires": None, "block_b_fires": None}
    return {"status": "FINAL", "axes_broke": axes_broke,
            "block_a_fires": len(axes_broke) >= 1, "block_b_fires": len(axes_broke) == 0}


# --------------------------------------------------------------------------- skeleton fill
def build_placeholders(axis_verdicts: dict, program: dict, alpha_corrected: float) -> dict:
    ph = {"alpha_corrected": round(alpha_corrected, 6)}
    for axis, v in axis_verdicts.items():
        p = AXES[axis]["dose_prefix"]  # d/s/c
        a = axis.lower()
        ph[f"{a}_n_families"] = v.disclosures.get("n_families")
        ph[f"{a}_n_excluded"] = v.disclosures.get("n_excluded")
        ph[f"{a}_n_pruned"] = v.disclosures.get("n_pruned")
        ph[f"{a}_oracle"] = v.oracle.get("verdict") or ("MISSING" if not v.oracle.get("present") else None)
        ph[f"{a}_oracle_n"] = v.oracle.get("n_sampled")
        ph[f"{a}_oracle_mismatches"] = v.oracle.get("n_mismatches")
        for idx, L in enumerate(DOSE_LEVELS, 1):
            c, t = v.per_dose.get(L, (None, None))
            ph[f"{a}_{p}{idx}_count"] = c
            ph[f"{a}_{p}{idx}_trials"] = t
            ph[f"{a}_{p}{idx}_rate"] = (round(c / t, 6) if (c is not None and t) else None)
        if v.mono:
            ph[f"{a}_ca_z"] = round(v.mono["z"], 4)
            ph[f"{a}_ca_p"] = round(v.mono["p_value"], 6)
            ph[f"{a}_ca_uptrend"] = v.mono["ca_uptrend"]
            ph[f"{a}_strict_rise"] = v.mono["strict_rise"]
            ph[f"{a}_gate_pass"] = v.mono["gate_pass"]
        if v.crossing:
            ph[f"{a}_critical_k"] = v.crossing["critical_count"]
            ph[f"{a}_crossing_p"] = round(v.crossing["p_value"], 6)
            ph[f"{a}_crossed"] = v.crossing["crossed"]
        # break_verdict: explicit string incl. withheld/pending
        if v.status == "PENDING":
            ph[f"{a}_break_verdict"] = "PENDING (not yet scored)"
        elif v.status == "PARTIAL_WITHHELD":
            npres = v.oracle.get("n_present")
            nexp = v.oracle.get("n_expected")
            ph[f"{a}_break_verdict"] = f"WITHHELD (partial: {npres}/{nexp} tasks scored)"
        elif v.status == "ORACLE_WITHHELD":
            ph[f"{a}_break_verdict"] = "WITHHELD (oracle FAIL/MISSING)"
        else:
            ph[f"{a}_break_verdict"] = "BREAK" if v.break_verdict else "NO BREAK"
    ph["which_axes_broke"] = ", ".join(program.get("axes_broke", [])) or "none"
    ph["program_status"] = program["status"]
    ph["block_a_fires"] = program.get("block_a_fires")
    ph["block_b_fires"] = program.get("block_b_fires")
    return ph


def fill_skeleton(skeleton_text: str, ph: dict) -> tuple[str, list]:
    """Replace {{name}} with ph[name] where present. Returns (filled, unfilled_placeholders)."""
    unfilled = []

    def repl(m):
        name = m.group(1).strip()
        if name in ph and ph[name] is not None:
            return str(ph[name])
        unfilled.append(name)
        return m.group(0)  # leave the placeholder for a human/next pass

    filled = re.sub(r"\{\{([^}]+)\}\}", repl, skeleton_text)
    return filled, sorted(set(unfilled))


def main() -> None:
    ap = argparse.ArgumentParser(description="E8 verdict compute (canonical instrument)")
    # per-axis expected task count (full corpus row count, verified): A1 450 / A2 390 / A3 336.
    # If the results dir has FEWER files than this, the axis is PARTIAL_WITHHELD (a live-writing dir
    # cannot be distinguished from a complete one by aggregation alone). Set --<a>-expect-n 0 to
    # disable the guard for that axis (e.g. an intentional subset run).
    _default_expect = {"a1": 450, "a2": 390, "a3": 336}
    for a in ("a1", "a2", "a3"):
        ap.add_argument(f"--{a}-results", type=Path, required=True)
        ap.add_argument(f"--{a}-filter-report", type=Path, default=None)
        ap.add_argument(f"--{a}-pruned", type=Path, default=None)
        ap.add_argument(f"--{a}-expect-n", type=int, default=_default_expect[a],
                        help=f"expected task count for {a.upper()} (default {_default_expect[a]}; "
                             "fewer files → PARTIAL_WITHHELD; 0 disables the guard)")
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--skeleton", type=Path, default=None,
                    help="VERDICT-skeleton.md to fill (optional; else only verdict-numbers.json)")
    ap.add_argument("--axis-count", type=int, default=3, help="bonferroni family size (frozen 3)")
    args = ap.parse_args()

    from closure_harness.stats import bonferroni_alpha
    alpha_corrected = bonferroni_alpha(axis_count=args.axis_count)  # stats.py:249
    _log(f"[verdict] alpha_corrected = bonferroni_alpha({args.axis_count}) = {alpha_corrected:.6f}")

    axis_verdicts = {}
    for axis in ("A1", "A2", "A3"):
        a = axis.lower()
        expect_n = getattr(args, f"{a}_expect_n")
        v = compute_axis(axis, getattr(args, f"{a}_results"),
                         getattr(args, f"{a}_filter_report"), getattr(args, f"{a}_pruned"),
                         alpha_corrected,
                         require_n_tasks=(expect_n if expect_n and expect_n > 0 else None))
        axis_verdicts[axis] = v
        if v.status == "PENDING":
            _log(f"[verdict] {axis}: PENDING (no results)")
        else:
            doses = " ".join(f"{L}:{v.per_dose.get(L,(0,0))[0]}/{v.per_dose.get(L,(0,0))[1]}"
                             for L in DOSE_LEVELS)
            _log(f"[verdict] {axis}: {v.status} | dose {doses} | break={v.break_verdict} | "
                 f"oracle={v.oracle.get('verdict')}")

    program = program_verdict(axis_verdicts)
    ph = build_placeholders(axis_verdicts, program, alpha_corrected)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    numbers = {
        "computed_at": _ts(),
        "alpha_corrected": alpha_corrected,
        "axes": {axis: {
            "status": v.status, "break_side": v.break_side, "theta": v.theta,
            "per_dose": {str(L): {"count": v.per_dose.get(L, (None, None))[0],
                                  "trials": v.per_dose.get(L, (None, None))[1]}
                         for L in DOSE_LEVELS},
            "monotonicity": v.mono, "crossing": v.crossing, "break_verdict": v.break_verdict,
            "oracle": v.oracle, "disclosures": v.disclosures, "notes": v.notes,
        } for axis, v in axis_verdicts.items()},
        "program_verdict": program,
    }
    (args.out_dir / "verdict-numbers.json").write_text(json.dumps(numbers, indent=2))
    _log(f"[verdict] wrote {args.out_dir/'verdict-numbers.json'}")

    if args.skeleton and args.skeleton.exists():
        filled, unfilled = fill_skeleton(args.skeleton.read_text(), ph)
        (args.out_dir / "VERDICT-numbers.md").write_text(filled)
        _log(f"[verdict] wrote {args.out_dir/'VERDICT-numbers.md'} "
             f"({len(unfilled)} placeholders left unfilled: {unfilled[:12]}"
             f"{'...' if len(unfilled) > 12 else ''})")

    _log("[verdict] PROGRAM " + json.dumps({
        "status": program["status"],
        "axes_broke": program.get("axes_broke"),
        "block_a_fires": program.get("block_a_fires"),
        "block_b_fires": program.get("block_b_fires"),
        "per_axis_status": {a: v.status for a, v in axis_verdicts.items()},
    }))


if __name__ == "__main__":
    main()
