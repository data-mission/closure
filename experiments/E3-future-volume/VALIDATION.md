# E3 synthetic validation — the analysis pipeline and verdict-branch logic proven on planted fixtures

**All five fixture classes plant a right answer BY CONSTRUCTION; the pipeline recovers each exactly;
the pre-registered verdict logic routes each to its known branch. 47 tests pass, CPU-only, no model,
no network. The verdict thresholds remain OPEN — fixed only at registration.**

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
- `verdict.py` — the pre-registered branch logic (README § Verdict conditions), parameterized
  entirely by `VerdictThresholds`. **This module invents no threshold value.** Five branches:
  confirmed-shaped, refuted/no-signal, refuted/binary-only, refuted/ood-failure,
  refuted/no-margin-over-verbalized.

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

## What remains open — thresholds fixed at registration, not here

Everything under `validation/` is throwaway-fixture machinery; the code is the real instrument but
the numbers below are NOT set:

- `r2_fidelity_min` — minimum in-distribution R² for "continuous fidelity present".
- `r2_margin_over_classmean_min` — minimum `R²_indist − R²_classmean` for the continuous probe to
  count as reading more than the binarized class.
- `r2_ood_min` — minimum leave-one-family-out R² for "OOD transfer present".
- `auc_binary_min` — minimum SEP-style median-split AUROC for "a binarized signal exists".
- `vc_ci_floor` — the paired-bootstrap CI-low on the probe-minus-verbalized AUROC margin that counts
  as beating verbalized confidence.
- The probe's `alpha` grid and inner-fold count, the bootstrap resample count and CI level — module
  defaults for the synthetic stage; e3-0004 freezes the confirmatory values in the config before any
  real datum is fit.

The `PASSING_THRESHOLDS` in `_fixtures.py` exist ONLY to route the planted fixtures to their known
branches; they are not a registration and carry no scientific commitment. The freeze boundary
(e3-0004) binds none of this until an OSF pre-registration timestamp predates the run.

## pytest summary

```
47 passed in ~8.5s
```

`test_compare.py` 6 · `test_determinism.py` 6 · `test_ood_shortcut.py` 3 · `test_probe_binary_only.py`
4 · `test_probe_nosignal.py` 3 · `test_probe_signal.py` 5 · `test_splits.py` 4 · `test_verdict.py` 9
· `test_volume.py` 7.
