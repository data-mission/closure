# E5 — Reclosure: revision as an operation

**Question:** When later evidence contradicts an earlier assumption, does **programmatically rebuilding the context without the assumption** (an explicit contraction operation) reduce downstream contamination more than **instructing the model to disregard it**?

**Hypothesis:** [H-RELEASE](../../HYPOTHESES.md#h-release--revision-is-an-operation-not-a-request). The cheapest experiment in the program: API-only, days of work. Not gated on E0 — a failure retires `release` as formulated, nothing broader.

## Status and prior art

`PARTIALLY PRE-EMPTED` — the premise is now settled science; the comparison is not:

- **Instructed disregard fails, replicated ≥ 7 times independently:** models "pretend to forget" — the final layer emits *forgotten* while earlier layers still compute from the content (arXiv:2410.00382); natural-language "this is outdated" annotations barely modulate retrieval under interference (arXiv:2506.08184); errors left in context bias later generations toward structurally similar errors, 10–20% drops, with neither feedback nor successful self-verification eliminating the effect (arXiv:2602.04288); a formal contamination-cascade model fits agent-retry data with error ratio ε₁/ε₀ = 7.1 on SWE-bench (arXiv:2605.08563); anchoring resists "ignore the anchor" instructions (arXiv:2505.15392, 2412.06593); prompted belief-tracking leaves large residual failure that even RL training only partly removes (arXiv:2605.30219); instruction-level belief-revision performance is near floor across ~30 models (arXiv:2406.19764, which cites AGM as motivation but implements only prompting).
- **Closest analog to the mechanical arm:** a deterministic freshness-resolver beating LLM-judged resolution by +10–21pp, growing with context size (arXiv:2606.01435) — two-arm, engineering-framed, no revision semantics.
- **Priority caution:** a commercial product (XTrace) advertises AGM expansion/revision/contraction as runtime operations for multi-agent systems — no paper, no benchmark, unverified. "First to apply AGM at runtime" is therefore not claimable; "first controlled comparison isolating mechanical contraction against instructed disregard, with downstream contamination as the measured outcome" is. One benchmark (ReviseQA, OpenReview) could not be accessed during the review and may overlap the task design — obtain it before building a corpus.

Citation statuses: [VERIFICATION.md](../../VERIFICATION.md).

## Protocol

1. **Task construction.** Multi-step tasks seeded with assumption A whose downstream conclusions measurably depend on A. Later, inject evidence ¬A. Ground truth: which conclusions *should* change.
2. **Arm A — naive append.** ¬A is appended; generation continues.
3. **Arm B — instructed disregard.** ¬A appended with an explicit, maximally strong instruction to retract A and revise everything that depended on it.
4. **Arm C — mechanical reclosure.** The context is programmatically rebuilt: A removed, ¬A inserted, verified-independent facts carried over per an explicit contraction rule (AGM semantics: retract A and everything whose support depended on A; keep what stands independently). Full regeneration from the rebuilt boundary.
5. **Outcome measures.** Scored against the step-1 ground truth, identically across arms. *Contamination*: the fraction of conclusions annotated **must-change** under ¬A that the arm's final output still asserts (bidirectional NLI against the annotated A-dependent conclusion). *Completeness*: the fraction of conclusions annotated **must-persist** that the output still asserts. The leave-one-out grounding machinery serves as Arm C's contraction rule — which claims to delete — while the outcomes are referenced to annotations that rule never touches: the contraction is never scored by the detector that built it, and no arm can win contamination by deleting everything ([0007](../../decisions/0007-e5-reclosure.md)).

## Verdict conditions (pre-registered)

- **CONFIRMED** iff C substantially beats B on contamination (per the pre-registered test in [0007](../../decisions/0007-e5-reclosure.md)) **and** C is non-inferior to B on completeness (margin pre-registered there). B vs A quantifies the value of instruction; C vs B isolates the operation. Report effect sizes per task family and per contamination depth (direct conclusions vs second-order inferences).
- **REFUTED** iff B ≈ C — instruction suffices in this setting, the published contamination results notwithstanding, and the `release` operator is demoted in the registry.
- **CONTRACTION WINS BY DELETION** iff C beats B on contamination but falls below B on completeness beyond the pre-registered margin — recorded as a failure of the operator as formulated: removing content trivially removes contamination, and the operator earns existence only by revising without gutting.
- **Validity gate:** the Arm-C contraction rule must be algorithmic — an explicit rule or model-computed dependency, applied uniformly across tasks. A hand-curated per-task contraction set turns Arm C into a human oracle beating a prompt, and voids the comparison. Pre-registered as invalid.

## Cost and prerequisites

API access only. No GPU, no open model. "Days" assumes the shared grounding harness exists (it is the contamination detector); building it fresh adds the harness time first. The strongest-instruction Arm B needs adversarial care (see E4's fair-instruction principle — a C-win over a weak B is worthless).

## Exclusion criteria (pre-registered)

Excluded before any arm runs, counted and reported: tasks where the A-dependency fails pilot verification (downstream conclusions do not shift under A-removal, so there is nothing to contaminate). Exclusions apply identically to all three arms.

## Wanted from contributors

- Task corpus with verified A-dependency structure.
- The contraction-rule implementation (what carries over is the intellectually load-bearing design decision — document it as an explicit rule, not ad hoc judgment).
- Pre-flight: obtain ReviseQA's methodology; assess XTrace's actual mechanism.
