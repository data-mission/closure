# E9 — Compaction cycles: does an iterated summarize-and-continue operator accumulate revision error?

**Status:** DESIGN (zero-spend authoring). Not runnable. Generation launches only through the lead
with disclosure. This document + the code skeletons in `driver/` are the complete apparatus design.

**Authoring provenance:** written by P2 after the P2 design-sufficiency audit
(`_dev_notes/e8-design-audit/P2-design-sufficiency-verdicts.md`) and confirmed against the X1
full-rescore result (`coldstart-package/x1-anatomy/true-floor-table.md`). Every anchor number below
is measured from this repo, not assumed.

**Novelty / related work:** see `X5-NOTES.md` for the full differentiation against arXiv:2607.08032
(rate–distortion compaction — predicts super-linear end-task-error accumulation under repeated
compaction), 2606.22528 (Governance Decay / ConstraintRot — single-compaction safety-constraint
erasure, 0%→30–59%), and 2510.07777 (Drift No More — bounded multi-turn equilibria). E9's separation
is structural on three verified axes: (i) DV = instructed-revision fidelity (contamination/persistence,
causally scored by instrument-v2), NOT end-task accuracy / constraint erasure / KL drift; (ii) an
operator-vs-no-compaction matched baseline over identical turns, which none of the three have on a
revision task; (iii) the tie to E5's registered contraction result. **E9 does NOT claim primacy on
iterating compaction** — 2607.08032 iterates it for end-task error; E9's claim is primacy on iterating
compaction against a matched baseline on a correction-fidelity DV. The Related-Work paragraph for the
registration is in `X5-NOTES.md`.

**⚑ ANCHOR CORRECTION (SYNTHESIS-GATE 2026-07-19).** This design was first drafted with E5 Arm-C's
10.3% contraction contamination as the plausible-effect anchor. That number has since been
re-adjudicated as an INSTRUMENT ARTIFACT (E5-C re-exam: 0/11 real echo; the B-vs-C 0.9%-vs-10.3%
separation is the same template-collision class as A3). Consequence for E9: there is now **no measured
positive prior** that any operator (compaction included) produces ~10% revision contamination — every
validly-measured revision baseline in the program sits at floor (~0–1%). E9's power table (§5) is
re-framed accordingly: E9 tests whether compaction lifts contamination ABOVE the ~1% floor AT ALL, with
the effect-size column now spanning the full plausible range (floor → large) rather than leaning on a
discredited 10% anchor. This RAISES E9's importance — with the E5-C failure gone, X5/H-COMPACT is one
of only three surviving routes to any operator-failure regime (SYNTHESIS-GATE §2 G10/G11) — while
removing its convenient effect-size prior. Both facts are folded in below.

---

## 0. Why E9 exists, and why it is NOT an E8 axis

E8 Phase 0 (`PHASE0.md` §2) dropped compaction from the E8 axis set with an explicit reason:

> "A summarize-and-continue cycle is a mechanical contraction applied to a live context — an
> *operator*, and E8 is registered operator-free. Its evidence base is the strongest of the eight
> (E5's own registered result), so the exclusion is a scope decision, recorded as such; the
> mechanism gets its own study rather than mislabelling an operator effect as task difficulty."

E9 IS that separately-staged study. This framing is load-bearing and is the first thing a reviewer
must accept:

- **The summarizer is the operator.** A compaction cycle reads the live working context and REPLACES
  it with a model-generated summary, then generation continues from the summary. That is exactly the
  shape of the E5 Arm-C contraction operator (`harness/src/closure_harness/contraction.py:50` —
  "a mechanical contraction applied to a live context"), except the reduction function is a model
  summarizer instead of the deterministic claim-pruner. E9 is therefore **operator-BEARING** and
  must be framed as its own hypothesis, never as a difficulty axis. Retro-labelling a compaction
  effect as "task difficulty" is the exact error §2 forbids.
- **The contrast is operator-vs-instruction over MATCHED turns**, not dose-of-difficulty. Both arms
  do the identical multi-turn task and the identical retract-and-revise work; they differ ONLY in
  whether the context is compacted between turns. Any contamination delta is attributable to the
  compaction operator alone.

## 1. Hypothesis (registered form)

**H-COMPACT.** An iterated summarize-and-continue operator applied to a live reasoning context
accumulates revision contamination across cycles, exceeding the no-compaction instruction baseline
and rising monotonically with cycle count; whereas the instruction baseline over the same turns stays
at its measured floor.

- **Kill condition (b):** compaction contamination does NOT rise monotonically across ≥3 cycle
  levels AND does NOT cross the frozen absolute threshold at the top level. Consequence: E5's
  single-shot contraction result does NOT scale into an iterated-operator failure regime; the
  compaction line closes with a bounded negative.
- **Confirm condition (a):** compaction contamination rises monotonically across ≥3 cycle levels,
  crosses the threshold at the top level, AND beats the matched no-compaction baseline. Consequence:
  the FIRST demonstrated regime where a real operator (compaction) measurably degrades revision that
  a plain instruction handles — the operator-failure regime the whole program has been assuming
  exists. This RE-OPENS the operator line with a concrete failing operator to study/repair.

Both outcomes are publishable: (a) is a positive operator-failure result; (b) refutes the strongest
of E8's eight candidate motivations (E5's own contraction number) as a scaling claim.

