# X-HUMAN — annotation packets (ready to hand to an annotator)

This folder is the **built, ready-to-run** X-HUMAN judge-validation set. The protocol is
`X-HUMAN-PROTOCOL.md`; this README is the operator's how-to. **No file here contains a human label
yet** — that is the point. The labels are produced by Vlad or recruited annotators; everything else
(packets, calibration, stats) is authored and deterministic.

## What to hand an annotator

1. **First:** `calibration/calibration-gold.json` — a 6-item teaching set with answers shown. The
   annotator reads it to learn the rubric. They must be comfortable with ≥5/6 before real labeling.
2. **Then:** one or more batch files from `packets/`, e.g. `packets/a3-contamination-batch01.json`.
   Each batch is **50 items**, self-contained, with the rubric and instructions embedded at the top.
   There are 17 batches:
   - `a3-contamination-batch01..08` — the A3 must_change judgment (200 flagged census + 200 clean sample).
   - `a3-completeness-batch01..06` — the A3 must_persist judgment (168 dropped census + 100 kept control).
   - `e5-contamination-batch01..03` — the E5 must_change judgment (15 contaminated census + 90 control).

Each item shows: the **sources**, the **correction**, the **question**, the **model's full output**,
and the single **scored sentence** with its named stale value. The annotator answers the rubric
question (`YES`/`NO`/`UNSURE`) and fills the item's empty `label` block:

```json
"label": {"judgment": "NO", "annotator_id": "vlad", "notes": "output states corrected $15,750"}
```

**Every item must be labeled by ≥2 independent annotators** (blind to each other). A 3rd annotator
adjudicates any item the first two disagree on or mark UNSURE.

## Collecting labels

Each annotator returns their answers as one file in `labels/`:

```json
{"annotator_id": "vlad", "annotator_kind": "human",
 "labels": {"A3-C-0325-C1#mc1": "NO", "F2-0016#A#mc0": "NO", ...}}
```

The `annotator_kind: "human"` field is **required** — `kappa_fp_fn.py` refuses to compute over any
label file not declared human. (`labels/TEMPLATE.json` is a copy-me starting point.)

## Producing the verdict

Once ≥2 human label files are in `labels/`:

```
python3 kappa_fp_fn.py          # prints per-cell Cohen's kappa + confusion matrices + R1-R5 adjudication
```

It computes, **never pooled**, per (dimension × regime × family-type):
- inter-annotator **Cohen's κ** with raw-agreement and the raw−κ **deflation** beside it (the 33–41pp
  effect the standard warns about);
- **NLI-original vs human** and **instrument-v2 vs human** confusion matrices (TP/FP/FN/TN, FP-rate,
  FN-rate);
- the frozen decision rules **R1–R5** (X-HUMAN-PROTOCOL.md §7): R1 v2-validated, R2 v2-refuted,
  R3 false-negative leak, R4 completeness characterization, R5 E5-verdict integrity.

Until then it prints `NO_HUMAN_LABELS` and stops — a green run over zero human labels is not a result.

## Provenance and integrity

- `packets/MANIFEST.json` — the frozen seed (`20260718`), source-file SHAs, and exact strata counts.
  Re-running `build_packets.py` reproduces the identical draw.
- `packets/_provenance/item_provenance.json` — the stratum + instrument flags for every item. This is
  **deliberately kept out of the packets** so annotators never see which instrument flagged an item or
  what stratum it came from. `kappa_fp_fn.py` joins it back **after** labels exist.
- Verify integrity anytime: `python3 build_packets.py --check` (oracle: census counts, no machine-label
  leak, determinism) and `python3 kappa_fp_fn.py --selftest` (oracle: κ, deflation, exact-binom,
  confusion tally, consensus). Both must print PASS.

## The boundary (non-negotiable)

The agent team authored the packets, calibration, and stats code. **It did not, and will not, fill any
label.** Any `judgment` value in `labels/` is a human's. Sonnet auxiliary pre-labels, if ever produced
for two-stage allocation, live in a separate channel `kappa_fp_fn.py` structurally refuses to read.
