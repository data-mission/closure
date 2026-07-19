# The NLI supersession artifact: how sentence-shape entailment scoring fabricates belief-revision failures

**A scientific note on a measurement-instrument failure class discovered across one belief-revision research program.**

Whole-sentence natural-language-inference (NLI) entailment, used to score whether a model still asserts a
superseded claim, produces **systematic, hypothesis-shaped false positives** on templated correction
corpora. It fires on the requirement *scaffold* shared between a stale sentence and its corrected
replacement — not on any assertion of stale content. On the corpora studied here the artifact reached
plausible-magnitude rates (10–26%) and, in one case, a clean rising dose-response curve — the exact
signatures a real belief-revision failure would produce. It appeared **five independent times in one
program**, each occurrence positioned to be published as a real effect. Under a claim-grounded
replacement instrument, every one of those "failures" collapses to zero real contamination, and the
studied model's instructed revision is robust in every regime tested.

The warning generalizes beyond this program: **any evaluation that scores "did the model update its
belief" with sentence-level entailment against the pre-correction sentence is exposed to this artifact**,
and the exposure is worst precisely where corpora are cleanest — template-generated, so that stale and
corrected sentences differ by a single value.

Provenance base: `closure@689833c` + the mission-x audit set. Adjudication of record:
`experiments/E8-instruction-breakpoint/coldstart-package/mission-x/SYNTHESIS-GATE.md`. Every quantitative
claim below carries its source file inline. What is proven and what is pending human validation are marked
separately throughout and never blurred.

---

## 1. The finding

### 1.1 The measurement setup

The program measures **belief revision**: a task carries an assumption whose downstream conclusions depend
on it; later evidence supersedes the assumption; the model must retract the stale conclusion and assert the
corrected one. The registered outcome metric — *contamination* — is the fraction of conclusions annotated
`must_change` that the model's final output "still asserts," scored by a frozen bidirectional
DeBERTa-v3-large-MNLI entailment check at threshold 0.7, max over premises, whole-sentence
(`experiments/E5-reclosure/PROTOCOL.md` step 5; mechanism traced in
`.../x1-anatomy/X1-FINDINGS.md` §2).

The stale sentences are template-generated. The canonical A3 shape
(`.../x1-anatomy/X1-FINDINGS.md` §2):

> "{quantity} is {STALE_NUMBER}, which {VERDICT} the {BENCHMARK} {noun}."

A model that revises *correctly* recomputes the number and flips the verdict, but restates the same
quantity noun and the same benchmark constant. Its correct sentence and the stale sentence overlap on
nearly every token. The bidirectional max-over-premises NLI clears 0.7 on that shared scaffold and reports
"still asserts" — a false positive on an output that in fact asserted the *corrected* value.

### 1.2 Not noise: the artifact wears the shape of the hypothesis

The failure is not random mis-scoring that would wash out in aggregate. It is structured three ways, each
of which mimics a real effect:

- **Plausible magnitude.** A3's raw flag rate is ~26% (`.../mission-x/MISSION-X-VERDICT.md` §2.2:
  registered θ=5% flag rate 26.7 / 29.4 / 24.1%). E5 Arm-C's raw rate is 10.3%
  (`.../x1-anatomy/CORRECTION-NOTE-DRAFT.md` §Summary). Both are in the range independent literature
  reports for instructed-disregard failure (10–20% drops; `experiments/E5-reclosure/README.md`
  prior-art list). A reviewer sees a number that *matches the field* and does not suspect the ruler.

- **Correct-shaped curve.** In the E9 compaction arm the frozen NLI produced a rising dose-response
  curve — 0 / 9 / 18 flags at doses k=1/2/3 (`.../mission-x/E9-SCREEN-APPENDIX.md` headline table) — the
  monotone rise that the compaction-accumulation hypothesis (H-COMPACT) explicitly predicts. The curve
  rises for a purely mechanical reason: dose k carries k stale-total premises in the scored slice, so
  there are simply more sentences to collide against (2 vs 3 per task), not more contamination
  (`.../mission-x/E9-SCREEN-APPENDIX.md` §Mechanism proof 2). A rising artifact is far more dangerous
  than a flat one — it is *confirmation*, not noise.

