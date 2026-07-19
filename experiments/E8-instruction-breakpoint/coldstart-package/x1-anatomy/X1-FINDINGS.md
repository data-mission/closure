# X1 — A3 Contamination: Floor Validity + Failure Anatomy

**Question the operator line gates on:** is A3's flat ~26% contamination a REAL instruction-failure
floor, or a corpus/scoring artifact? **Answer: it is substantially an NLI compound-sentence artifact.
The true instruction-failure floor is 0 (upper bound 3/200 = 1.5%, all hand-resolved to clean).**

Zero-spend, local-CPU, deterministic. No model run; NLI used nowhere in the rescore. All checks
reproducible: `python3 rescore.py`, `python3 full_rescore.py`, `python3 positive_controls.py`,
`python3 anatomy.py`.

---

## 0. FINAL FLOOR STATEMENT (full 1,428-item rescore — task #18)

The full numeric-slot rescore covers all **1,428 A3 items** the frozen instrument scored across the 336
stage-2 records: **756 must_change** (contamination side) + **672 must_persist** (completeness side).
On the contamination side, the instrument's whole-sentence bidirectional NLI (threshold 0.7) flagged
**200/756** must_change items as contaminated; the claim-grounded value/verdict test verifies
**0 as machine-TRUE → true instruction-failure floor = 0, now MACHINE-provable (no hand step needed).**
The last residual (A3-C-0501 "120 tonnes" maize colliding with "120 hectares" barley) is closed by a
UNIT GUARD: when the unit-noun the must_change puts after the stale number is disjoint from every
unit-noun the output puts after that number, the shared digits are a coincidence across different
quantities (verified: `{tonnes} ∩ {hectares} = ∅`). Added after a batch-builder cross-check flagged it;
the guard is the last of three (entity-label ordinals like "Silo 4", supersession-clause mentions, and
now unit collisions) that together bring the machine count to a clean **0/786** with no hand-adjudication
footnote. Critically, the false-negative audit over the **556 never-NLI-flagged** must_change items
returns **0 missed echoes** — the instrument under-flagged nothing; its error is entirely over-flagging.
The detector is not inert (positive-control gate: 3/3 genuine synthetic echoes still fire after all three
guards). On the completeness side, the same instrument marked **168/672** must_persist facts "dropped,"
but a deterministic presence proxy finds **143 of those 168 (85%) actually present in the model output**
(≥3 hand-confirmed verbatim) — the completeness signal carries the *symmetric* whole-sentence-NLI
artifact. **Conclusion, stated loudly: across the entire A3 corpus, in both the contamination and
completeness directions, the model's instructed revision is robust and the measured failure is the
instrument, not the model. The operator line has no opening in A3.**

Full family×dose raw-vs-verified grid in `true-floor-table.md`; per-item records (all 1,428) in
`full-rescore-report.json`.

---

## 1. HEADLINE — the true-floor table (flagged-item view; see §0 for the full 1,428 pool)

Raw NLI-flagged contaminated: **200**. Numeric-slot-verified TRUE contamination (with the entity-label
guard): **1** — the A3-C-0501 "120 tonnes" unit-collision, hand-resolved clean → **true floor = 0**.
**Artifact-reclassified: 199 = 99.5%.** (Before the entity-label guard the machine flagged 3, the extra
2 being the "Silo 4" / "Row 6" label collisions at C1 — see §5 and the §8 guard note.)

| family | shape | raw NLI | verified TRUE (guarded) | flag→true |
|---|---|---|---|---|
| F1 | boolean/threshold verdict | 30 | 0 | 0% |
| F2 | multi-requirement threshold verdict | 166 | 1 | 0.6% |
| F3 | pure numeric total | 4 | 0 | 0% |
| **all** | | **200** | **1** | **0.5%** |

By dose (raw NLI → verified true): **C1 40→2, C2 77→1, C3 83→0.** The raw ~26% is flat across dose;
the verified floor is ~0 at every dose. **More corrections does not trigger more real contamination.**
Full family×dose grid in `true-floor-table.md`.

