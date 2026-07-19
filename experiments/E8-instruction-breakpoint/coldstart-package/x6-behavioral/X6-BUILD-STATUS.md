# X6 — build status + pilot launch sheet

Status 2026-07-19: **HARNESS BUILT + ACCEPTANCE-PASSED (no generation). Pilot generation gated on team-lead.**
All tools alongside the design docs in this dir; mirror on the Mini at `/tmp/x6/` (move to `~/e8-driver/`
for the real run). Frozen harness files untouched throughout.

## Files
- `x6_normalize.py` — canonical_scalar + canonical_eq + hand oracle suite (guard B primitive). RAISES on
  word/ambiguous values → the (FF) diagnostic. **Oracle suite: PASS** (19 scalar + 6 eq cases).
- `x6_turnbank.py` — 14 neutral intervening sub-tasks + guard-F forbidden-token check. **Guard F: PASS.**
- `x6_build.py` — A2→X6 transform, both arms, construction gates A/B/C/E, exclusion register.
- `x6_generate.py` — multi-turn FORM-WRITE agent loop, guard-G verbatim re-present, `--dry-run` fake agent.
- `x6_verdict.py` — deterministic aggregator: guard-D conditioning, FF/TT smoke cells routed not counted,
  paired SCOPED−BLANKET permutation contrast, frozen stats imported VERBATIM from `closure_harness.stats`.
- `x6_toy_test.py` — 12 hand-computed aggregator assertions. **PASS.**

## Acceptance evidence (all no-generation, run on the Mini)
1. **Normalizer oracle suite PASS** — `python3 x6_normalize.py` → 19/19 scalar + 6/6 eq, RAISES on
   "twelve thousand"/""/two-number/boolean/None.
2. **Guard F PASS** — 14 neutral turns, 0 leakage tokens.
3. **Transform: 119/130 families kept, 714 specs, 0 oracle-exclusivity violations.** Rejections all
   legitimate: 4 unparseable-exception, 3 rule==exception collision (guard A), 3 excepted-noop (exception
   value == case's rule value, guard A), 1 unparseable-rule. Structural spot-check: arms balanced 357/357,
   doses balanced, SCOPED always has EXCEPTED case (366/366), BLANKET never does (0), turn-count matches
   dose (714/714). (Yield matches the pre-build feasibility estimate of 121; the 2 fewer are the new
   excepted-noop guard, which is correct to reject.)
4. **Aggregator toy test PASS** — 12/12 hand assertions incl. guard-D conditioning (lost-exception RULE
   dropped + excepted_lost incremented), FF/TT routed-not-counted, BLANKET decay = 1−correct, and verdict
   WITHHELD when a TT appears on real output.
5. **Full pipeline dry-run (build→generate→aggregate, 714 specs, no generation)** — fixture agent (correct everywhere
   except over-generalize on RULE at T3) produced SCOPED over-rate 0/0/0.667, BLANKET decay 0/0/0,
   separation_ok, paired p=0.0 over 119 families, **0 FF / 0 TT / 0 excepted_lost / 0 pc_fail / 0
   cross_mismatch**. Verdict correctly = NO_BREAK (flat-then-jump fails strict_rise — the anti-fishing gate
   firing as designed even on the fixture). This proves the plumbing AND that a fake single-dose bump is
   correctly rejected as not-a-break.

## Pilot launch (owner/team-lead gated; generation)
The full 119-family corpus in both arms is a large generation load; the pilot uses a **40-family
stratified subset** to bound it. Exact sequence:

```
# 0. (one-time) move tools to ~/e8-driver, corpus to ~/e8-run/x6/
# 1. re-verify acceptance on the box (no generation):
cd ~/repos/closure/harness && PYTHONPATH=~/e8-driver uv run python ~/e8-driver/x6_toy_test.py
python3 ~/e8-driver/x6_normalize.py && python3 ~/e8-driver/x6_turnbank.py
# 2. build corpus (no generation), then take the 40-family pilot subset:
python3 ~/e8-driver/x6_build.py --a2 <A2.jsonl> --out-dir ~/e8-run/x6/out
#    (subset: first 40 family_ids × both arms × 3 doses; D-EXC cell = 40 SCOPED T-mid)
# 3. DRY-RUN the subset end-to-end (no generation) — must be clean before real gen:
python3 ~/e8-driver/x6_generate.py --corpus <pilot-subset.jsonl> --out ~/e8-run/x6/results-dry.jsonl --dry-run
# 4. REAL generation (~1,920 turns) — team-lead launches, disclosed:
ANTHROPIC_API_KEY=… python3 ~/e8-driver/x6_generate.py --corpus <pilot-subset.jsonl> \
    --out ~/e8-run/x6/results.jsonl   # model pin from frozen CONFIG.generation.model_pin
# 5. verdict (no generation); θ/δ from the pilot's own dose-1 BLANKET floor, not assumed:
cd ~/repos/closure/harness && PYTHONPATH=~/e8-driver uv run python ~/e8-driver/x6_verdict.py \
    --results ~/e8-run/x6/results.jsonl --theta <pilot-θ> --delta <pilot-δ>
```

## Verified pilot workload table (per-dose, both arms; turn counts)
40-family stratified subset:

| arm/dose | families | turns/spec | turns |
|---|---|---|---|
| SCOPED T1 / T2 / T3 | 40 each | 4 / 7 / 11 | 160 / 280 / 440 |
| BLANKET T1 / T2 / T3 | 40 each | 4 / 7 / 11 | 160 / 280 / 440 |
| D-EXC cross-val | 40 | 4 | 160 |
| **total** | | | **1,920** |

Scoring = local deterministic (no generation). Generation is the entire model workload.

## Pilot subset — BUILT (`--pilot-families N`)
`x6_build.py --pilot-families 40` writes `x6-corpus-pilot.jsonl` = first 40 kept families × both arms ×
3 doses (240 specs) + a 40-spec D-EXC cross-val cell = **280 pilot specs**. Verified: builds clean, and
the full pilot subset dry-runs end-to-end (280/280 generated in dry-run, no generation). So the launch
sequence's step 2 is a single flag, not hand-work.

## One open item before a REAL run (flagged, not blocking the build)
- **θ and δ are pilot-measured, not assumed** (X6-NOTES §1, SRD-verified: blanket decay ranges ~0%→80%
  across models, so `claude-sonnet-5`'s floor must be measured). The `x6_verdict.py` defaults (θ=0.10,
  δ=0.05) are placeholders for the toy; the real verdict passes θ/δ derived from the pilot's dose-1 BLANKET
  rate. Sequence is therefore: pilot (exploratory) → freeze θ/δ → registered run.
