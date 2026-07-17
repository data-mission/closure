# E8 Phase 0 — the frozen axis-selection registration

This document is the Phase-0 sub-registration required by [decision 0008](../../decisions/0008-e8-instruction-breakpoint.md):
E8 is not runnable until the content below is frozen by a public commit plus a tagged, Zenodo-archived release
([0006 as amended](../../decisions/0006-reproducibility-and-freeze.md) — the release DOI is the registration
act). No probe of any kind is generated before that release exists; pilots included (0008 (iv)). The frozen
scoring configuration is **unchanged from E5's registered configuration** — config hash
`6dbe47a8e843ec1540f64ed6ddd8339c17b95688db363e31605502e374a8b9f0` carries forward as this registration's
token (the additions since E5 are verdict *functions* and their oracle tests, not configuration; see §6).

## 1. The frozen axis set — three axes

Selected from the eight registered candidates (0008 (i)) under the four selection criteria (0008 (ii)); the
full narrowing record is §2.

- **A1 — Dependency depth.** Dose = number of reasoning operations between the corrected fact and the scored
  conclusion. Levels **D1 / D2 / D3** (1 / 2 / 3 operations; D1 is the E5-equivalent anchor). A level is
  certified at construction time, never post-hoc: a frozen operation definition, a reference-solution
  dependency graph per task, an irreducibility check (the conclusion must be underivable with fewer
  operations), and two-annotator agreement on the operation count. A solver-independence confirmation (the
  standard A-dependency filter) runs during corpus construction as a pre-registered acceptance gate: it may
  reject a task that fails to instantiate its level; it can never redefine a level, and every rejection is
  counted and reported. Break read on `must_change` (contamination).
- **A2 — Scoped-exception generalization (propositional form).** Dose = number of accumulated case-scoped
  exceptions to a general rule, levels **S1 / S2 / S3** (1 / 2 / 3 exceptions, each naming a distinct case).
  Sources state a general rule plus the scoped correction(s); `must_change` carries the excepted cases'
  conclusions, `must_persist` carries the rule's conclusions for every non-excepted case. Cases are certified
  pairwise disjoint at construction (a frozen case-partition; no exception may touch another case's
  conclusions). The predicted failure is over-generalization — treating a scoped exception as revoking the
  whole rule — so the break is read on the **`must_persist`** side (§3). The behavioral/agentic form of this
  mechanism is excluded (not scorable by the frozen instrument) and staged as a separately derived hypothesis.
- **A3 — Accumulated corrections.** Dose = number of stacked full-supersession corrections, levels
  **C1 / C2 / C3** (1 / 2 / 3 corrections; C1 is the E5-equivalent anchor), order fixed (pure supersession —
  no correction overturns another; interleaving is a dropped axis, §2). Each correction is its own source
  under the standard per-source token cap; the scorer builds premises per source, so the pair length is
  dose-invariant by construction. Break read on `must_change`.

Every task is built as a **matched family**: one scenario instantiated at all of its axis's dose levels, so
each task appears at every level. This is a binding construction rule — the task-level companion test (§3)
requires it.

## 2. Selection record and dropped axes (0008 (ii): the narrowing is recorded)

