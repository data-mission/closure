# e3-0005 — audit-driven verdict-contract redesign (pre-freeze)

- Status: proposed
- Deciders: closure research program contributors
- Scope: E3
- Date: 2026-07-14

This record is e3-scoped pending a merge-time renumbering into the global `decisions/` sequence (see
`README.md` in this directory). It is a **single dated pre-freeze decision** that folds every change the
2026-07-14 audit round forced into one place, so a later reader sees one boundary event, not a scatter of
edits. It **refines** the E3 protocol (`../README.md` § Verdict conditions) — it adds precision and guards
to the two headline branches and never contradicts anything the protocol fixes.

## Context

Two review activities ran against the frozen-candidate E3 records on 2026-07-14, both before corpus
approval and before any confirmatory datum:

- **The five-lens adversarial audit** (pre-mortem `../PREMORTEM.md`; the consolidated defect ledger of the
  hostile-reviewer, interpretability, statistician, replication-skeptic, and methodologist lenses).
- **The labeled dress rehearsal** (`../REHEARSAL.md`, 41 disposable prompts) and the **kind-based
  hardening calibration** (`../hardening/HARDENING.md`, 102 disposable prompts across three rounds).

Together they proved the pre-redesign verdict contract could produce its **strongest** branch off empty or
confounded evidence. The load-bearing findings:

1. **The correctness arm can be evidentially empty.** The rehearsal fired `confirmed-shaped` with **one**
   negative in 41 items — and that one was a 256-token-cap truncation artifact, not a wrong answer (genuine
   error count 0/41). No verdict clause checked that the correctness labels carried mass. The hardening
   calibration then showed that hardening by *degree* buys ~zero negatives (Qwen2.5-7B-Instruct-4bit is at
   ceiling across difficulty 1–4 of the original ladder); only a change of *kind* produces a real negative
   rate.
2. **The fidelity clause read a confound, not a geometric quantity.** On the rehearsal set
   ρ(volume, mean continuation length) = **0.910** (rank) and between-family volume η² = **0.255** — either
   could reproduce most of the volume ranking without any within-family semantic-dispersion signal. The
   global-R² fidelity gate and its 2-bin class-mean guard were satisfiable by family recognition and by a
   length readout.
3. **The R² target has a floor mass point.** 11/41 rehearsal volumes (and 6/30 pilot volumes) sit on the
   exact degenerate minimum `10·log(1e-6) = −138.155`. R² on a mixed discrete-continuous target rewards
   predicting the mode split; Spearman was absent from the decided inputs.
4. **The added-value story was under-specified.** B3 (predictive entropy) and B4 (P(IK)-style correctness
   probe) were named in `../decisions/e3-0003.md` but orphaned from every verdict branch — the confirmation
   clause required only beating verbalized confidence. Published work (arXiv:2509.10625) shows a correctness
   probe (B4) beating verbalized confidence on Qwen2.5-7B, so a confirmation that never had to beat B4 or B3
   was defensible only by omission.
5. **OOD could be extrapolation, not transfer**, and the frozen instrument shipped only test helpers for
   the pooled OOD statistic, unpinned pooling, no per-family floor.
6. **The freeze surface was too small** (revision recorded but not enforced at load; the config hash covered
   a minority of result-moving inputs); the corpus carried pilot-contaminated prompts; the normalizer and
   refusal list were prose promises.

The deep-read pass also **re-scoped the claim** (see § Decision, claim clause), which changed what the
verdict must gate: the sharper surviving question is whether a *volume* direction transfers where
*correctness* directions provably do not (arXiv:2506.08572, arXiv:2509.10625) and whether it adds anything
over B4, B3, and zero-shot verbalized confidence.

## Decision

Rebuild the verdict contract and its frozen surround as one pre-freeze change. Concretely, all of the
following are adopted together; the rebuilt instrument (`../validation/src/e3_validation/verdict.py`,
`preconditions.py`, `fidelity.py`, `ood.py`, `correctness.py`, `loader.py`, `freeze.py`) implements them and
`../VALIDATION.md` proves each on planted-answer fixtures (99 tests, CPU-only).