- **Family-structured, dose-invariant.** The A3 flag rate tracks template collidability exactly: F3
  (pure numeric total, numerically separable) 1.2% raw; F2 (three parallel threshold clauses, maximally
  collidable) 82.2% raw (`.../x1-anatomy/X1-FINDINGS.md` §2, §6). The rate is flat across correction
  dose (`.../x1-anatomy/true-floor-table.md`: by-dose raw NLI 40 / 77 / 83, verified-true 0 / 0 / 0). It
  varies with *sentence shape*, not with anything the model did.

### 1.3 Five independent appearances in one program

Every "revision failure" the program measured re-adjudicated to this one artifact class. From the findings
catalog (`.../mission-x/MISSION-X-VERDICT.md` §1):

| # | corpus | raw signal | re-adjudicated | source |
|---|---|---|---|---|
| 1 | E8-A2 | wrong-side counting (scorer counted retention, not the `must_persist` drop) | fixed → drops 5.0/4.6/5.4% below θ, no break | `verdict-numbers.pre-a2fix.json` + PHASE0 §3 |
| 2 | E8-A1 | polarity inversion — the axis measured revision *success*, not contamination | 450/450; rebuilt + rescored by X4, depth NO-BREAK | X1/P2/red-check + X4 |
| 3 | E8-A3 | ~26% contamination floor | 200 flags → **0 real**; full sweep 0/786 machine-provable | `.../x1-anatomy/X1-FINDINGS.md` |
| 4 | E5 Arm-C | 10.3% vs Arm-B 0.9% "separation" | 0/11 real echo; separation is artifact | `.../CORRECTION-NOTE-DRAFT.md` |
| 6 | E9 compaction | rising S-curve 0/9/18 (would confirm H-COMPACT) | **0/27 real**, all supersession-scaffold | `.../mission-x/E9-SCREEN-APPENDIX.md` |

(Findings #5 and #7 are distinct, real defects, not this artifact — treated in §4.4 and §4.5; they are
listed here only so the reader knows the catalog is complete and the artifact is not being made to absorb
every anomaly.)