| Candidate (0008 (i)) | Disposition | Reason |
|---|---|---|
| Context length / distractor volume | **Deferred to a future amendment** | The scoring instrument is valid only for it via a per-segment extension; pre-freeze validation of that extension found (a) it never engages at this corpus scale (maximum observed asserted-text premise 196 tokens vs the ~480-token window) and (b) when it does engage, max-over-segments can inflate a score across the assert threshold by isolating entailing evidence from its diluting context (planted-fixture check: 0.643 → 0.787). Freezing an extension that is both unreachable and unsound-when-reached would add risk and no measurement. The axis returns, if ever, by its own registered amendment carrying the repaired extension and its full validation. |
| Accumulated corrections | **RETAINED (A3)** | Passes all criteria once interleaving is dropped; per-source premise construction makes its instrument condition dose-invariant. |
| Correction-of-correction interleaving | Dropped | Mechanically contains correction-count as a substrate; a monotone break is unattributable without matched-count controls. Dropping it is what makes A3's independence clean. |
| Dependency depth | **RETAINED (A1)** | Passes all four criteria; directly probes the regime E5's audit marked untested (1–2 operations per task). |
| Assumption-to-correction distance | Dropped | Dose realized as inserted length (instrument collision) and confounded with the length cluster. |
| Domain shift of the correction | Dropped | No naturally ordered ≥3-level dose; thinnest cited motivation. |
| Compaction cycles | Dropped from E8; staged as its own derived hypothesis | A summarize-and-continue cycle is a mechanical contraction applied to a live context — an *operator*, and E8 is registered operator-free. Its evidence base is the strongest of the eight (E5's own registered result), so the exclusion is a scope decision, recorded as such; the mechanism gets its own study rather than mislabelling an operator effect as task difficulty. |
| Scoped-exception generalization | **RETAINED (A2), propositional form only** | Passes; instrument-clean; its motivation is registered as an original prediction (disclosed — no direct citation). |

## 3. The break definition (frozen)

Per axis, a **break** is declared iff all three hold:

1. **Monotone trend:** Cochran–Armitage trend Z > 0 across the ordered dose levels (integer scores, per-item
   binary response). Reported with Z and one-sided p; not alpha-consuming (a conjunctive gate can only make
   rejection harder).
2. **Strict observed rise:** the observed rate strictly increases across every adjacent level pair
   (p̂₁ < p̂₂ < p̂₃). Tolerance-free; under sampling noise this conjunct can only fail — the conservative
   direction. It is what excludes the flat-then-jump curve 0008 (iii) forbids: a 0%/0%/12% curve has a large
   positive trend statistic (Z ≈ +5.3 at N=150/level) yet is not a dose-response; the oracle for exactly that
   curve is in the frozen test suite. Per-level rates are always published, so a noise-failed gate is visible
   as such.
3. **Top-level crossing:** a one-sided exact binomial test of the top level's pooled count against the frozen
   absolute threshold, at α = 0.05/m (m = 3, the frozen axis count; exactly one verdict-bearing crossing test
   per axis, on the side that carries its registered break).
   - **Contamination side (A1, A3): θ = 5%** — ≈5× E5's measured 0.93% instruction floor (a crossing cannot
     be noise off the floor), ≈½ the 10.28% known-bad contraction reference.
   - **Persist side (A2): θ_persist = 10%** — the persist-violation floor is 5.83% (E5 Arm B, 7/120
     non-excepted persist items; identically 1 − 0.9417 completeness), ~6× the contamination floor, so the
     contamination θ cannot be reused: the clean baseline itself would cross a 5% line (P ≈ .03), a
     manufactured break. At θ_persist = 10% the clean-floor crossing probability is ≈ 7×10⁻⁶. Each A2 family
     fixes its non-excepted persist-item count per task at **2** (the E5-inherited calibration), frozen here.

**N = 150 pooled must-change items per dose level** (≈85 tasks per axis at the measured 1.78 items/task;
persist side receives ≈170 items at 2/task). Corrected power at m=3, θ=5%: 0.97 against a true top-level rate
of 15%, 0.81 at 12%, 0.54 at 10%, 0.22 at 8%. Persist side at θ_persist=10%, N≈170: 0.79 against a true 18%.
**Power honesty, frozen openly:** this design detects a substantial break (true rate ≥ ~12% contamination /
~18% persist) and records outcome (b) as a *bounded* negative — "no substantial break at practical scale,"
the scale defined by these numbers. A marginal break (a rate a few points over θ) needs N = 576–1215 per
level and is explicitly not funded. Clustering: pooled items are the primary unit (E5 precedent); a
task-level paired trend companion (permutation test over matched families) is pre-registered with zero
verdict weight, to expose any pooling artifact. Every dose level is reported; a dropped level voids its axis.

## 4. Corpus construction rules (binding)

Fresh construction for A1 and A2 (their dose-defining content does not exist in the E5 corpus to transform);
A3 is transform-preferred from the frozen E5 corpus with disclosed fresh supplement, route recorded per task.
Carried over from E5 unchanged: the two-state three-draw A-dependency filter; the ≥2-of-3 correction-state
pruning rule; deterministic selection; the ≤350-token per-source cap; annotations authored at construction
time, never from measured-model output. Annotation drafting uses a non-measured model with human spot-checks,
disclosed (the E5 materials-provenance pattern). The corpus is single-vendor, matching E5; a second-vendor
replication corpus is a registered follow-up; vendors are never mixed within an axis (vendor identity would
confound the dose). Pre-registered exclusions, each counted and reported: filter failures, persist-wobble
flags, depth acceptance-gate rejections, and any item whose single asserted-text string exceeds the scorer's
token bound (the item is unscorable; expected incidence ≈0 — the observed maximum is 196 tokens against a
512 bound).

