# E3 synthetic validation — the analysis pipeline and verdict-branch logic proven on planted fixtures

**All fixture classes plant a right answer BY CONSTRUCTION; the pipeline recovers each exactly; the
pre-registered verdict logic routes each to its known branch. 99 tests pass, CPU-only, no model, no
network. The verdict thresholds remain OPEN — fixed only at registration.** The instrument was
rebuilt on 2026-07-14 to close the holes the labeled dress rehearsal (`REHEARSAL.md`) exposed — see
**Audit-driven redesign (2026-07-14)** below for the new modules, gates, fixtures, and open params.

The anti-fishing point, same ordering as the harness (`harness/tests/README.md`, E0 PLAN step 4):
validate the analysis logic and the verdict-branch logic on throwaway data whose answer is known
before any real corpus exists, so the instrument cannot be tuned to a real result afterward. The
modules under `validation/src/e3_validation/` **are** the E3 analysis instrument a later gated
session will point at real hidden states — not a mock. Fixtures are generated in-code with fixed
seeds (`validation/tests/_fixtures.py`); **no data blob is committed**.

Environment: `validation/` is a uv project — Python 3.12.13, numpy 2.5.1, scikit-learn 1.9.0,
scipy 1.18.0, pytest 9.1.1; `pyproject.toml`, `uv.lock`, `.python-version` committed. Run with
`uv run pytest` from `validation/`.

## Pipeline modules (one per stage, deterministic and seeded)

- `volume.py` — `log det(G + 1e-6 I)` over the N embeddings **mean-centered THEN L2-normalized**
  (e3-0002). Order note: e3-0002 § Decision states "mean-center the N vectors, L2-normalize them,
  form the N×N Gram matrix" — centering **before** normalization; that is implemented, and it is the
  order the task's ambiguity clause names as the default either way. Zero rows (all continuations
  identical → every centered vector is zero) are left at zero rather than dividing 0/0, so the Gram is
  exactly the zero matrix. float64 throughout.
- `probe.py` — ridge probe (e3-0001): z-score standardizer fit on **train only**; `alpha` from a
  log-spaced pre-registered grid via inner k-fold CV **on train only**; closed-form fit; returns R²
  and Spearman on any eval split. Plus the SEP-style logistic **median-split** probe (median on train
  only), returning AUROC (B2 of e3-0003). Plus `class_mean_predictor_r2` — the oracle ceiling of
  binarized-only information, the quantity the binary-only branch compares against.
- `splits.py` — seeded in-distribution split and leave-one-family-out OOD rotation (e3-0001).
- `compare.py` — AUROC and paired-bootstrap CI for probe-vs-baseline AUROC differences (e3-0003);
  resample count and CI level are explicit parameters recorded on the result.
- `preconditions.py`, `fidelity.py`, `ood.py`, `correctness.py`, `loader.py`, `freeze.py` — the
  audit-driven redesign modules; see **Audit-driven redesign (2026-07-14)** below.
- `verdict.py` — the pre-registered branch logic (README § Verdict conditions), parameterized
  entirely by `VerdictThresholds`. **This module invents no threshold value.** Redesigned branch set
  (see below): confirmed-shaped; the terminal not-evaluable/correctness-arm; and the refuted branches
  no-signal, margin-only, binary-only, length-confounded, ood-range-uncovered, ood-failure,
  no-margin-over-verbalized, no-margin-over-entropy, dominated-by-correctness-probe.

## The five fixture classes: planted answer vs observed result

Metrics are on the seeded fixtures at the seeds in `_fixtures.py`; the throwaway routing thresholds
(`PASSING_THRESHOLDS`) are `r2_fidelity_min=0.50`, `r2_margin_over_classmean_min=0.10`,
`r2_ood_min=0.50`, `auc_binary_min=0.70`, `vc_ci_floor=0.0`. Every fixture sits well clear of every
bound (no knife-edge routing).

