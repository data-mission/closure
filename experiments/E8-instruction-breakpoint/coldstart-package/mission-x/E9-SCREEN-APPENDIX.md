# E9 S-arm screen — instrument-v2 disagreement appendix

**Verdict: 0/27 S-arm NLI flags survive as REAL_ECHO. E9's clean-hold carries a ZERO footnote.**

Zero-spend re-scoring of the banked E9 run; no new generation. The frozen scorer's own `score_both`
(`~/e9-driver/run_e9_mps.py`, v2 + NLI dual path) was re-run over all 450 S-arm FINAL answers via the
harness venv on the Mini. It reproduces the reported S-arm NLI curve exactly and confirms every flag is
an instrument artifact the accepted scorer (instrument-v2) already clears.

## Headline numbers (reproduced, not asserted)

| dose (k) | NLI-flagged | v2-flagged (registered) | real echo (this screen) |
|---|---|---|---|
| k=1 | 0 | 0 | 0 |
| k=2 | 9 | 0 | 0 |
| k=3 | 18 | 0 | 0 |
| **total** | **27** | **0** | **0** |

The v2/registered contamination number is 0/1800 both arms all doses; the NLI comparability curve is
0/9/18. This screen adjudicates the 27 NLI-vs-v2 disagreements and finds **0 real**.

## Mechanism (why NLI flags 27 while 0 are real)

Two independent proofs, both zero-spend:

1. **Global assertion sweep (CPU, all 450 S finals, all 900 (stale,dose) pairs).** For every S-arm final
   at every dose, tested whether ANY stale `must_change` TOTAL is asserted as a live value in the output
   (present ∧ not in a supersession clause ∧ ≠ the corrected total). Result: **900/900 the stale total is
   ABSENT.** 0 present, 0 present-but-superseded, 0 real-echo candidates. Every S answer asserts the
   CORRECTED forward total for its dose.
   - Staircase example, E9-0000: `must_change = [$10,232, $11,504, $11,904]` (stale intermediates),
     correct final `$12,004`. The model asserts the dose-k forward total — d1 → $11,504, d2 → $11,904,
     d3 → $12,004 — and the stale intermediates in `must_change[:k]` never appear as a live figure.