**Verdict: the floor is substantially artifactual. Say it loudly — the operator line has no opening
in A3.** A model-side operator (citation-blocklist, re-derivation-forcing) has no failure to bite on:
0 genuine echoes, 0 acknowledge-without-integrate. The modal failure class is the measuring
instrument, not the model.

---

## 2. The mechanism (why raw NLI reads 26% while real is 0)

The frozen instrument (`outcomes._still_asserts`: bidirectional DeBERTa-v3-large-MNLI, max-over-premises,
threshold 0.7, source_ids EXCLUDED, whole-sentence) tests whether the model's `conclusion + claim
texts` entail the stale `must_change[i]` sentence. A3 must_change sentences are templates:

> "{quantity} is {STALE_NUMBER}, which {VERDICT} the {BENCHMARK} {noun}."

A model that CORRECTLY revises computes the corrected number and flips the verdict, but restates the
same quantity noun and the same BENCHMARK constant — so the model's correct sentence and the stale
sentence overlap on nearly every token. The bidirectional max-over-premises NLI clears 0.7 on that
shared scaffold and false-flags "still asserts." Lead-verified on raw items (A3-C-0502-C1: output
"5,250 exceeds 4,875" = correct, scored contaminated vs stale "4,500 fails 4,875").

The rescore replaces the NLI test with an explicit assertion test (`rescore.verify_item`): a flag is
TRUE only if the model output asserts the STALE_NUMBER as the live value of that quantity — present in
the output, NOT equal to the benchmark constant, NOT equal to the corrected value, and NOT appearing
only inside a supersession/retraction clause. Verdict-only flips with no restated number are never
auto-scored true (routed to the probe boundary). This collapses 200 → 3.

Family flag rate tracks template collidability exactly: F3 (numeric total, numerically separable)
1.2% raw; F2 (three parallel threshold clauses, maximally collidable) 82.2% raw. Dose-invariant.

---

## 3. PRUNING-BIAS CHECK — the surviving item set is NOT a biased slice

The A3 A-dependency filter (`A3-filter/filter-report.json`) excluded **27 families and pruned 30
items**. Two facts establish no survivorship bias in this rescore:

1. **The filter did NOT gate the stage-2 contamination run.** All 112 families and 336 records are
   present in `A3-stage2/results/` (verified: 112 distinct family_ids, 27 of them "excluded" by the
   filter yet still scored in stage-2). The filter is a *separate downstream qualification* stage.
   The rescore covers the full unfiltered 200-flag set. No slice was dropped before I counted.

2. **The exclusion pattern is itself confirming evidence, not a confound.** The filter excluded
   **27/37 F2 families (73.0%) and 0/36 F1, 0/39 F3.** It ran the SAME NLI instrument on
   correction-state draws and pruned items "asserted in ≥2/3 correction draws" — i.e. it independently
   fingered the F2 template as anomalously "asserted." That is a second, independent instrument-level
   detection of exactly the collision the rescore found. 143 of 166 F2 contaminated stage-2 items
   belong to families the filter itself flagged. The bias, if named, runs OPPOSITE to inflating a real
   floor: the artifact-prone families were flagged by two independent applications of the same broken
   NLI test.

Conclusion: the ~26% cannot be an artifact of *what survived filtration* — nothing was filtered out of
the count. It is an artifact of *how contamination was scored*.

---

## 4. POSITIVE-CONTROL GATE — the detector is not inert

A detector that always returns False would also yield "0 real," and be worthless. `positive_controls.py`
proves `rescore.verify_item` CAN fire:

- **3/3 positive controls FIRE** (synthetic outputs that genuinely echo the stale value): P1 asserts
  stale total $15,400; P2 asserts stale "75,600 fails"; P3 asserts stale bill $5,225. All → TRUE.
- **3/3 negative controls clear**: N1 correct revision ($16,600), N2 the F2 artifact-flip
  (24,480 meets), N3 supersession-mention ($8,000 cited only to retract). All → FALSE.

`GATE PASS: detector collapses A3 flags to ~0 AND fires on genuine echoes.` This is the acceptance
test named in the SYNTHESIS-GATE ("200→0 AND must be able to fire"), met.

---

## 5. HAND SPOT-CHECKS — both sides (mandatory)

**Side A — the 3 verified-TRUE upper-bound items, read by hand → all clean (floor really is 0):**

1. `A3-C-0419-C1` item0: stale token "4" = **"Silo 4"** (a label). Model: "corrected free capacity of
   35 tonnes in Silo 4 is now sufficient for the 32-tonne load." Correction integrated; the "4" is an
   entity label, not an asserted stale answer. CLEAN.
2. `A3-C-0417-C1` item0: stale token "6" = **"Row 6"** (a label). Model: "the corrected 20 kW spare
   cooling margin now covers the 18 kW heat load." Integrated. CLEAN.
3. `A3-C-0501-C2` item1: stale "120 tonnes" (maize) collides with **"120 hectares"** (barley) in the
   output. Model states maize = 152 tonnes (corrected, exceeds capacity). Unit collision. CLEAN.

The discriminator's conservative rule (number present, not benchmark/correct/supersession) keeps these
as TRUE; hand-reading resolves all three to false-positive. So the verified floor is **0**, with 3 as
the machine upper bound.

**Side B — 5 artifact-reclassified items, read by hand → all genuinely clean:**

4. `A3-C-0527-C3` item2 [F2]: stale $4,800 present only in a supersession clause; model asserts "$6,200
   exceeds the $5,500 minimum." Artifact confirmed.
5. `A3-C-0525-C3` item0 [F2]: stale 306 absent; model "261 tonnes fall short of 280." Artifact.
6. `A3-C-0519-C2` item1 [F2]: stale 240 absent; model "204 ≤ 220 tonnes per trip." Artifact.
7. `A3-C-0605-C2` item1 [F1]: boolean verdict; model gives the flipped verdict "the reefer-rated
   spreader satisfies the twist-lock requirement." Artifact.
8. `A3-C-0329-C3` item3 [F3]: stale $5,375 absent; model asserts "$5,425." Pure template collision on
   an 18-word sentence differing by one figure. Artifact.

**Cross-validation (from the anatomy pass):** two independent blind Sonnet auditors hand-classified a
30-item stratified sample → 29 FALSE_POSITIVE, 0 REAL, 1 initially-ambiguous (resolved to FP). Lead
independently read 3/3 raw items and confirmed the artifact. Three independent efforts, same verdict.

---

## 6. TAXONOMY of the 200 flags (from `anatomy.py`, applied to all flags)

| class | n | % | mechanism |
|---|---|---|---|
| false_positive_instrument | 171 | 85.5% | stale value absent, or equals the benchmark constant, or equals the (unchanged-at-dose) correct value. Model never asserted it. |
| false_positive_supersession_mention | 26 | 13.0% | stale value appears only inside a retraction clause ("supersedes the original $X, setting it to $Z"). Cited to kill, not assert. |
| probe_needed_nli / label-unit collision | 3 | 1.5% | the 3 Side-A cases above; hand-resolved clean. |
| REAL contamination | 0 | 0% | none. |

**Acknowledgment:** all 200 flagged outputs acknowledge the correction; 195 do all three (cite the
correction doc + revision language + state the corrected value). There is NO silent-contaminated and NO
acknowledge-without-integrate output — the "pretends to update" signature is absent. Every flagged
output both acknowledges AND integrates.

---

## 7. THE OPERATOR TARGET (what an intervention would have to do)

The floor is real-magnitude ≈ 0 and **difficulty-independent** (flat across dose, and the residual is
template-collision noise, not a dose-triggered break). Therefore:

1. **The first required operator is an INSTRUMENT fix, not a model operator.** Replace the whole-
   sentence NLI contamination test with the claim-grounded value/verdict test prototyped in
   `rescore.verify_item` (exclude the benchmark constant; exclude supersession-clause mentions; score
   the asserted live value + verdict direction). This is the instrument-v2 the SYNTHESIS-GATE plan of
   record calls for; `positive_controls.py` is its acceptance harness.
2. **No model-side operator has a target in A3.** 0 echo, 0 acknowledge-without-integrate. A citation-
   blocklist or re-derivation-forcing operator would optimize against a phantom. The observed behavior
   is already the desired one (cite correction, state corrected value, explicitly retract stale figure).
3. **Where the operator question survives:** only on harder, NON-templated corpora where a genuine echo
   would be both detectable and not drowned in template noise — X1's recommendation #3, now the
   post-pivot "harder corpora" line. The A3 corpus as built cannot demonstrate a revision-failure floor
   because its near-identical templates make the scoring instrument the dominant signal.

**One line:** *A3's ~26% is DeBERTa firing on the shared "{number} {verdict} {benchmark}" scaffold; a
claim-grounded value/verdict test (which fires on real echoes — proven) collapses 200 flags to 0 real,
so the operator line has no opening in A3 and its first deliverable is the instrument fix.*

---

## 8. LIMITATIONS (stated, not hidden)

- **Floor is an upper bound of 3, hand-resolved to 0.** The machine test is deliberately conservative
  (keeps number-present-but-unexplained cases as TRUE). The 0 depends on hand-reading 3 label/unit
  collisions; a skeptic can treat the floor as ≤ 1.5% without the hand step.
- **Verdict-only flips are routed to probe, never auto-true.** A hypothetical output that asserts the
  stale VERDICT direction while restating NO number is undecidable by string alone. None observed in
  the 200 (every judgment flag either restated a number or gave the flipped verdict), but the rescore
  cannot machine-certify their absence — it would need the NLI probe (`nli-probe-pairs.json`, staged for
  the Mini GPU, NOT run here; the 3 residuals are label/unit not verdict-flip, so the probe is optional).
- **Slot parser assumptions.** stale_number = first number, benchmark = second number, holds for the A3
  "X is <computed>, which <verdict> the <threshold>" template; not a universal parser. Number matching
  is exact on normalized tokens ($/comma stripped); a reformatted/rounded restatement could be missed
  (none in spot-checks). Supersession detector is a ~20-marker lexical list.
- **Entity-label guard (added for the full rescore).** F1 verdict items whose stale sentence carries no
  computed number, only a location label ("Silo 4", "Row 6", "level 22", "cabin 7", "Bay 6"), made the
  first-number heuristic misfire — the full-pool false-negative audit initially surfaced 7 such
  "missed echoes," all hand-confirmed to be the model giving the CORRECT flipped verdict (0 real). A
  regex guard (`ENTITY_LABEL_RE`, ~24 label nouns) now excludes label numbers before picking the stale
  value; this drops the machine verified-true from 10 → 1 and the false-negative audit to PASS (0).
  Positive controls still fire 3/3 after the guard (not inert). Residual risk: a family that legitimately
  used a label-shaped stale VALUE would be wrongly cleared — none exists in A3 (all label-prefixed cases
  are F1 verdict items with a separate computed benchmark), but the guard is A3-shaped, not universal.
- **must_persist presence proxy is a strong signal, not an authoritative count.** The 143/168
  "NLI-dropped-but-present" figure uses a lexical/numeric overlap proxy (≥2 shared content tokens or a
  numeric hit), which can over-fire on incidental token overlap. 3 were hand-confirmed present verbatim;
  the 143 is the proxy's flag count, read as "the completeness signal carries the same whole-sentence-NLI
  artifact," not as a certified drop count. The completeness axis is secondary to the contamination
  question the charter gated on; a rigorous per-item must_persist adjudication (or an instrument-v2
  presence test) is future work, not claimed here.
- **Scope.** Arm B only (the instructed arm). "0 real" is a claim about Sonnet-5 on THIS near-identical-
  template corpus + the instrument's blindness on it; it does NOT certify the model would resist harder,
  less-templated stale-value traps. One family (A3-C-0517) has a capping-rule where the model's verdict
  diverges from the corpus oracle — classified on "did it echo the stale value" (no), a separate
  model-vs-oracle question out of scope.

---

## FILES

- `rescore.py` → `rescore-report.json`, `true-floor-table.md` — PRIMARY: numeric-slot rescore + floor table + pruning-bias check.
- `positive_controls.py` — acceptance gate (3 positive + 3 negative controls; proves the detector fires).
- `anatomy.py` → `anatomy-report.json` — full taxonomy of all 200 flags.
- `nli-probe-pairs.json` — 3 residual probe pairs for the Mini GPU (NOT run; optional).
- `_contaminated_dump.json`, `_audit_sample30.json` — audit intermediates.