### A — linear signal that transfers OOD → confirmed-shaped
`y = w·x + 0.05·noise`, same signal direction `w` in every family; families differ only by a
nuisance offset **orthogonal to `w`**, so the target is family-invariant.
- Planted: probe recovers `w`; R²/Spearman ≈ 1 in-dist AND OOD; continuous R² ≫ class-mean R²;
  probe beats a weak verbalized-confidence arm.
- Observed: in-dist R² **0.9977**, Spearman **0.9978**; class-mean R² 0.6032 (margin **+0.395**);
  pooled leave-one-family-out R² **0.9963**; probe−VC AUROC diff **+0.209**, 95% paired-bootstrap CI
  **(0.135, 0.285)**, excludes zero. → **confirmed-shaped**.

### B — no-signal negative control → refuted/no-signal
`y` drawn independently of `x`.
- Planted: no map exists; held-out R² ≈ 0 (must not be manufactured positive); binarized AUROC ≈ 0.5.
- Observed: held-out R² **−0.0101**; median-split AUROC **0.605** (< 0.70 bar). → **refuted/no-signal**.

### C — binary-only (the discriminating case) → refuted/binary-only
`x = c·u·mag + noise` encodes only the class `c = sign(y)`; within-class magnitude of `y` is
independent of `x`.
- Planted: logistic median-split AUROC high; continuous R² does NOT materially exceed the class-mean
  predictor (everything `x` says about `y` is the class — the signal SEP already established).
- Observed: median-split AUROC **0.9865**; continuous R² 0.6544 vs class-mean R² 0.8405, margin
  **−0.186** (ridge cannot even fully match the oracle class-mean; well below the +0.10 margin bar).
  Note R² 0.654 alone clears `r2_fidelity_min` — it is the **class-mean margin clause** that denies
  fidelity, which is exactly the SEP-already-showed-this guard. → **refuted/binary-only**.

### D — volume statistic, hand-computed → exact
- N identical vectors → centered Gram is the zero matrix → `log det = N·log(ε)` **exactly**: N=10
  gives −138.15510557964274, observed difference from `10·log(1e-6)` = **0.0**.
- N standard-basis vectors → centered-normalized Gram eigenvalues `{0, N/(N−1) (×N−1)}` →
  `log(ε) + (N−1)·log(N/(N−1) + ε)`; observed matches for N=3..6 to **<1.3e-10**. Two opposite
  vectors → `log(2ε + ε²)`, matches to **<1e-9**.
- Strictly monotone in a planted dispersion parameter (orthogonal spread `s`): volume strictly
  increasing across `s ∈ [0.05, 1.5]` (asserted `np.diff > 0`).
- ε-stability: finite and ordered `v(1e-8) < v(1e-6) < v(1e-4)` for the registered ε and neighbours;
  with ε=0 the un-ridged centered Gram is singular and volume is correctly `−inf` (the reason the
  rank-safety ridge exists, e3-0002).

### E — OOD shortcut trap → refuted/ood-failure
A family-specific indicator coordinate (value 10) carries each family's mean (spanning [−5, 5], large
variance); the true signal is weak (0.3·`x·w`). Ridge provably prefers the high-variance shortcut
in-distribution; under leave-one-family-out the held-out family's indicator is constant-zero in
training, so its coefficient is inert.
- Planted: in-dist R² ≈ 1 (shortcut works on seen families); pooled OOD R² collapses far below zero.
- Observed: in-dist R² **0.9997** (margin over class-mean +0.261); pooled leave-one-family-out R²
  **−0.54**. This proves the OOD regime catches a shortcut an in-distribution-only evaluation would
  have scored as success. → **refuted/ood-failure**.

The fifth branch, **refuted/no-margin-over-verbalized** (fidelity + OOD transfer present but the
probe does not beat verbalized confidence), is not reachable from a single data fixture — it is a
property of the correctness-prediction comparison — and is covered directly in `test_verdict.py`
with a planted metric tuple, alongside boundary tests confirming the `>=` bars are inclusive and the
beats-VC floor is strict.