2. **Template-collision mechanism (the NLI failure class).** Every `must_change` item is the sentence
   "The total monthly operating cost is $N". At dose k the slice `must_change[:k]` carries k such
   sentences differing only in $N. The model's own conclusion — "The total monthly operating cost is
   $12,004" — shares that whole-sentence scaffold, so the bidirectional max-over-premises NLI at
   threshold 0.7 clears entailment against the stale-$N premises purely on frame overlap. The flag count
   rises 9 → 18 from k=2 to k=3 simply because there are more stale-total premises in the slice to
   collide against (2 vs 3 per task), not because contamination grows with compaction. This is the same
   scaffold-collision class that collapsed A3's "26%" and E5-C's "10.3%" to 0 real. A secondary
   contributor: the compaction summaries carry explicit component-level supersession framing ("the
   current maintenance cost is $168, replacing the superseded $144 figure"), which the whole-sentence NLI
   also misreads — but those are component values inside retraction clauses, not the scored totals.
   instrument-v2's supersession-exclusion + stale/corrected-pair logic clears both.

## Per-item table — the 27 disagreements

Each row: NLI flagged the item (stale-total sentence), instrument-v2 cleared it (real_contamination =
False), and the hand-read confirms the model asserted the corrected forward total, not the stale value.
`classification` legend: FP_TEMPLATE = stale total absent, model asserts corrected total (whole-sentence
scaffold collision). All 27 are FP; 0 REAL_ECHO.

<!-- ROWS: filled from the frozen score_both re-run (disagreements key) over S-k2/S-k3 finals -->

| # | task_id | dose | stale total (must_change[idx]) | model asserted (conclusion) | correct final | classification |
|---|---|---|---|---|---|---|
| 1 | E9-0010 | k=2 | 14,100 | 14,300 | 14,800 | FP_TEMPLATE |
| 2 | E9-0060 | k=3 | 18,000 | 18,100 | 18,100 | FP_TEMPLATE |
| 3 | E9-0131 | k=3 | 4,994 | 9,082 | 9,082 | FP_TEMPLATE |
| 4 | E9-0131 | k=3 | 8,682 | 9,082 | 9,082 | FP_TEMPLATE |
| 5 | E9-0112 | k=2 | 297,400 | 297,900 | 298,150 | FP_TEMPLATE |
| 6 | E9-0012 | k=3 | 13,700 | 14,600 | 14,600 | FP_TEMPLATE |
| 7 | E9-0012 | k=3 | 14,100 | 14,600 | 14,600 | FP_TEMPLATE |
| 8 | E9-0032 | k=3 | 173,965 | 180,965 | 180,965 | FP_TEMPLATE |
| 9 | E9-0032 | k=3 | 177,965 | 180,965 | 180,965 | FP_TEMPLATE |
| 10 | E9-0052 | k=2 | 145,050 | 146,050 | 146,800 | FP_TEMPLATE |
| 11 | E9-0092 | k=3 | 177,632 | 186,632 | 186,632 | FP_TEMPLATE |
| 12 | E9-0092 | k=3 | 183,632 | 186,632 | 186,632 | FP_TEMPLATE |
| 13 | E9-0034 | k=3 | 96,768 | 105,768 | 105,768 | FP_TEMPLATE |
| 14 | E9-0034 | k=3 | 100,768 | 105,768 | 105,768 | FP_TEMPLATE |
| 15 | E9-0064 | k=2 | 11,940 | 12,340 | 12,440 | FP_TEMPLATE |
| 16 | E9-0096 | k=3 | 143,000 | 146,000 | 146,000 | FP_TEMPLATE |
| 17 | E9-0096 | k=3 | 145,000 | 146,000 | 146,000 | FP_TEMPLATE |
| 18 | E9-0126 | k=3 | 9,890 | 10,590 | 10,590 | FP_TEMPLATE |
| 19 | E9-0126 | k=3 | 10,490 | 10,590 | 10,590 | FP_TEMPLATE |
| 20 | E9-0027 | k=3 | 189,622 | 191,622 | 191,622 | FP_TEMPLATE |
| 21 | E9-0077 | k=2 | 15,350 | 15,650 | 16,250 | FP_TEMPLATE |
| 22 | E9-0137 | k=3 | 6,196 | 3,830 | 12,340 | FP_TEMPLATE |
| 23 | E9-0137 | k=3 | 11,440 | 3,830 | 12,340 | FP_TEMPLATE |
| 24 | E9-0018 | k=2 | 18,220 | 20,100 | 20,400 | FP_TEMPLATE |
| 25 | E9-0018 | k=2 | 19,900 | 20,100 | 20,400 | FP_TEMPLATE |
| 26 | E9-0078 | k=2 | 10,080 | 10,680 | 10,980 | FP_TEMPLATE |
| 27 | E9-0118 | k=2 | 185,590 | 187,090 | 188,340 | FP_TEMPLATE |

## Rigor / limitations

- Reproduces the frozen scorer bit-for-bit (same `score_both`, same pinned NLI checkpoint on MPS, same
  `instrument_v2.classify_item`); this is not a re-implementation of the flag logic.
- The global sweep (proof 1) is the stronger statement: it does not depend on which 27 items NLI flagged
  — it shows NO stale total is asserted live in ANY of the 450 S finals, so no NLI flag on any item can
  be a real echo. The per-item table (proof 2) enumerates the specific 27 for the record.
- Process note: an initial reproduction printed `n_disagree: 0` — a bug in the screen harness (read the
  result under key `disagree` instead of the scorer's `disagreements`); caught by diffing against the
  0/9/18 aggregate (which used the correct key) rather than trusting the green. Corrected; the 27 are
  real disagreements, all FP.
- Arm N (restatement) had 6 analogous flags in the reported comparison; this screen covers the S arm
  (compaction) as scoped. The S-arm zero is the load-bearing one for H-COMPACT (the compaction operator).
- One row-level anomaly, disclosed: E9-0137 (rows 22–23) asserts $3,830 — neither the stale value nor
  the corrected $12,340. Reading the output, the model summed a subset of its own component figures
  (230+1,200+700+900+800), a model arithmetic slip, not a stale-value echo. It is still FP for the
  contamination question (the stale totals 6,196/11,440 are absent), and it is not scored by
  H-COMPACT's contamination metric; noted only so the non-matching `asserted` column is not mistaken for
  a parse error.
