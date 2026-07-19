"""Equivalence gate: filter_report_from_batched vs the FROZEN filter-stage report — byte-level on the
load-bearing content, on the smoke families. MANDATORY before using rebuilt pruned-items.json.

Compares the report this tool rebuilds from batched scores against the ORIGINAL frozen-path outputs at
~/e8-run/_smoke/{filter-report.json, pruned-items.json}. PASS iff:
  - pruned-items.json is IDENTICAL (same rows, same order, same fields — canonical-JSON byte compare);
  - passed_families + excluded_families sets IDENTICAL;
  - per_family verdicts IDENTICAL: for every family, {passes, a_dependent_items, pruned_items,
    n_must_change, assertion_counts} byte-equal (assertion_counts is the a/c majority substrate — if it
    matches, the pass/prune logic provably matches since adjudicate is a pure function of it);
  - n_passed / n_excluded / n_pruned_items scalars IDENTICAL.
The ONLY field excluded from the compare is `elapsed_s` (wall-clock, provably volatile) and — if the
batched scores were produced on MPS — `config_hash` (device-dependent by design; the booleans are what
must match, and they're captured in assertion_counts). Any other divergence = FAIL loud, exit nonzero.

INPUT: this gate does NOT score. It takes an ALREADY-PRODUCED batched-scores.json for the smoke
families (produce it on the Mini by running batched_scorer on ~/e8-run/_smoke/tasks.jsonl +
~/e8-run/_smoke/gen.jsonl, or reuse ~/e8-run/_gpu_rewire/equiv-smoke.json if it carries the same
per-(fam,state,draw,item) scores), rebuilds the report via filter_report_from_batched's functions, and
diffs. Because the rebuild is a pure re-shape + frozen adjudicate, this gate proves the WHOLE
rebuild-from-batched path is byte-equivalent to the frozen path on real ground truth.

CLI:
  cd ~/repos/closure/harness && HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run python -u ~/e8-driver/filter_report_equiv.py \
      --tasks ~/e8-run/_smoke/tasks.jsonl \
      --batched-scores <smoke batched-scores.json> \
      --frozen-report ~/e8-run/_smoke/filter-report.json \
      --frozen-pruned ~/e8-run/_smoke/pruned-items.json \
      --out ~/e8-run/_smoke/filter-report-equiv.json --n-draws 3
  echo "exit=$?"   # nonzero => divergence => rebuilt pruned-items.json NOT safe
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DRIVER = Path(__file__).resolve().parent
sys.path.insert(0, str(DRIVER))
import filter_stage  # noqa: E402
import filter_report_from_batched as frb  # noqa: E402
from common import atomic_write_json  # noqa: E402


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(msg: str) -> None:
    print(f"[{_ts()}] {msg}", flush=True)


def _canon(obj) -> str:
    """Canonical JSON: sorted keys, compact separators — byte-stable for comparison."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="filter_report_from_batched vs frozen filter-report (byte-level)")
    ap.add_argument("--tasks", required=True, type=Path)
    ap.add_argument("--batched-scores", required=True, type=Path)
    ap.add_argument("--frozen-report", required=True, type=Path)
    ap.add_argument("--frozen-pruned", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--n-draws", type=int, default=3)
    ap.add_argument("--families", type=str, default=None)
    ap.add_argument("--correction-keep-cap", type=int, default=None)
    args = ap.parse_args()

    from closure_harness.config import CONFIG, config_hash
    threshold = CONFIG.outcome.assert_threshold

    tasks = [json.loads(l) for l in args.tasks.read_text().splitlines() if l.strip()]
    top = filter_stage.top_level_per_family(tasks)
    if args.families:
        keep = set(args.families.split(","))
        top = {f: t for f, t in top.items() if f in keep}

    batched, meta = frb.load_batched_scores(args.batched_scores)
    _log(f"[report-equiv] {len(top)} families; batched keys={len(batched)}; device={meta.get('device')}")

    # rebuild via the SAME functions filter_report_from_batched uses (pure re-shape + frozen adjudicate)
    t0 = time.time()
    scored = frb.reconstruct_scored(top, batched, args.n_draws)
    if args.correction_keep_cap is None:
        passed, excluded, pruned_rows, per_family = filter_stage.adjudicate(top, scored, args.n_draws)
    else:
        passed, excluded, pruned_rows, per_family = filter_stage.adjudicate(
            top, scored, args.n_draws, correction_keep_cap=args.correction_keep_cap)

    frozen_report = json.loads(args.frozen_report.read_text())
    frozen_pruned = json.loads(args.frozen_pruned.read_text())

    # restrict the frozen report to the families we rebuilt (the smoke report may be exactly these 4)
    fam_keep = set(top.keys())
    fz_per_family = {k: v for k, v in frozen_report.get("per_family", {}).items() if k in fam_keep}
    fz_pruned = [r for r in frozen_pruned if r.get("family_id") in fam_keep]
    fz_passed = [f for f in frozen_report.get("passed_families", []) if f in fam_keep]
    fz_excluded = [f for f in frozen_report.get("excluded_families", []) if f in fam_keep]

    diffs = []

    # 1. pruned-items.json — IDENTICAL (rows, order, fields). Canonical compare of the full list.
    if _canon(pruned_rows) != _canon(fz_pruned):
        diffs.append({"what": "pruned-items", "rebuilt": pruned_rows, "frozen": fz_pruned})

    # 2. passed / excluded sets IDENTICAL
    if sorted(passed) != sorted(fz_passed):
        diffs.append({"what": "passed_families", "rebuilt": sorted(passed), "frozen": sorted(fz_passed)})
    if sorted(excluded) != sorted(fz_excluded):
        diffs.append({"what": "excluded_families", "rebuilt": sorted(excluded), "frozen": sorted(fz_excluded)})

    # 3. per_family verdict fields IDENTICAL (passes, a_dependent_items, pruned_items, n_must_change,
    #    assertion_counts). assertion_counts is the a/c substrate — equality here proves the pass/prune
    #    logic matches (adjudicate is a pure function of it). task_id/axis carried too.
    verdict_fields = ("task_id", "axis", "n_must_change", "a_dependent_items", "pruned_items",
                      "passes", "assertion_counts")
    fam_union = sorted(set(per_family) | set(fz_per_family))
    for fam in fam_union:
        rb = per_family.get(fam)
        fz = fz_per_family.get(fam)
        if rb is None or fz is None:
            diffs.append({"what": "per_family presence", "family": fam,
                          "rebuilt_present": rb is not None, "frozen_present": fz is not None})
            continue
        for f in verdict_fields:
            if _canon(rb.get(f)) != _canon(fz.get(f)):
                diffs.append({"what": f"per_family.{f}", "family": fam,
                              "rebuilt": rb.get(f), "frozen": fz.get(f)})

    # 4. scalar counts
    for scalar, rb_val, fz_val in (
        ("n_passed", len(passed), len(fz_passed)),
        ("n_excluded", len(excluded), len(fz_excluded)),
        ("n_pruned_items", len(pruned_rows), len(fz_pruned)),
    ):
        if rb_val != fz_val:
            diffs.append({"what": scalar, "rebuilt": rb_val, "frozen": fz_val})

    passed_gate = (len(diffs) == 0)
    report = {
        "tool": "filter_report_equiv",
        "verdict": "PASS" if passed_gate else "FAIL",
        "n_families": len(top),
        "batched_device": meta.get("device"),
        "excluded_from_compare": ["elapsed_s (volatile)",
                                  "config_hash (device-dependent by design; booleans compared via "
                                  "assertion_counts)"],
        "n_diffs": len(diffs),
        "diffs": diffs[:50],
        "rebuilt_summary": {"n_passed": len(passed), "n_excluded": len(excluded),
                            "n_pruned_items": len(pruned_rows)},
        "frozen_summary": {"n_passed": len(fz_passed), "n_excluded": len(fz_excluded),
                           "n_pruned_items": len(fz_pruned)},
        "elapsed_s": round(time.time() - t0, 3),
    }
    atomic_write_json(args.out, report)
    _log("[report-equiv] RESULT " + json.dumps({
        "verdict": report["verdict"], "n_diffs": len(diffs),
        "rebuilt": report["rebuilt_summary"], "frozen": report["frozen_summary"]}))
    _log(f"[report-equiv] wrote {args.out}")

    if not passed_gate:
        _log("[report-equiv] *** FAIL: rebuilt report diverges from the frozen filter-stage output. "
             "Do NOT use the rebuilt pruned-items.json. First diffs above.")
        sys.exit(1)
    _log("[report-equiv] PASS: rebuilt pruned-items.json + pass/exclude verdicts BYTE-IDENTICAL to the "
         "frozen filter-stage output on the smoke families.")


if __name__ == "__main__":
    main()