## Determinism check (e3-0004 algorithmic-exactness claim)

Every pipeline function run twice with the same seed yields **bit-identical** output (asserted with
`==` / `np.array_equal`, not tolerance): `semantic_volume`; the ridge probe (`alpha`, R², Spearman,
predictions); `select_alpha`; the logistic median-split probe (threshold, AUROC); the seeded split;
the paired bootstrap (full dataclass equality). This is the exact-reproducibility half of e3-0004:
the closed-form ridge fit on a fixed feature matrix and the volume computation on fixed embeddings
are exactly reproducible; the seeded steps reproduce identically given the same seed. (e3-0004's
non-bit-exact caveat concerns Metal/GPU activation extraction upstream — outside this CPU-only,
numpy/sklearn synthetic stage.)

## Audit-driven redesign (2026-07-14)

The labeled dress rehearsal (`REHEARSAL.md`, 41 disposable prompts) fired the strongest verdict
branch (confirmed-shaped) off a correctness arm carrying **one** negative, from a fidelity number the
volume ↔ length rank correlation of **0.910** and the between-family volume variance (η² = 0.255)
could each fully explain. The verdict contract was rebuilt to make those failures impossible. Every
new behaviour has planted-answer fixtures and tests in the established style.

### New modules (`validation/src/e3_validation/`)

- **`preconditions.py`** — the correctness arm must carry evidential mass. `correctness_arm_evaluable`
  gates on a pre-registered `min_negatives`; below it `decide` returns the terminal, honest
  `NOT_EVALUABLE_CORRECTNESS_ARM` (not a refutation), checked BEFORE any branch. `exclusion_report`
  tallies per-family excluded/answerable counts.
- **`fidelity.py`** — two-part target + within-family fidelity. `degenerate_mask`/`degenerate_floor`
  split out items on the exact `N·log(ε)` floor; `degeneracy_auroc` reports the floor classifier
  separately; `continuous_fidelity` scores R² AND Spearman on the NON-degenerate subset only;
  `within_family_metrics` scores volume/predictions residualized on train-derived family means (immune
  to between-family means); `family_mean_oracle_r2` is the family-band ceiling the probe must beat;
  `length_residualized_within_family_spearman` supports the length gate.
- **`ood.py`** — `leave_one_family_out_spearman` scores the rank correlation INSIDE each held-out
  family (pooled = **mean over rotations**, pinned), retains the per-rotation minimum for a per-family
  floor, and flags `range_uncovered` (a materially out-of-range held-out family = extrapolation, not
  transfer) with a relative guard-band against finite-sample tail noise.
- **`correctness.py`** — frozen `ORIENTATION` table (`probe = −predicted_volume`, `B3 = −entropy`,
  `B4 = P(correct)`, `verbalized = stated_value`); `probe_scores_oof` / `b4_scores_oof` are the ONLY
  scoring paths and are strictly out-of-fold (seeded k-fold, no in-sample path); the missing-VC rule
  masks to the VC-present subset for verbalized comparisons and `arm_aurocs` reports both subsets.
- **`loader.py`** — `load(model_id, revision, loader_fn)` fails closed unless the resolved snapshot
  equals the pin, and records the SHA-256 of a canonical probe rendered through the chat template
  (`ChatTemplateMismatchError` catches a template change under an unchanged revision). Injected loader
  → no model download in tests.
- **`freeze.py`** — `FrozenConfig` enumerates EVERY result-moving input (corpus/golds hashes, refusal
  regexes, normalizer spec version, ε, N, sampler, base seed + split/bootstrap/CV seed FORMULAS, alpha
  grid, inner/CV folds, bootstrap n/CI, test fraction, ALL verdict thresholds incl. the new ones,
  model/tokenizer/embedder revisions + chat-template hash, dims, library versions, orientation table)
  → sorted-key JSON → SHA-256. The hash is stable across key order and changes on any field change.

### New / changed verdict gates (`verdict.py`)