- **Precondition layer.** A `min_negatives` gate: if the answerable subset carries fewer than
  `min_negatives` negatives, the correctness arm cannot be evaluated at all and the verdict is the terminal,
  honest `NOT_EVALUABLE_CORRECTNESS_ARM` — **not** a refutation — checked before any branch so no verdict
  rests on empty correctness evidence.

- **Two-part fidelity target.** Degenerate items (volume within tolerance of the `N·log(ε)` floor) are split
  out by a degeneracy classifier (reported, `degeneracy_auroc`, not gated); continuous fidelity is scored on
  the **non-degenerate subset only**, with **both** R² (`r2_fidelity_min`) and Spearman
  (`spearman_fidelity_min`, floor-mass-robust) required.

- **Within-family fidelity + family-oracle margin.** A within-family Spearman (volume and predictions
  residualized on train-derived family means; `within_family_spearman_min`) and a family-mean-oracle margin
  (`family_oracle_margin_min` = probe R² − family-mean-oracle R²) are hard fidelity gates. The family-oracle
  margin **replaces** the old 2-bin class-mean margin as the gate; the class-mean margin is retained as B2
  reporting only.

- **Length-residualized gate.** With `require_length_robust`, within-family fidelity must also survive
  residualizing volume on continuation length (mean+std); if the length-residualized within-family Spearman
  falls below `within_family_spearman_min` the fidelity was a verbosity readout →
  `REFUTED_LENGTH_CONFOUNDED`.

- **Within-held-out-family OOD Spearman with per-family floor + range-coverage flag.** The OOD statistic is
  the within-held-out-family Spearman under leave-one-task-family-out rotation, pooled as the
  **mean over rotations** (pinned), with a per-rotation floor (`ood_per_family_floor`): a single collapsing
  rotation refutes even if the pooled mean clears (`ood_pooled_spearman_min`). If any rotation's held-out
  true-volume range is not covered by the training range, that rotation is extrapolation, not transfer →
  `REFUTED_OOD_RANGE_UNCOVERED` (distinct from a genuine collapse, `REFUTED_OOD_FAILURE`). OOD is resolved
  **before** the added-value gates.

- **Added-value gates.** In order after OOD: probe beats the **max over verbalized** variants
  (`probe_vs_vc_ci_low > vc_ci_floor`; the CI-low of the probe's margin over the strongest B1 variant, i.e.
  the minimum paired margin across variants), probe beats predictive entropy B3
  (`probe_vs_b3_ci_low > b3_ci_floor`), and the correctness probe B4 does **not** beat the probe
  (`b4_vs_probe_ci_low ≤ b4_margin_ceiling`). Each failure routes to a **distinct** honest branch —
  `REFUTED_NO_MARGIN_OVER_VERBALIZED`, `REFUTED_NO_MARGIN_OVER_ENTROPY`,
  `REFUTED_DOMINATED_BY_CORRECTNESS_PROBE` — rather than one conflated label.

- **Out-of-fold correctness scoring + frozen orientation table.** Probe and B4 correctness scores are
  produced strictly out-of-fold (seeded k-fold, `correctness_cv_folds`; no in-sample path exists in the
  instrument), and the per-arm score orientation is frozen in `correctness.py`
  (`probe = −predicted_volume`, `B3 = −entropy`, `B4 = P(correct)`, `verbalized = stated_value`), closing
  the self-scoring and orientation holes.

- **Kind-based d4 hardening + improved normalizer + raised answer cap.** The three answerable families each
  replace their 14 difficulty-3 items with 14 calibrated d4 hard-kind items (`arith_mult3x3`,
  `fact_numeric_tail`, `ded_seat6`) that break the model while keeping single-answer-unambiguous golds; the
  normalizer is upgraded to the frozen F1–F5b spec (conclusion extraction for deduction, truncation-as-
  exclusion, tolerance, diacritic folding); and the correctness-label answer cap is raised to **≥ 768
  tokens** so a long chain-of-thought is not truncated into a fake negative (`../hardening/HARDENING.md`).