## 5. Probe budget caps (frozen; 0008 (iv))

Denominated in dollars (generations are not fungible across levels). Per axis: **A1 $19.51 · A2 $22.65 ·
A3 $14.71**; program total for this freeze **$56.87**, which is the approved cap (scenario cost ~$45.5 plus a
25% contingency margin calibrated to the ~12% retry rate observed in E5). Pricing basis: the pinned
generation model's published per-token rates, reconciled against E5's billed pilot ($6.27 / 898 generations).
Spending past a cap voids the axis. Construction dominates (~85–90% of cost); the registered run itself is
the remainder. Generation uses the E5 registered pin `claude-sonnet-5` (`generation.model_pin`, inside the
frozen config hash; a provider-returned model-identity mismatch halts the run), E5's frozen sampler
configuration, and the frozen Arm-B instruction pinned by content hash
`f9c242958fccba4eb536ef74d903f6c897545f4365211a6dacd00b6fdbe70a7c`
([ARM-B-INSTRUCTION](../E5-reclosure/ARM-B-INSTRUCTION.md)). One generator identity across all doses and axes.

## 6. Instrument (frozen, unchanged) and the new verdict functions

The scoring instrument is E5's, bit-for-bit: same checkpoint, revision, thresholds, device pin, and config
hash. Two additions since E5, neither touching configuration: (a) the verdict functions —
`exact_binomial_crossing`, `monotonicity_gate` (the three-conjunct rule of §3), `bonferroni_alpha` — added to
the frozen stats module with a hand-computed oracle suite that must stay green (including the
flat-then-jump gate oracle); (b) a documented reproducibility constraint discovered during pre-freeze
validation: **a pair's score depends on its batch composition** (the CPU float path is not bit-invariant to
padding), so batch_size=16 grouping in request order is part of the frozen scoring path, and any replay must
reproduce it — divergences under other groupings are last-ULP artifacts (measured bound ±2.4×10⁻⁴, far below
every decision threshold; zero threshold crossings observed in controlled replays).

## 7. Validity threats and their controls

| Threat | Control |
|---|---|
| Manufactured break | Axes, levels, thresholds, budgets frozen before any probe; α/m; the strict-rise conjunct fails toward NO-break; flat-then-jump excluded by an oracle-backed rule; no post-hoc drops (a dropped level voids the axis). |
| False negative from underpower | Exact-binomial power table frozen openly with the unfunded cells visible; outcome (b) is scoped numerically, never "instruction never fails." |
| Wrong regime | The depth axis probes past E5's audited 1–2 operations; the deferred context-volume axis is recorded as a scoped limitation with its amendment path, not hidden. |
| Instrument artifact | Scorer unchanged from E5 (hash-identical); batch discipline documented and pinned; the candidate segmentation extension was excluded after validation exposed score inflation when it fires. |
| Operator contamination | Compaction excluded — E8 stays operator-free, so a break is attributable to task difficulty alone. |
| Baseline-floor gaming | The persist-side threshold is derived from its own ~6×-higher measured floor; the contamination threshold sits 5× above its floor. |
| Generator drift | Model pin + identity halt + frozen sampler + content-hashed instruction; one generator identity throughout. |
| Construction-time tuning | Level definitions are structural and checkable at construction; annotations authored before any arm output exists; all exclusions pre-registered and counted. |
| Single-author bias | This registration is open to adversarial review before the first probe: objections filed against it are recorded verbatim in the results record, adopted or not. |

## 8. What follows the freeze

Corpus construction (the first paid generation) begins only after the release DOI exists, under §4's rules
and §5's caps. The run and its verdict are reported against [the pre-registered outcome
conditions](README.md#verdict-conditions-pre-registered): (a) a break re-scopes the operator experiments to
the found regime, confirming none of them; (b) no break at the scale defined in §3 concludes the revision
line with a program-level negative of record.
