# E8 verdict compute plan

Plan only — no executable written. Read-only outside `~/e8-run/verdict-prep/` per assignment.
Every step names its exact input files, the exact frozen function called with exact args, and
the exact output field it fills in `VERDICT-skeleton.md`. Team-lead adjudicates this plan before
any code is written; code is reviewed at that boundary, not before.

## 1. Inputs (per axis X in {A1, A2, A3})

- `~/e8-run/{X}-filter/results/*.json` — Stage-2 per-task result files, one per task, each shaped
  per `score_worker.score_one_task` (score_worker.py:53-138): `{task_id, kept_change_indices,
  routing: {family_id, axis, dose_level, break_side, verdict_item, verdict_item_defaulted,
  item_roles}, arms: {B: {n_items, contaminated_items, contamination, completeness,
  must_change_asserted_by_index, must_persist_asserted}}}`.
  - NOTE: this is the REGISTERED-RUN result dir (post-filter Stage-2 scoring of the full corpus
    under the Arm-B-only generation), NOT the filter-stage's own `filter-report.json` /
    `pruned-items.json` (those are filter-stage outputs consumed as INPUT to Stage-2 via
    `--pruned`, per launch.sh:71). Confirm this distinction is real by checking
    `~/e8-run/{X}-filter/results/` is a directory of per-task JSONs (score_worker's
    `atomic_write_json` pattern) separate from `~/e8-run/{X}-filter/filter-report.json` before
    writing any aggregation code — if Stage-2 hasn't launched yet for an axis, `results/` will
    be empty or absent, which is itself the "not ready" signal to check for.
- `~/e8-run/{X}-filter/results/_oracle_result.json` — CONFIRMED exact path (oracle_verify.py
  tail, `(args.out_dir / "_oracle_result.json").write_text(...)`): `{oracle, verdict: "PASS"|"FAIL",
  oracle_threads, n_sampled_tasks, per_worker_coverage, n_mismatches, mismatches (first 50),
  elapsed_s}`, for §2 "Validity gate". NOTE the leading underscore — `load_results` (oracle_verify.py:43-49)
  explicitly skips any `out_dir` file starting with `_`, so this file is invisible to the
  aggregation loop in §2 of this plan without special-casing; the §2 loop over `results/*.json`
  MUST exclude `_oracle_result.json` (and any other `_`-prefixed file) or it will crash trying to
  parse it as a per-task result record.
- `~/repos/closure/experiments/E8-instruction-breakpoint/corpus-candidates/{X-file}.jsonl` — the
  frozen corpus, for `must_change`/`must_persist` item counts and `axis_params.verdict_item` (only
  needed as a cross-check; the routing block already carries `verdict_item` per result file, so
  this is a redundant-agreement check, not a primary source).
- `~/repos/closure/harness/src/closure_harness/config.py` → `CONFIG.stats` — `alpha=0.05`,
  `bonferroni_comparisons=3` (NOTE: this field name is inherited from E5's 3-arm pairwise-comparison
  use case; for E8 it is NOT reused directly — E8's multiplicity is over the 3-AXIS count via
  `bonferroni_alpha(axis_count=3)`, stats.py:249-259, a distinct function/purpose from
  `two_proportion_ztest`'s `bonferroni_comparisons` field. Do not conflate the two Bonferroni
  divisors — confirm `bonferroni_alpha(3)` is the one actually called for the crossing tests, not
  a manual `0.05/3` that happens to numerically coincide).

## 2. Per-axis aggregation (fills §2 tables in VERDICT-skeleton.md)

For axis X, break_side S (must_change for A1/A3, must_persist for A2), for each dose level L in
the axis's 3 levels:

```
count_L = 0
trials_L = 0
for each result JSON in ~/e8-run/{X}-filter/results/ where routing.dose_level == L:
    vi = routing.verdict_item                    # list[bool], parallel to ORIGINAL break_side item list
    kept = kept_change_indices if S == "must_change" else range(len(vi))  # must_persist has no pruning register (filter_stage.py:128 — pruning is must_change-only)
    for i in range(len(vi)):
        if not vi[i]:
            continue                              # not verdict-bearing, skip
        if S == "must_change" and i not in kept:
            continue                              # pruned, skip (score_worker.py:122-128 rule)
        trials_L += 1
        asserted = (arms["B"]["must_change_asserted_by_index"][str(i)] if S == "must_change"
                    else arms["B"]["must_persist_asserted"][i])
        count_L += 1 if asserted else 0
```

Fills: `{{aX_LN_count}}`, `{{aX_LN_trials}}`, `{{aX_LN_rate}} = count_L/trials_L`.

CROSS-CHECK before trusting this loop: sum(trials_L across all 3 levels) should equal the
axis's `n_families_scored × (items_per_family_after_pruning_and_verdict_filter)` — sanity print
this against the raw `wc -l` of the results dir and the corpus's declared per-family item counts
(PHASE0.md §3: "≈1.78 items/task" for must_change axes, "2/task" fixed for A2 must_persist) before
accepting any count as final. A mismatch here means the routing/pruning logic was misread, not
that the data is wrong.

## 3. Per-axis break-conjunct computation (fills the three bullet points under each axis heading)