## 2. The two arms (matched)

Every task is run at each dose level `k ∈ {1, 2, 3}` (cycle count) in BOTH arms. Matched families:
one scenario instantiated at every `k` in both arms, so a task appears 6 times (3 doses × 2 arms).

- **Arm N — no-compaction instruction baseline.** The task is presented as a `k+1`-turn interaction:
  the base sources, then `k` correction turns delivered one at a time, then the question. The FULL
  transcript (all sources + all corrections + all prior model turns) is retained in context at every
  turn. The frozen E5 Arm-B retract-and-revise instruction
  (`ARM-B-INSTRUCTION.md`, content hash `f9c24295…`) is appended at the final answer turn, identically
  to E8. Arm N is the control: it isolates "the model saw everything and was told to revise."
- **Arm S — summarizer/compaction operator.** Identical turn sequence and identical corrections, but
  BEFORE each of the `k` correction turns is appended, the current live context (sources + prior
  turns) is REPLACED by a model-generated summary produced by the frozen generation model under a
  pinned **summarizer instruction** (`driver/SUMMARIZER-INSTRUCTION.md`, content-hash-pinned like
  Arm-B). Generation then continues from `[summary] + [new correction]`. At the final turn the same
  retract-and-revise instruction is appended. Arm S is the operator: it isolates "the model revised
  through `k` compaction boundaries."
  - **Launch-ready pin (computed, awaiting the lead's stamp):** `SUMMARIZER-INSTRUCTION.md` file-bytes
    sha256 = `305f7e27a63696dc96046fbe40208224287cd099142d6fec73b01623490426e4` (as of the current file
    content). `run_e9.startup_guards` hashes file bytes (same as the Arm-B pin path), so this is the
    value that replaces the `SUMMARIZER_PINNED_SHA256 = "<FROZEN-AT-REGISTRATION>"` placeholder at
    launch. NOTE: any edit to the instruction file changes this hash — recompute at stamp time if the
    prose is touched. (Extracted-blockquote-text hash, for reference only, is
    `24f83a5ee537cac89e751f2cf1b6d875e2a3ae57b806ef4acc97372b11cf2df2`.)

**Dose = number of compaction cycles `k`** (Arm S) / matched correction turns (Arm N). ≥3 levels
(k=1,2,3), extensible. `k=1` is NOT the E5 anchor: E5 compacted once over a single-correction context;
E9 `k=1` compacts once over a single-correction context in a MULTI-TURN protocol, so E5 informs the
prior but is not a shared datum (stated as a non-re-run, matching E8's "Not a re-run of E5").

**Matched-turn discipline (the anti-confound):** Arm N and Arm S at the same `k` have the IDENTICAL
number of turns, the IDENTICAL corrections in the IDENTICAL order, and the IDENTICAL final
instruction. The ONLY difference is the compaction step. This is what makes a contamination delta
attributable to the operator and not to turn count, correction count, or context growth.

## 3. Scoring — dual-scorable, numeric-only (the F2-artifact dodge)

The X1 full rescore proved the frozen whole-sentence NLI scorer is unsound on compound
`{value} {verdict} {threshold}` strings (200 NLI flags → 1 verified real;
`true-floor-table.md`). E9 must not re-import that artifact. Two binding rules:

1. **All scored strings are NUMERIC-ONLY, single-proposition, F3-grammar.** Every `must_change` and
   `must_persist` item is of the form `"The <label> is <value>."` — a pure computed value, NO
   embedded threshold clause, NO verdict word (`fails`/`exceeds`/`within`). This is the F3 grammar
   that instrument-v2 documents as VALUE-echo-only and that the frozen NLI scores correctly (F3:
   0 artifacts across 344 items in the X1 rescore). Verdict/threshold reasoning MAY appear in the
   task, but the SCORED conclusion is always a bare value. This dodges the F2 mechanism at the
   corpus level, not the scorer level.

2. **Every item is scored by BOTH instruments and they must agree (comparability gate).**
   - **Frozen NLI** (`harness/.../outcomes.py`, `nli.py`, config hash
     `6dbe47a8…`, bs=16, cpu, 0.70) — the registered instrument, carried forward bit-for-bit so E9's
     numbers are directly comparable to E5 and E8.
   - **instrument-v2** (`coldstart-package/x1-anatomy/instrument_v2.py`, the claim-grounded
     value-echo test) — the de-artifacted instrument. On F3-grammar numeric-only strings, value_echo
     is the sound contamination signal.
   - **Comparability gate (pre-registered):** on the E9 corpus, because strings are numeric-only, the
     two instruments must agree on ≥ 98% of items (F3 had 0 NLI artifacts, so disagreement should be
     near-zero). Any item where they disagree is HAND-ADJUDICATED and the adjudication is published;
     a disagreement rate > 2% VOIDS the numeric-only construction (it means a compound string leaked
     in) and halts before verdict. The registered contamination number is the **instrument-v2**
     value, with the NLI number reported alongside for comparability; they should be identical.

Contamination = fraction of `must_change` (stale computed value) items the arm's final answer still
asserts as a live value. Completeness = fraction of `must_persist` items retained. Definitions are
`outcomes.py` semantics unchanged; only the corpus grammar is constrained.

**Polarity assertion (the A1-class guard, fail-closed):** at construction, a static check asserts
every `must_change` value equals the STALE-world computed value (pre-final-correction) and differs
from the correct-final value. Any `must_change` numeric equal to the correct-final value HALTS
construction. This is the exact guard whose absence produced the A1 inversion; it is mandatory and
enforced in `driver/build_e9_corpus.py`.

## 4. Corpus design — reuse E5/E8 machinery

**MEASURED SCALE CONSTRAINT (verified, changes the build route).** Running the E9 guards
(`build_e9_corpus.py --self-check`) against the real A3 corpus: of 336 A3 rows, 117 are F3; after the
numeric-only grammar gate, **99 clean records survive, spanning only 4 distinct base scenarios**
(`base_family_e5`), all 3 doses each. Clean must_change items per dose: 65 / 98 / 131 (294 total). So
a pure A3→E9 transform yields ~4 matched scenario templates — nowhere near N=150 tasks/dose, and with
crippling clustering (4 independent families cannot support the task-level companion trend test). The
transform is therefore validated as a SCHEMA-and-GUARD proof, NOT as the scale source. **E9 requires
FRESH F3-family construction** (the A1/A2 route in E8: fresh scenarios, not a transform), reusing the
A3 correction-stacking + state_values + independence-certification structure per new scenario. This is
the single biggest build-cost driver and is called out here so it is priced, not discovered mid-run.

- **Base families:** the substrate is the E5 F3 quantitative grammar (`experiments/E5-reclosure/corpus/`
  and the A3 `F3-*` scenarios as the STRUCTURAL template). F3 is the family that (i) carries the
  numeric-only grammar natively and (ii) had zero contamination in both E5 and the X1 A3 rescore — so
  its instruction floor is genuinely ~0, giving the operator maximum headroom to show a delta. Building
  on F3 is deliberate: it is the clean substrate where any accumulation is attributable to compaction,
  not to a pre-existing baseline leak. But the SCENARIOS must be freshly generated to reach N and to
  give ≥ ~40 independent families for the companion test (the existing 4 do not).
- **Correction stacking:** reuse the A3 accumulated-corrections construction
  (`corpus-candidates/A3-corrections.jsonl` schema — `axis_params.corrections[]`, pure supersession,
  `state_values` stale→corrected, independence certification per correction). E9 needs exactly this:
  `k` independent full-supersession corrections, each retracting one live figure, order fixed. The A3
  transform route (`route: transform:F3-*`) is reused; each correction becomes one TURN instead of
  one appended document.
- **Turn delivery:** the only new construction is turning the A3 "all corrections appended at once"
  into "one correction per turn" and inserting the compaction step for Arm S. Prompt-state machinery
  is reused: `axis_prompt.documents_for_state` already knows how to include/withhold correction docs
  per axis; E9 adds a `turn` parameter that reveals corrections incrementally (skeleton in
  `driver/turn_prompt.py`).
- **Annotations:** authored at construction from `state_values` (never from model output), F3-grammar
  numeric-only, two per persist side (E5-inherited calibration), depth-certified via the reused
  A-dependency two-state three-draw filter.
- **Generation:** reuse `generation_driver.py` verbatim for the per-turn calls (frozen provider,
  model-identity halt, ARM-B hash pin, resumable append-only log). E9 adds a thin multi-turn
  orchestration wrapper (`driver/run_e9.py`) that sequences turns and invokes the summarizer between
  them; each individual model call still goes through the frozen `generate_row`.
- **Single vendor** (`claude-sonnet-5` pin), one generator identity across arms and doses, matching
  E5/E8. Summarizer uses the SAME model pin (a compaction operator in the wild uses the same model);
  its instruction is separately hash-pinned.

## 5. Spend estimate and power table

### Spend (per arm × dose × N)

Calls per task, per arm, at dose `k`:
- Arm N: `k` correction turns are context-only (no generation needed until the answer) + 1 answer
  generation = **1 generation** per task (the intermediate corrections are appended text, not model
  turns, in the baseline — the model answers once at the end with the full transcript). To keep the
  arms turn-matched in COST as well, an optional per-turn "acknowledge" generation can be added, but
  the registered design keeps Arm N at 1 answer generation (the correction turns carry no model
  output to summarize).
- Arm S: `k` summarizations + 1 answer generation = **k + 1 generations** per task.

Per matched task across all doses: Arm N = 3 (one answer at each of k=1,2,3) ; Arm S = (2)+(3)+(4)=9.
Total = 12 generations per matched task.

At the E8-calibrated rate (E5 billed pilot $6.27 / 898 generations = **$0.00698/generation**,
`PHASE0.md` §5) and N tasks per dose:

| N tasks/dose | matched tasks | total generations | est. cost | +25% contingency |
|---|---|---|---|---|
| 50 | 50 | 50×12 = 600 | $4.19 | $5.24 |
| 85 (E8 calibration) | 85 | 85×12 = 1020 | $7.12 | $8.90 |
| 120 | 120 | 120×12 = 1440 | $10.05 | $12.57 |
| 150 | 150 | 150×12 = 1800 | $12.57 | $15.71 |

Summaries are short (they compress context) so per-generation cost is at or below the E5 average;
the estimate uses the flat average conservatively. Scoring is local CPU/GPU, $0.

**Construction dominates (per the §4 scale finding).** Because E9 needs FRESH F3 scenarios (the 4
existing clean A3 F3 families are far too few), construction is the main cost, matching E8's own
"construction is ~85–90% of cost" pattern (`PHASE0.md` §5). Budget it like A1/A2 (fresh-construction
axes: A1 $19.51, A2 $22.65) rather than A3 (transform: $14.71). Expected E9 total at N=150/dose:
run generations $15.71 (table above) + fresh F3 construction on the A1/A2 scale (~$20) ≈ **$36 with
contingency**, inside the E8 per-axis envelope. Annotation drafting uses a non-measured model + human
spot-check (E5 materials-provenance pattern), disclosed at freeze; every exclusion (grammar-gate
rejects, compression-band redraws, polarity HALTs) counted and reported.

### Power table

Anchors (measured, this repo): no-compaction baseline REAL contamination ≈ **0.13%** (1/756,
instrument-v2 A3 rescore) ~ E5's 0.9% floor — this is the ONE surviving hard anchor. θ = 5% (E8
contamination side, carried forward).

**⚑ The effect-size prior is now UNANCHORED (SYNTHESIS-GATE re-adjudication).** The earlier draft used
E5 Arm-C's 10.3% as the plausible-effect anchor and set the confirm range at S∈[10%,20%]. That anchor
is withdrawn: E5-C's 10.3% is now judged an instrument artifact (0/11 real echo), so there is NO
measured operator effect ≥ floor anywhere in the program. E9 therefore does not assume a 10% effect —
it MEASURES whether compaction lifts contamination above the ~1% floor at all. The table below spans
the full plausible range (8% marginal → 20% large) precisely because no point estimate is defensible;
the 10.3% column is retained ONLY as a reference magnitude (what the old artifact looked like), not as
an expectation. The honest registered read: E9 is well-powered to detect a LARGE compaction effect
(≥15%) and underpowered for a marginal one (≤8%) — and given the program's floor-everywhere result, a
NULL (outcome b) is now the higher-prior outcome, which E9 records as a bounded negative, not a
surprise.

**(1) Top-dose crossing θ=5%, exact binomial, α=0.05** (Arm S, N pooled must_change items/dose):

| N items | S=8% | S=10.3% | S=15% | S=20% |
|---|---|---|---|---|
| 107 | 0.35 | 0.67 | 0.97 | 0.999 |
| 150 | 0.42 | 0.78 | 0.99 | 1.00 |
| 200 | 0.54 | 0.89 | 0.999 | 1.00 |
| 300 | 0.70 | 0.97 | 1.00 | 1.00 |

**(2) S-vs-N paired McNemar** (operator beats baseline), N tasks, discordant favor(S worse)=0.10 /
against=0.01 (S~10% vs N~1%):

| N tasks | power |
|---|---|
| 85 | 0.83 |
| 107 | 0.93 |
| 150 | 0.99 |
| 200 | 0.9995 |

**(3) The E8 three-conjunct break gate** (Cochran–Armitage trend Z>0 AND strict rise p̂₁<p̂₂<p̂₃ AND
top-cross θ=5%), simulated on an accumulation curve [2%, 5.5%, 10.3%]:

| N items/dose | power |
|---|---|
| 50 | 0.28 |
| 85 | 0.43 |
| 120 | 0.61 |
| 150 | 0.71 |

**Power honesty (frozen openly, E8 pattern):** the S-vs-N paired contrast (2) is the strong,
well-powered primary test — at N=150 tasks it detects a 10%-vs-1% operator effect at power 0.99.
The three-conjunct dose-response gate (3) is the WEAK link: the strict-rise conjunct is punishing
under sampling noise, so even a real accumulation curve peaking at 10.3% is caught at only ~0.71 at
N=150/dose. E9 therefore pre-registers TWO verdict tiers: the **primary** verdict is the
paired S-vs-N contamination contrast at top dose (well-powered, this is what carries H-COMPACT); the
**secondary** verdict is the monotone-accumulation gate (underpowered for a shallow curve, reported
honestly as a bounded read). A confirmed primary with a failed secondary = "compaction degrades
revision but the per-cycle accumulation shape is below our resolution" — a true and publishable
bounded result, not a null. Registered N = **150 tasks/dose** (McNemar 0.99 primary; $15.71 with
contingency, inside the E8-scale envelope).

## 6. Pre-stated conclusion sentences (two-sided, frozen before the run)

Exactly one fires; both are written now so neither can be authored to fit the data.

- **(a) ACCUMULATES — H-COMPACT confirmed / first operator-failure regime.** "An iterated
  summarize-and-continue operator contaminated N.N% of must-change conclusions at k=3 compaction
  cycles (top dose), significantly exceeding the matched no-compaction instruction baseline of N.N%
  (McNemar p = N.NNN, S worse on n tasks, N worse on m), and [did / did not] rise monotonically
  across k=1,2,3. This is the FIRST validly-measured regime in the program where any operator applied
  to a live reasoning context degrades a revision that a plain retract-and-revise instruction handles
  at floor — an especially load-bearing result because the program's prior candidate operator-failure
  (E5 Arm-C's 10.3%) was found to be an instrument artifact, leaving NO measured operator failure until
  this one. It confirms, on a correction-fidelity DV, the super-linear-accumulation direction that
  2607.08032 predicts for end-task error under repeated compaction. It re-opens the operator line with
  a concrete failing operator (compaction) to characterize and repair; it does NOT by itself validate
  any proposed closure operator, which must still beat instruction AND beat compaction in this regime."
- **(b) HOLDS — H-COMPACT refuted, bounded negative.** "An iterated summarize-and-continue operator
  contaminated N.N% at k=3, not distinguishable from the matched no-compaction baseline of N.N%
  (McNemar p = N.NN), and did not cross the 5% threshold / did not rise monotonically. Model-summarizer
  compaction, as a live-context operator, holds instructed revision at floor across the depths tested
  (N=150/dose, curve resolution per §5(3)). Combined with the program's floor-everywhere revision
  result and the withdrawal of E5-C's 10.3% as an artifact, this closes the compaction route to an
  operator-failure regime: the super-linear end-task-error accumulation 2607.08032 predicts does NOT
  transfer to instructed-revision fidelity at these depths, and it aligns instead with the
  bounded-equilibrium finding of 2510.07777. The compaction line closes with a bounded negative of
  record."

## 7. Validity threats and controls

| Threat | Control |
|---|---|
| Compaction effect mislabeled as difficulty (the §2 error) | Matched-turn discipline: N and S differ ONLY in the compaction step; identical corrections/order/instruction. Delta is attributable to the operator. |
| F2 compound-sentence artifact re-imported | All scored strings numeric-only F3-grammar; dual-scored NLI + instrument-v2; comparability gate voids the construction if disagreement > 2%. |
| A1-class polarity inversion | Fail-closed construction assertion: every must_change value = stale-world computed value ≠ correct-final; HALT on violation. |
| Summarizer is a weak/strawman operator (an easy win) | Summarizer instruction is the STRONGEST faithful-compression prompt after an adversarial candidate review (mirrors the Arm-B selection discipline); a weak summarizer makes an accumulation result worthless, same logic as E5's "weak Arm B makes an Arm-C win worthless." Content-hash-pinned. |
| Baseline not actually at floor (no headroom) | Built on F3, whose instruction floor is measured ~0 in both E5 and X1 A3 rescore. Baseline floor is re-measured in-run (Arm N) and published; if Arm N is not near floor, the headroom claim is void and reported as such. |
| Underpowered dose-response read | Two verdict tiers frozen: strong paired primary (0.99) + honestly-bounded monotone secondary (0.71); unfunded marginal cells (S~8%) visible in the table. |
| Generator/summarizer drift | Model pin + identity halt + frozen sampler; Arm-B hash pin AND summarizer hash pin; one generator identity across arms/doses. |
| Order/interleaving confound | Corrections are pure supersession, fixed order, independence-certified per correction (reused A3 rule); no correction overturns another. |
| Turn-count confound | N and S have identical turn counts at each k; dose varies k identically in both arms. |

## 8. What E9 does NOT test

- Not a re-run of E5 (E5 = single-shot claim-pruner contraction at one difficulty; E9 = iterated
  model-summarizer compaction over matched multi-turn revision).
- Not a validation of any closure operator: a confirmed (a) opens the operator-failure regime; it
  does not confirm that any proposed operator beats compaction there — that is a separate experiment.
- Not a long-context claim: numeric-only F3 sources stay well under the 512 token bound (max observed
  A3/F3 asserted premise 196 tokens); the fail-closed instrument never engages. E9 does not touch the
  deferred context-length axis.
- Not a claim about human summarization or non-model compaction; the operator under test is
  specifically a model-generated summary under the pinned instruction.

## 9. Files in this design (BUILT + acceptance-verified)

- `DESIGN.md` (this document) — framing, arms, scoring, corpus, spend, power, conclusions, threats.
- `X5-NOTES.md` — related-work / novelty differentiation (2607.08032, 2606.22528, 2510.07777).
- `driver/SUMMARIZER-INSTRUCTION.md` — the pinned summarizer prompt (Arm S operator), hash frozen at
  registration; compression band [30–50%] is a hard requirement of the prompt.
- `driver/build_e9_corpus.py` — **BUILT.** `--generate` is the registered FRESH F3 generator (20-domain
  scenario zoo × scale variants → ≥150 independent families; one record per family at k=max, driver
  slices doses). Running totals computed in-code so polarity is correct BY CONSTRUCTION. THREE live
  guards: numeric-only F3 grammar, fail-closed A1-polarity, and instrument-v2 label/unit anchoring
  (folded in). `--in` retains the A3→E9 transform as a schema/guard proof. Acceptance: 150/150 clean;
  guards proven to FIRE on injected inversion / wrong-stale / grammar / unit-collision.
- `driver/turn_prompt.py` — **BUILT.** Incremental per-turn prompts: framing → k correction turns →
  answer; Arm-S compaction insertion; Arm-N restatement variant (`build_restatement_prompt`,
  matched k+1 turns). Reuses the E8 Arm-B marker discipline.
- `driver/run_e9.py` — **BUILT.** Full driver: startup hash guards (Arm-B + summarizer + config),
  per-family dose loop over BOTH arms, Arm-N restatement k+1 matched-count control, Arm-S k compaction
  cycles with compression-band redraw accounting, EVERY generation logged (atomic append, resumable),
  dual scoring (`score_both`: instrument-v2 + frozen NLI) with the ≤2% comparability gate. `--dry-run`
  exercises the whole pipeline via the frozen fake provider at $0. Acceptance: matched-count invariant
  (S-cycles == N-restatements == k) holds for every cell; resume banks 0 on re-run; instrument-v2
  scores correct-answer output clean and stale-asserting output contaminated on generated tasks.
- `driver/prompt_template.txt`, `driver/summarizer_template.txt` — the answer and compaction templates
  (answer template = the E8 template verbatim, for cross-experiment comparability).
- `corpus-schema/e9-task.example.json` — one worked E9 matched-family record (from the A3 transform).

## 10. Weakest point of THIS design (my own hostile pass)

Required by the mission. The single weakest point:

**The summarizer instruction is the whole ballgame, and it is unfalsifiably tunable toward either
outcome.** Arm S's result is a function of one artifact — the summarizer prompt. A summarizer told
"preserve every figure and every correction verbatim" will accumulate almost no error (→ HOLDS, but
it's a strawman that isn't really compacting — it's near-lossless, so the operator was never exercised).
A summarizer told "compress aggressively to the key conclusion" will drop corrections and contaminate
heavily (→ ACCUMULATES, but the break is manufactured by an adversarially lossy operator nobody would
deploy). Unlike Arm-B (where "strongest retract-and-revise instruction" has a clear optimization
direction — maximize revision fidelity), the summarizer has NO single correct target: real-world
compaction operators trade off compression ratio against fidelity, and the result moves continuously
with where you set that dial. So a single pinned summarizer yields a single point on a curve whose
shape is the actual object of interest, and whichever point I pin can be attacked as cherry-picked in
whichever direction it landed.

**Why it is not fatal, and the minimal fix:** pin the summarizer by a MEASURABLE compression target,
not by prose vibes. Register a **compression ratio band** (e.g., summary length = 30–50% of live
context tokens, measured and logged per cycle; a summary outside the band is a construction failure,
re-drawn) so "how much it compacts" is a controlled, reported variable rather than an accident of
wording. Then the summarizer instruction optimizes fidelity SUBJECT TO the pinned compression band —
giving it the same well-defined optimization direction Arm-B has (maximize retention at the fixed
compression), and making the operator faithfully strong rather than strawman-lossy or strawman-lossless.
The compression band is frozen at registration and its choice is disclosed as the one free parameter,
with the honest caveat that E9 measures compaction AT THAT band, not compaction in general (a second
band is a registered follow-up, exactly as E8 handled its deferred axis). This converts the weakest
point from "unfalsifiable dial" into "one disclosed, measured, single-parameter scope limit" — the
program's standard move for an unavoidable degree of freedom.

**Second-order caveat (disclosed, not fixed here):** even with a pinned compression band, Arm N at
1 answer generation vs Arm S at k+1 generations means the arms differ in generation COUNT, not just
compaction. A skeptic can argue Arm S's extra generations (not the compaction per se) drive any
delta. The clean fix — an Arm-N variant with k+1 matched "restate the running answer" generations
that do NOT compact — is registered as the primary control refinement to add before the run if the
lead wants the tightest possible attribution; it roughly doubles Arm N cost (still inside the
envelope at N=150). Flagged for the lead's decision rather than silently chosen.