- **Revision enforcement at load + full freeze-hash schema.** `loader.py` fails closed unless the resolved
  model/tokenizer snapshot equals the pin and records the SHA-256 of a canonical probe rendered through the
  chat template; `freeze.py`'s `FrozenConfig` enumerates **every** result-moving input (corpus/golds hashes,
  refusal regexes, normalizer spec version, ε, N, sampler, base seed + split/bootstrap/CV seed formulas,
  alpha grid, inner/CV folds, bootstrap n/CI, test fraction, ALL verdict thresholds incl. the new ones,
  model/tokenizer/embedder revisions + chat-template hash, dims, library versions, orientation table) into a
  sorted-key JSON → SHA-256.

- **Claim re-scope (adopted).** The registered §1 claim is re-scoped to the maximal-defensible sentence:
  E3 asks whether a **volume** direction transfers across task families where **correctness** directions
  provably do not (arXiv:2506.08572; arXiv:2509.10625) and whether it adds anything over the correctness
  probe (B4), predictive entropy (B3), and zero-shot verbalized confidence. Positioning is fixed against
  BbZKxrZCNn (closest prior art: continuous semantic-entropy regression from hidden states, in-distribution
  only, no volume, no OOD, no VC/B4 head-to-head), arXiv:2509.10625, arXiv:2506.08572, and arXiv:2606.02907
  (whose format-feature **residualization** protocol is adopted as a control). Belief-state / geometry
  language is demoted to labeled speculation. The 4-bit host is scoped, not apologized for: arXiv:2606.02628
  (cited as **NF4**) is the 4-bit-Qwen2.5-7B probing precedent.

### README wordings this record refines

This decision refines the `../README.md` § Verdict conditions (pre-registered) wordings, without
contradicting them:

- **"useful fidelity"** — made precise as the four-gate continuous-fidelity predicate on the non-degenerate
  subset (R², Spearman, within-family Spearman, family-oracle margin) plus the length-residualized gate.
- **"generalizes OOD"** — made precise as the within-held-out-family Spearman transfer statistic with a
  pooled bar, a per-family floor, and the range-coverage distinction between transfer and extrapolation.
- **"beats verbalized confidence" / "adds nothing over verbalized confidence"** — widened to the registered
  added-value set: beats the max over verbalized variants **and** beats B3 **and** is not dominated by B4.
- **"exists only at binary granularity"** — kept as `REFUTED_BINARY_ONLY`, now co-located with the new
  `REFUTED_MARGIN_ONLY` row (above-floor R² that fails the margin/within-family gates with no binarized
  signal) the pre-redesign code had mislabeled `refuted/no-signal`.

### HYPOTHESES.md § H-VOL amendment (proposed, merge-time)

`../../HYPOTHESES.md` § H-VOL is a **frozen E5-era file** on this branch and is **not edited here**. The
kill condition currently reads: *"the hidden state encodes only the binary high/low class (already known),
or the probe fails to generalize out-of-distribution, or adds nothing over verbalized confidence."* The
proposed merge-time amendment brings it into line with the redesigned contract: *"…or adds nothing over
verbalized confidence, predictive entropy, or a directly-trained correctness probe; or the correctness arm
is not evaluable (too few negatives); or the fidelity is a family-band or continuation-length readout rather
than a within-family geometric quantity."* This amendment is flagged for the registrant to apply at merge
time; it is **not** made on this branch.

## Options considered

- **Thresholds-only hardening (tighten the existing bars, leave the contract shape)** — rejected. The
  rehearsal's `confirmed-shaped` fired with every existing bar cleared; the failure was structural (no
  precondition, wrong fidelity quantity, orphaned B3/B4, no length control), not numeric. Raising numbers
  would not have caught a one-negative arm or a 0.910 length confound.