```
from closure_harness.stats import monotonicity_gate, exact_binomial_crossing, bonferroni_alpha

alpha_corrected = bonferroni_alpha(axis_count=3)     # = 0.05/3, called via the function per PHASE0.md §6/(a),
                                                       # NOT hand-typed — the frozen function is the source of truth

mono = monotonicity_gate(
    counts=[count_L1, count_L2, count_L3],
    trials=[trials_L1, trials_L2, trials_L3],
)
# mono.z, mono.p_value, mono.rates, mono.ca_uptrend, mono.strict_rise, mono.gate_pass

theta = 0.05 if S == "must_change" else 0.10          # PHASE0.md §3: θ=5% contamination (A1,A3), θ_persist=10% (A2)

crossing = exact_binomial_crossing(
    count=count_L3,                                    # TOP level only (D3/S3/C3) — PHASE0.md §3.3
    trials=trials_L3,
    threshold=theta,
    alpha_corrected=alpha_corrected,
)
# crossing.p_hat, crossing.critical_count, crossing.p_value, crossing.crossed

break_verdict = mono.gate_pass and crossing.crossed    # PHASE0.md §3: "iff all three hold" — conjunction of
                                                         # (1) ca_uptrend, (2) strict_rise, (3) crossed
```

Fills: `{{aX_ca_z}}=mono.z`, `{{aX_ca_p}}=mono.p_value`, `{{aX_ca_uptrend}}=mono.ca_uptrend`,
`{{aX_strict_rise}}=mono.strict_rise`, `{{aX_gate_pass}}=mono.gate_pass`,
`{{aX_critical_k}}=crossing.critical_count`, `{{aX_crossing_p}}=crossing.p_value`,
`{{aX_crossed}}=crossing.crossed`, `{{aX_break_verdict}}=break_verdict`.

INDEPENDENT HAND RECOMPUTATION (matching E5 VERDICT.md's own disclosed practice, "all three
z-tests were independently recomputed by hand — exact match to the frozen stats.py"): for at
least the TOP level's crossing test on each axis, hand-verify `exact_binomial_crossing`'s
`critical_count` via `scipy.stats.binom.sf(k-1, trials, threshold) <= alpha_corrected` at k-1
and k to confirm k is truly the smallest crossing count — do not trust the function's output
without this check, per stats.py:173-178's own `_critical_count` loop logic being simple enough
to hand-verify at one data point.

## 4. Program-level verdict (fills "Which pre-registered program-level block fires")

```
axes_broken = [X for X in ("A1","A2","A3") if break_verdict[X]]
block_a_fires = len(axes_broken) >= 1
block_b_fires = len(axes_broken) == 0
```

Per README.md's verdict conditions (quoted verbatim in skeleton §2): these two conditions are
mutually exclusive and exhaustive over {broke, didn't}, so exactly one of block_a/block_b fires
— no adjudication ambiguity expected here (unlike E5's REFUTED-vs-registered-wording gap, which
arose from a 3-way A/B/C comparison space that didn't cleanly cover a significant reversal; E8's
binary break/no-break structure does not have that failure mode). Still write the adjudication
prose by hand rather than auto-filling from the boolean, in case an axis's oracle FAILED (voiding
that axis's contribution) or a level was dropped (voiding that whole axis) — those cases need
prose disclosure, not a silent boolean.

## 5. Oracle validity gate (fills §2 "Validity gate")

Read `~/e8-run/{X}-filter/results/_oracle_result.json` (confirmed path, §1) for PASS/FAIL,
sampled task count, mismatch count, per-worker-signature coverage. Any FAIL blocks that axis's
break_verdict from being reported as final in VERDICT.md — report it as "AXIS X: ORACLE FAIL,
verdict withheld pending re-score" rather than silently computing and publishing a break/no-break
number derived from unverified scores.

## 6. Deviations register (fills §4)

Pull exact timestamps/evidence for each disclosed deviation from:
- Dashboard event log (`e8-console.html`'s `RUN.events`) — launch times, kill/relaunch times,
  equivalence-check results already logged there during the run (e.g., "Parallel scorer
  equivalence PASS — 84/84 booleans identical serial vs sharded").
- `~/e8-run/*/run.log` + `run-timestamped.log` for exact per-axis phase timestamps.
- `git diff` of `filter_stage_progress.py` vs `filter_stage.py` (and `filter_parallel.py` vs the
  registered driver) to confirm and quote the exact diff size claimed in dashboard events
  ("2-line diff vs original") — do not just repeat the dashboard's claim without independently
  confirming it via an actual diff, matching this auditor's own standard from the dashboard-audit
  work (never proxy an unverified number).

## 7. What this plan deliberately does NOT do (flagged for team-lead adjudication)

- Does not decide WHERE the aggregation code lives (a new script under `~/e8-run/verdict-prep/`
  vs. reusing/extending an existing harness module) — that's an implementation choice for the
  coding boundary, not this planning pass.
- CONFIRMED (not left as an assumption): `build_annotations` (score_worker.py:38-50) computes
  `must_persist=tuple(task["must_persist"])` — the FULL list, unfiltered by `keep`/pruned_ids.
  Pruning applies ONLY to must_change (`keep = [i for i in range(len(task["must_change"])) if i
  not in pruned_ids]`). So A2's aggregation loop in §2 above is correct as written: for
  break_side=="must_persist", `kept = range(len(vi))` (no pruning filter applied), matching this
  confirmed behavior exactly. Flagged here because getting this backwards would have silently
  under-counted A2's trials by excluding items that were never actually pruned.
- Does not pre-compute any actual number — no axis has a populated `results/` directory yet as
  of this writing (all three are still in filter/Stage-1 or earlier); this plan is executable
  the moment the first axis's Stage-2 results land.