Common root, stated once (`.../mission-x/MISSION-X-VERDICT.md` §1 closing): bidirectional
DeBERTa-v3-large-MNLI at 0.7, max-over-premises, whole-sentence — fires on the requirement scaffolding
shared between stale and corrected sentences. Four of these (#1–#4) were caught by the program's own audit
*before* any external reviewer; #6 was caught by a mandatory cross-check screen built into the E9 run.

The generalization the reader outside this program should carry away: this is not a quirk of one corpus. It
is a property of the *method* — sentence-level entailment against the pre-correction sentence — interacting
with any corpus whose stale and corrected claims are structurally near-identical. Template generation, the
practice that makes a corpus clean and controllable, is exactly what maximizes the collision.

---

## 2. The supersession paradox

The sharpest and most counterintuitive part of the finding: **the better the model behaves, the guiltier
the instrument makes it look.**

Good revision hygiene means explicitly naming what is being retracted. A model that writes

> "the current maintenance cost is $168, replacing the superseded $144 figure"

is doing revision *correctly* — it acknowledges the correction, retracts the stale value by name, and
asserts the corrected one. This is the target behavior. It is also precisely what the whole-sentence NLI
convicts: the stale value `$144` is present in the output, inside a retraction clause, and the entailment
check — which has no notion of a retraction clause — reads its *mention* as an *assertion*
(`.../mission-x/E9-SCREEN-APPENDIX.md` §Mechanism, second contributor;
`.../x1-anatomy/X1-FINDINGS.md` §6, `false_positive_supersession_mention` = 26 of 200 flags = 13%).

The metric therefore rewards the model for *hiding* its revision (silently swapping the number, leaving no
retraction trace) and punishes it for making the revision auditable. An operator designed to optimize this
metric would train the model *away* from good hygiene. The convicting move — mention-read-as-assertion — is
strongest exactly where the correction is most explicit.

### 2.1 The worked example: E9's rising curve

E9 tested whether iterated summarize-and-continue compaction accumulates revision error against a matched
no-compaction baseline (`.../mission-x/MISSION-X-VERDICT.md` §2.7). The frozen NLI produced the rising
S-curve — the H-COMPACT signature. The screen adjudicated all 27 flags and found **0 real**
(`.../mission-x/E9-SCREEN-APPENDIX.md`). The per-item table is the worked example of the paradox:

| dose (k) | NLI-flagged | v2-flagged | real echo |
|---|---|---|---|
| k=1 | 0 | 0 | 0 |
| k=2 | 9 | 0 | 0 |
| k=3 | 18 | 0 | 0 |
| total | 27 | 0 | 0 |

Two independent proofs, both re-scoring only, no new generation
(`.../mission-x/E9-SCREEN-APPENDIX.md` §Mechanism):

1. **Global assertion sweep.** For every one of the 450 S-arm finals, at every dose, test whether *any*
   stale `must_change` total is asserted as a live value (present ∧ not in a supersession clause ∧ ≠ the
   corrected total). Result: **900/900 the stale total is absent.** Every S answer asserts the corrected
   forward total for its dose. Worked example E9-0000: `must_change = [$10,232, $11,504, $11,904]` (stale
   intermediates), correct final `$12,004`; the model asserts the dose-k forward total (d1 → $11,504,
   d2 → $11,904, d3 → $12,004) and the stale intermediates never appear as a live figure. This proof does
   not depend on which 27 items NLI flagged — no stale total is asserted live in *any* final, so no flag
   on any item can be a real echo.

2. **Template-collision mechanism.** Every `must_change` item is "The total monthly operating cost is $N".
   At dose k the slice carries k such sentences differing only in $N. The model's own conclusion shares
   that whole-sentence scaffold, so the bidirectional NLI clears entailment against each stale-$N premise
   on frame overlap alone. **The count rises 9 → 18 from k=2 to k=3 because there are more stale-total
   premises in the deeper slice to collide against (2 vs 3 per task), not because contamination grows with
   compaction.** The rise is a counting property of the corpus slice, wearing the shape of behavioral
   decay.

This is the mechanism laid bare: a curve that any reviewer would read as *the effect confirming itself*,
produced entirely by the number of superseded premises available to collide against. The N-arm
(no-compaction) frozen-NLI is 2/2/2 flat — the same two items at every dose — confirming the signal is
sentence-structure, not dose (`.../mission-x/MISSION-X-VERDICT.md` §2.7).

---

## 3. The fix, battle-proven

The replacement instrument (**instrument-v2**) scores *asserted content*, not *sentence shape*. Every
element below is credited with the specific real error it caught in this program's record — the design is
not proposed, it is the design that already found the artifacts above.

### 3.1 Claim-grounded value/verdict scoring

instrument-v2 is a revision-fidelity test. Given a task carrying a stale→corrected value/verdict pair, it
scores whether the output echoes the *stale* value and/or the *stale verdict direction* as a live
proposition — a flag is TRUE only if the output asserts the stale number as the live value of that
quantity (`.../x1-anatomy/INSTRUMENT-V2-NOTES.md` §What; `.../x1-anatomy/X1-FINDINGS.md` §2 rescore
rule). A *corrected*-value assertion cannot trip either channel. Two channels — `value_echo` and
`verdict_echo` — both gated on the stale value being asserted live.

**What it caught:** replacing whole-sentence NLI with the assertion test collapsed A3's 200 flags to 3
machine-residual, then to 0 (`.../x1-anatomy/X1-FINDINGS.md` §1, §2), and E5 Arm-C's 11 to 0 real echo
(`.../CORRECTION-NOTE-DRAFT.md` evidence table). This is the load-bearing element; the guards below close
the residual.

### 3.2 The exclusion guards, each earning its place

Four exclusions, each added to kill a specific residual false positive
(`.../x1-anatomy/X1-FINDINGS.md` §0, §5, §8; `.../x1-anatomy/INSTRUMENT-V2-NOTES.md` §What):

- **Supersession-clause exclusion.** A stale value appearing only inside a retraction clause ("supersedes
  the original $X") is a mention, not an assertion — excluded. *Caught:* the 26 supersession-mention
  flags in A3 (13% of the 200), and the E9 component-level retraction framing (§2 worked example).
- **Correct-final exclusion.** The corrected value is never scored as an echo of the stale one.
- **Threshold-constant exclusion.** The shared benchmark constant is unchanged by the correction and
  present in every sentence; excluded so it cannot anchor a collision.
- **Entity-label / unit guards.** A number that is a location label ("Silo 4", "Row 6") or carries a unit
  disjoint from the stale quantity's unit is a coincidence, not an echo. *Caught:* the last three A3
  machine-residuals — `A3-C-0419-C1` ("Silo 4"), `A3-C-0417-C1` ("Row 6"), and `A3-C-0501` ("120 tonnes"
  maize colliding with "120 hectares" barley) — dropping the machine verified-true count from 10 → 1 → 0
  (`.../x1-anatomy/X1-FINDINGS.md` §5 Side-A, §8 entity-label-guard note).

### 3.3 Positive controls that MUST fire

A detector that returns False on everything also reports "0 real" and is worthless. instrument-v2's
acceptance requires it to *fire* on genuine echoes (`.../x1-anatomy/X1-FINDINGS.md` §4;
`.../CORRECTION-NOTE-DRAFT.md` §certification):

- 3/3 hand-authored positive controls fire (synthetic outputs that genuinely assert the stale value); 3/3
  negative controls clear (correct revision, the F2 artifact-flip, a supersession mention).
- Adversarial hardening: 60/60 bare-stale-sentence hard positives detected, 40/40 subtle F2 echoes,
  30/30 verdict-channel echoes; 0/60 false fires on negative controls (corrected value injected).

The gate named in the plan of record — "200 → 0 **AND** must be able to fire" — is met
(`.../mission-x/SYNTHESIS-GATE.md` §3 acceptance).

### 3.4 Withhold-not-bless acceptance gates

The strongest evidence that the corrected regime is honest is that its gate **refused to certify a run it
could not validly score** — the same day it was built. X6's behavioral pilot generated 280/280 specs, but
its acceptance gate failed (AC2: FF-cell rate 0.7368 vs 0.05 tolerance) and the harness respected its
exit-2 rule and refused to emit a verdict (`.../mission-x/MISSION-X-VERDICT.md` §2.6). The root cause was
a corpus-construction defect, not model behavior: the X6 worksheet gave the model the *rule* ("2% of
insured value") and the *exception* but not the per-case *facts* the rule needs as inputs, so the model
could not compute rule-case values — and correctly refused to fabricate them
(`_dev_notes/x6-ff-diagnosis/FF-TAXONOMY.md`, capture evidence: 30/30 sampled replies are missing-input
refusals; RULE/NEW cases answered 0/90; EXCEPTED cases — whose facts *are* in the prompt — answered
13/15). **The model's refusal to fabricate was the good behavior; the withholding gate was the system
working.** A gate that blesses everything green would have scored this uninterpretable run and published a
number; this one withheld.

The refusal count itself is the X-HUMAN thesis in miniature: the "30/30 missing-input refusals" holds only
because the replies were *read*, not keyword-matched. A narrow refusal-keyword scan matched 12/30; a
broadened idiom list (adding the "I don't have X / please provide the records" phrasing) reached 30/30, and
a hand-read of the items the narrow scan missed is what certifies them as genuine refusals
(`_dev_notes/x6-ff-diagnosis/FF-TAXONOMY.md`, provenance note). Even the audit's *own* keyword instruments
are phrasing-fragile — the same shape-vs-content failure this note is about, now one level up — and prose
reading is the ground truth. That is the standing argument for the pending human κ pass (§5.2), not a
weakening of the 30/30.

### 3.5 Item-level raw reads behind every aggregate

No aggregate stands without a per-item reading beneath it. A3: two independent blind auditors
hand-classified a 30-item stratified sample → 29 false-positive, 0 real, 1 initially-ambiguous resolved to
FP; the lead independently read 3/3 raw items (`.../x1-anatomy/X1-FINDINGS.md` §5 cross-validation). E5:
two independent adjudication passes agreed on 9 FP + 2 dangling-rule, with the F2 arithmetic computed
explicitly (`.../CORRECTION-NOTE-DRAFT.md` §certification). E9: the per-item table enumerates all 27
disagreements with stale/asserted/correct values side by side (`.../mission-x/E9-SCREEN-APPENDIX.md`
§Per-item table). The self-caught discriminator discipline is visible even in the tooling: the E9 screen's
first reproduction printed `n_disagree: 0` — a harness bug reading the wrong result key — caught by
diffing against the 0/9/18 aggregate rather than trusting the green (`.../mission-x/E9-SCREEN-APPENDIX.md`
§Rigor, process note).

---

## 4. What the corrected instrument shows

Under instrument-v2, the model-side result inverts the program's registered readings: **instructed
revision is robust in every validly-measured regime, and the operator line has no measured opening in any
regime tested** (`.../mission-x/SYNTHESIS-GATE.md` §0, §4 program conclusion).

### 4.1 Single-shot (A3, E5)

A3 real contamination = **0** across the full 786-item `must_change` sweep (verdict basis 756 post-pruning;
`.../mission-x/MISSION-X-VERDICT.md` §2.2). The false-negative audit over the 556 never-NLI-flagged items
returns 0 missed echoes — the instrument under-flagged nothing; its error is entirely over-flagging
(`.../x1-anatomy/X1-FINDINGS.md` §0). E5: all three arms ≈0 real; Arm-C 0/11 real echo, Arm-B 0/1, and
the *same item* (F1-0016/1) flags in both arms — direct proof the flag tracks sentence template, not arm
behavior (`.../mission-x/MISSION-X-VERDICT.md` §2.5; `.../CORRECTION-NOTE-DRAFT.md` §airtight closer).

### 4.2 Depth (X4)

The A1 axis, rebuilt with correct polarity and re-scored on the certified instrument, shows no
depth-breakpoint. Per-dose contamination 0/149, 10/149, 3/142 at D1/D2/D3
(`.../mission-x/MISSION-X-VERDICT.md` §2.4 table); the break verdict is FALSE (Cochran-Armitage
one-sided p=0.133; strict observed rise FALSE since D3 0.021 < D2 0.067; top-level crossing vs θ=5% not
met). The panel-necessity screen adjudicated all 13 NLI-flagged items as artifacts, so the **true depth
floor is 0/447 = 0.0% real contamination at any depth** — a real zero, not merely a not-crossed
(`.../mission-x/MISSION-X-VERDICT.md` §2.4 TRUE FLOOR).

### 4.3 Compaction (E9), with the matched-arm control

E9 contamination = **0 / 1800 real at every (arm, dose)**: N-arm (no-compaction restatement) 0/150,
0/300, 0/450; S-arm (compaction) 0/150, 0/300, 0/450 (`.../mission-x/MISSION-X-VERDICT.md` §2.7). The
matched no-compaction baseline is the control that makes "compaction does not accumulate revision error"
a comparison, not an assertion. Comparability gate 33/1800 = 1.83% ≤ 2% (the two arms are comparably
scored).

### 4.4 The honest texture: one disclosed arithmetic slip

The record is not sanded smooth. E9-0137 (E9-SCREEN rows 22–23) asserts $3,830 — neither the stale value
nor the corrected $12,340. Reading the output, the model summed a subset of its own component figures
(230+1,200+700+900+800): a model arithmetic slip, not a stale-value echo. It remains a false positive for
the *contamination* question (the stale totals 6,196/11,440 are absent) and is not scored by H-COMPACT's
metric, disclosed only so the non-matching asserted column is not mistaken for a parse error
(`.../mission-x/E9-SCREEN-APPENDIX.md` §Rigor, row-level anomaly). A separate, real completeness defect —
DANGLING_RULE, 2/11 E5 Arm-C items where contraction computes the corrected value and retains the rule but
never draws the final Boolean — is a genuine defect in the contraction operator, not contamination, fix
specced and gated to future retest (`.../CORRECTION-NOTE-DRAFT.md` §dangling rule;
`.../mission-x/MISSION-X-VERDICT.md` §1 finding #5). Both are recorded because they are true, not because
they help the headline.

### 4.5 Scope limits of the model-side result

The robustness result holds for **one model** (claude-sonnet-5), **one pinned compression band** (30–50%,
summarizer sha 305f7e27 for E9), on **template-generated corpora**
(`.../mission-x/MISSION-X-VERDICT.md` §2.7 scope limits; `.../x1-anatomy/X1-FINDINGS.md` §8 scope). "0
real" is a claim about this model on these near-identical-template corpora plus the instrument's blindness
on them; it does not certify the model would resist harder, less-templated stale-value traps. The
operator question survives only on harder non-templated corpora where a genuine echo would be both
detectable and not drowned in template noise (`.../x1-anatomy/X1-FINDINGS.md` §7 item 3).

---

## 5. Positioning and limits

### 5.1 Novelty

Per the owner-ordered novelty sweep (`.../mission-x/MISSION-X-VERDICT.md` §3), the replacement instrument
is positioned against the architecturally-closest prior art, Proof-Carrying Numbers (arXiv:2509.06902;
`.../x1-anatomy/INSTRUMENT-V2-NOTES.md` §Prior art). instrument-v2 **adopts PCN's policy vocabulary**
({exact / rounding / alias / tolerance}) and shares its span-verification substrate — extract numeric
spans, mechanically compare to reference values under declared policies. It **differentiates** on task:
PCN is a *faithfulness* verifier (is this emitted number a policy-compliant copy of a single structured
source value?); instrument-v2 is a *revision-fidelity* scorer over a stale↔corrected **pair** with a
supersession relation, asking which side of a known supersession the model landed on. PCN has no
supersession relation, no stale/corrected pair, no directional echo, and no verdict channel. The honest
line: the extraction/comparison plumbing is PCN-adjacent; the revision-echo task is not modelled by PCN.

The critical negative result for the field: **the nearest prior art in the belief-revision line uses the
vulnerable method.** The instructed-disregard literature that reports 10–20% failure
(`experiments/E5-reclosure/README.md` prior-art list) scores with the same family of sentence-level
entailment or judged-assertion checks. No publication of this specific trap — sentence-shape entailment
fabricating a hypothesis-shaped revision-failure curve on templated corpora — was found in the sweep. That
absence is the reason this note exists.

### 5.2 What is proven vs pending

**Proven** (machine-provable or hand-adjudicated with independent cross-validation, all on banked data, no
new generation): A3 0/786; E5 0/11 real echo with the both-arms control; X4 0/447 true floor; E9 0/1800
real with the matched-arm control and the 27-item screen; instrument-v2 acceptance and adversarial positive
controls.

**Pending** (marked, not blurred into the proven set): the NLI human-validation (X-HUMAN — ≥100 items × 2
annotators, κ + FP/FN near 0.7) is owner-mediated and awaiting annotators; annotation packets are staged
(`.../mission-x/SYNTHESIS-GATE.md` G1, §4 X-HUMAN PENDING). The item-level screens above were **agent-run**;
the human-label validation that would convert "screened to 0" into "human-confirmed 0" is built but not yet
executed. The E5 correction-note publication is an owner act, drafted not published
(`.../CORRECTION-NOTE-DRAFT.md` status). The X6 behavioral-form question remains open pending an
owner-gated corpus re-run (`.../mission-x/MISSION-X-VERDICT.md` §2.6). The A1 instrument-v2 screen used a
hand-certified adapter; tool-certification for the A1 corpus is future work
(`.../mission-x/MISSION-X-VERDICT.md` §2.4 tooling note).

### 5.3 Standing limits

- **Single program, single model family.** All appearances are from one program on claude-sonnet-5. The
  *artifact mechanism* is model-independent (it is a property of the scorer and the corpus template), but
  the *robustness* conclusion is not.
- **Template corpora are both amplifier and scope condition.** Template generation maximizes the
  stale↔corrected collision that produces the artifact — which is why the artifact is so visible here —
  and simultaneously bounds the model-side "0 real" claim to templated stale-value traps. The same
  property that exposes the instrument caps the generality of the result.
- **Screens agent-run pending human κ.** The falsification is strong (global assertion sweeps,
  both-arms controls, positive controls that fire) but the human validation that closes the circularity
  of an LLM-adjacent judge is staged, not complete. Stated as pending, not done.

---

## 6. One-line statement

Sentence-level NLI scoring of belief revision fires on the requirement scaffold shared between a stale
claim and its corrected replacement — reading a superseded value's retraction as its assertion — and on
templated corpora this produces hypothesis-shaped false positives (10–26%, and a rising dose curve) that
five times in one program would have been published as real revision failures; a claim-grounded value/
verdict instrument that excludes retraction clauses and must prove it can fire collapses all five to zero
real, under which the studied model's instructed revision is robust across single-shot, depth, and
compaction — with human κ-validation of the screens the one load-bearing step still pending.