- **Report-only confounds (compute length/family/entropy diagnostics, keep them out of the verdict)** —
  rejected. The pre-mortem (`../PREMORTEM.md` §1, §2) judged a length control and a B3 clause **mandatory**
  regardless of the rehearsal number: a `confirmed-shaped` verdict at scale with ρ(volume, length) = 0.910
  unaddressed in the *verdict* is one "your probe reads verbosity" review from collapse. A diagnostic that
  cannot change the verdict does not protect it.
- **Degree-based corpus hardening (harder items of the same kinds)** — rejected by the calibration:
  difficulty 1–4 of the original ladder leaves the model at ceiling (rehearsal 0/41 genuine errors), so the
  entire correctness arm would rest on accidental labels. Kind-based hardening was adopted instead.
- **A single collapsed added-value / refuted label** — rejected. Conflating "loses to entropy", "loses to
  the correctness probe", and "does not beat verbalized confidence" under one label would repeat exactly the
  honest-labeling failure the audit targets; each reason routes to a distinct branch. (The reviewer spec
  named three added-value gates but only two new branch labels; the distinct-branch reading is flagged as an
  interpretation in `../VALIDATION.md`, reversible in one line if the registration prefers a collapsed
  label.)
- **Version-record the model revision post-hoc rather than enforce at load** — rejected (as in `e3-0004`):
  the probe reads a specific tensor of a specific checkpoint, so a silent revision change moves the input
  vector; the revision is asserted at load, fail-closed.
- **Keep the pooled-R² OOD bar** — rejected: pooled R² over rotations is dominated by between-family mean
  structure (the family-band confound) and can pass with one family collapsed. Within-held-out-family
  Spearman with a per-family floor is immune to both.

## Consequences

Honest costs, stated rather than hidden:

- **More open threshold parameters.** The redesign adds `min_negatives`, `spearman_fidelity_min`,
  `within_family_spearman_min`, `family_oracle_margin_min`, `ood_pooled_spearman_min`, `ood_per_family_floor`,
  `b3_ci_floor`, `b4_margin_ceiling`, `require_length_robust`, and `correctness_cv_folds` to the registration's
  open set (`../THRESHOLDS-PROPOSAL.md`), retires `r2_ood_min`, and demotes `r2_margin_over_classmean_min` to
  reporting. More parameters is more surface a reviewer can dispute — mitigated by the sweep discipline
  (each swept, verdict computed at the primary, threshold-fragility reported) and by the fact that the new
  bars are set by construction/rehearsal evidence, not tuned on any real datum.
- **Stricter confirmation.** A `confirmed-shaped` verdict now requires clearing four fidelity gates, a
  length gate, an OOD transfer bar with a per-family floor, and three added-value gates — materially harder
  than the pre-redesign two-headline-clause path. This is intended: the rehearsal showed the easy path
  confirmed on empty evidence.
- **`NOT_EVALUABLE` is now a possible outcome.** If the confirmatory corpus produces fewer than
  `min_negatives` negatives (the calibration projects ≈ 0.20–0.25 negative rate, ~25–32 negatives at 126
  answerable, but only if the deduction answer cap is ≥ 768), the correctness arm returns the terminal
  not-evaluable state rather than a verdict. This is honesty, not failure: a false confirmation or refutation
  on 3–6 labels is worse than declaring the arm undecidable.
- **Heavier freeze surface.** Enumerating and hashing every result-moving input, and enforcing the revision
  at load, makes the environment heavier to change — any change to any listed field is a freeze-touching
  event needing a new registration. That rigidity is the intended price of a pre-registration a later reader
  can check was unimpeachable before the data existed (`e3-0004` § Consequences).
- **The claim narrows and sharpens.** Geometry/belief-state framing leaves the claim sentence and becomes
  labeled speculation; the surviving question (does a volume direction transfer where correctness directions
  provably do not, and buy anything over B4/B3/VC) is narrower but, per the deep read, more interesting — a
  YES is volume as the more universal latent quantity; a NO cleanly retires H-VOL.