`VerdictInputs` now enumerates exactly the redesigned quantities and `VerdictThresholds` carries all
new params. Decision precedence: **precondition** → **continuous fidelity** (R² + Spearman on the
non-degenerate subset, within-family Spearman, family-mean-oracle margin — the family-oracle margin
replaces the 2-bin class-mean margin as the gate; the old class-mean margin is retained as B2
reporting) → **length gate** (within-family fidelity must survive residualizing volume on
mean+std continuation length) → **OOD range** → **OOD transfer** (pooled within-family Spearman AND
per-family floor) → **added value** (probe beats verbalized AND probe beats B3 entropy AND B4 does
not beat probe — paired-bootstrap CIs). OOD is resolved BEFORE the verbalized/added-value gates.

New branches: `NOT_EVALUABLE_CORRECTNESS_ARM`, `REFUTED_LENGTH_CONFOUNDED`,
`REFUTED_OOD_RANGE_UNCOVERED`, `REFUTED_NO_MARGIN_OVER_ENTROPY`,
`REFUTED_DOMINATED_BY_CORRECTNESS_PROBE`, and **`REFUTED_MARGIN_ONLY`** — the fix for the row the
pre-redesign code mislabeled `refuted/no-signal` (above-floor R² that fails the margin/within-family
gates with no binarized signal is margin-only, not no-signal). The three distinct added-value branches
(verbalized / entropy / B4-dominated) are a deliberate choice to name each honest reason separately
rather than conflate them; this is flagged as an interpretation of the spec (see below).

### New fixtures (`tests/_fixtures.py`)

- `passing_inputs(**overrides)` — a fully gate-satisfying `VerdictInputs` for one-dimension-at-a-time
  branch tests.
- `make_family_band_only` — heterogeneous family MEANS with NO within-family signal (the fixture the
  old suite lacked): passes a naive pooled/full R² and binarized AUROC but the within-family Spearman
  is ~0 and the family-oracle margin ~0 → routes **refuted** (never confirmed).
- `make_family_specific_signal` — genuine within-family signal in a family-specific block: learnable
  in-distribution, does NOT transfer OOD → `REFUTED_OOD_FAILURE` (a collapse, ranges covered).
- `make_degenerate_mixed` — a degenerate-floor mass point plus a continuous population, cleanly and
  disjointly encoded; the two-part treatment recovers the floor and scores continuous fidelity on the
  non-degenerate subset.
- `make_length_confound` — volume ≈ a linear readout of continuation length; within-family fidelity
  holds until the volume is residualized on length, then collapses → `REFUTED_LENGTH_CONFOUNDED`.
- `make_correctness_arms` — a full arm bundle (probe/B3/B4/verbalized with missing VC) exercising the
  added-value gates and the missing-VC rule.

Fixture E (`make_ood_shortcut`) is re-read: under the within-family OOD Spearman its genuine
within-family signal DOES transfer (its collapse was between-family LEVEL, i.e. the family-band
confound the redesign rules out), so it no longer routes `refuted/ood-failure` — its test now
documents the pooled-R²-collapse vs within-family-transfer contrast. The old `test_verdict.py`
five-field tuples and the pipeline tests' `VerdictInputs` constructions embodied the superseded
pre-redesign contract (`r2_ood`/`r2_ood_min`, class-mean margin as the fidelity gate) and were
updated; the analysis logic itself was not weakened to fit any test.

### New open threshold params (added to the registration's open set)

- `min_negatives` — minimum negatives for the correctness arm to be evaluable (rehearsal proposed
  ≥ 20). **NEW; must be registered.**
- `spearman_fidelity_min` — Spearman bar on the non-degenerate subset (the floor-mass-robust half).
- `within_family_spearman_min` — within-family Spearman bar (also the length-residualized bar).
- `family_oracle_margin_min` — minimum `probe R² − family-mean-oracle R²`.
- `ood_pooled_spearman_min`, `ood_per_family_floor` — the within-family OOD transfer bars (replace
  `r2_ood_min`).
- `b3_ci_floor`, `b4_margin_ceiling` — the entropy-beat and B4-non-domination bars.
- `require_length_robust` — whether the length gate is enforced.
- `correctness_cv_folds` (k) — the out-of-fold correctness-scoring fold count.

`THRESHOLDS-PROPOSAL.md` proposes values for the pre-existing bars; the NEW bars above have no proposed
value yet and are open for the registration decision.

### Contract ambiguity flagged

The reviewer's spec named three added-value gates (beats verbalized, beats B3, B4 non-domination) but
enumerated only two new branch labels (`REFUTED_MARGIN_ONLY`, `ROOD_RANGE_UNCOVERED`). Rather than
conflate three distinct scientific failure reasons under one label — which would repeat exactly the
honest-labeling failure the audit targets — each added-value failure and the length-gate failure route
to a DISTINCT branch (`REFUTED_NO_MARGIN_OVER_VERBALIZED`, `REFUTED_NO_MARGIN_OVER_ENTROPY`,
`REFUTED_DOMINATED_BY_CORRECTNESS_PROBE`, `REFUTED_LENGTH_CONFOUNDED`). This is an interpretation, not
a deviation from the gate semantics; if the registration prefers a single collapsed label it is a
one-line change to the enum mapping.

## What remains open — thresholds fixed at registration, not here

Everything under `validation/` is throwaway-fixture machinery; the code is the real instrument but
the numbers below are NOT set:

- `r2_fidelity_min` — minimum R² on the non-degenerate subset for "continuous fidelity present".
- `spearman_fidelity_min` — minimum Spearman on the non-degenerate subset (**NEW**, floor-robust).
- `within_family_spearman_min` — minimum within-family Spearman, and the length-residualized bar
  (**NEW**).
- `family_oracle_margin_min` — minimum `probe R² − family-mean-oracle R²` (**NEW**; the fidelity gate
  that replaces the class-mean margin).
- `r2_margin_over_classmean_min` — the old `R²_indist − R²_classmean` margin, RETAINED as B2 reporting
  only (no longer a fidelity gate).
- `ood_pooled_spearman_min`, `ood_per_family_floor` — the within-family OOD transfer bars (**NEW**;
  replace the old `r2_ood_min` pooled-R² bar).
- `auc_binary_min` — minimum SEP-style median-split AUROC for "a binarized signal exists".
- `vc_ci_floor`, `b3_ci_floor` — the paired-bootstrap CI-low floors for beating verbalized confidence
  and predictive entropy (`b3_ci_floor` **NEW**).
- `b4_margin_ceiling` — the ceiling the (B4 − probe) CI-low must not exceed (**NEW**).
- `min_negatives` — the correctness-arm precondition (**NEW**).
- `require_length_robust` — whether the length gate is enforced (**NEW**).
- The probe's `alpha` grid and inner-fold count, the correctness out-of-fold `k`, the bootstrap
  resample count and CI level — module defaults for the synthetic stage; e3-0004 freezes the
  confirmatory values in the config before any real datum is fit.

The `PASSING_THRESHOLDS` in `_fixtures.py` exist ONLY to route the planted fixtures to their known
branches; they are not a registration and carry no scientific commitment. The freeze boundary
(e3-0004) binds none of this until an OSF pre-registration timestamp predates the run.

## pytest summary

```
99 passed in ~16s
```

`test_compare.py` 6 · `test_correctness.py` 9 · `test_determinism.py` 6 · `test_fidelity.py` 8 ·
`test_freeze.py` 5 · `test_loader.py` 5 · `test_ood.py` 7 · `test_ood_shortcut.py` 3 ·
`test_preconditions.py` 5 · `test_probe_binary_only.py` 5 · `test_probe_nosignal.py` 3 ·
`test_probe_signal.py` 6 · `test_splits.py` 4 · `test_verdict.py` 20 · `test_volume.py` 7.
