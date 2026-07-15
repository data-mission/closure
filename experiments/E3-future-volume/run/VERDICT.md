# E3 confirmatory verdict

**VERDICT: `confirmed-shaped`**

The branch name is the result. Everything below is the evidence the frozen instrument (`e3_validation.verdict.decide`) used to reach it, plus a clearly separated exploratory section carrying zero verdict weight.

## Registered vs observed — every gate quantity

| gate quantity | registered bar | observed |
|---|---|---|
| precondition: n_negatives | >= 15 | 26 |
| continuous fidelity: R^2 (non-degenerate) | >= 0.1 | +0.5485 |
| continuous fidelity: Spearman (non-degenerate) | >= 0.3 | +0.8316 |
| within-family Spearman | >= 0.3 | +0.7183 |
| family-mean-oracle margin | >= 0.05 | +0.3936 |
| length gate: within-family Spearman (length-residualized) | >= 0.3 (require_length_robust=True) | +0.3613 |
| OOD range covered | not uncovered | yes |
| OOD pooled within-family Spearman | >= 0.2 | +0.5717 |
| OOD per-family floor (min rotation Spearman) | >= 0.0 | +0.1939 |
| added value: probe vs verbalized (CI-low) | > 0.0 | +0.1554 |
| added value: probe vs entropy B3 (CI-low) | > 0.0 | +0.2178 |
| added value: B4 vs probe (CI-low, must NOT exceed) | <= 0.0 | -0.1288 |
| B2 reporting: SEP median-split AUROC | (auc_binary_min=0.7; branch-router only) | +0.9098 |
| B2 reporting: class-mean margin (R2_indist - R2_classmean) | (reporting only; r2_margin_over_classmean_min=0.05) | -0.0626 |
| reporting: degeneracy classifier AUROC | (reported, not gated) | +0.8873 |

Precedence outcome: correctness arm evaluable = True (n_negatives 26 vs min_negatives 15); continuous fidelity present = True; degenerate/non-degenerate test split = 6/34.

## Sweep stability

Verdict at the registered primaries: `confirmed-shaped`. Sweep fragility across all registered sweep points: **FRAGILE — verdict flips inside a sweep band**.

| swept parameter | registered points | verdict stable across band? | branches seen |
|---|---|---|---|
| min_negatives | 15*, 20 | yes | confirmed-shaped |
| r2_fidelity_min | 0.05, 0.1*, 0.2 | yes | confirmed-shaped |
| spearman_fidelity_min | 0.2, 0.3*, 0.4 | yes | confirmed-shaped |
| within_family_spearman_min | 0.2, 0.3*, 0.4 | NO | confirmed-shaped, refuted/length-confounded |
| family_oracle_margin_min | 0.05*, 0.1 | yes | confirmed-shaped |
| ood_pooled_spearman_min | 0.2*, 0.3 | yes | confirmed-shaped |
| ood_per_family_floor | 0.0*, 0.1 | yes | confirmed-shaped |
| b3_ci_floor | 0.0* | yes | confirmed-shaped |
| b4_margin_ceiling | 0.0* | yes | confirmed-shaped |
| correctness_cv_folds | 5*, 10 | yes | confirmed-shaped |

`*` marks the registered primary. A parameter whose band shows more than one branch is threshold-fragile (a pre-registered honesty label, not a re-decision).

## Confirmatory vs exploratory separation

**Confirmatory** — only the gate table and sweep above bear on the verdict; the branch is a deterministic function of exactly the `VerdictInputs` fields, decided by the frozen `verdict.decide` at the manifest thresholds.

**Exploratory (ZERO verdict weight)** — the following are descriptive observations that did NOT and cannot move the verdict branch. They are recorded for interpretation only.

- Between-family volume structure: eta^2 = 0.189 (within-family fraction 0.811). Per-family mean volume: arithmetic -65.7; creative -22.8; deduction -74.9; enumeration -71.9; factual -48.5.
- Volume vs continuation length (verbosity confound): Spearman(mean_len) +0.740, Spearman(std_len) +0.553.
- Entropy-volume decoupling: Spearman(volume, entropy) all-prompts +0.200, answerable +0.075.
- Overall greedy accuracy on the answerable subset: 0.794. Accuracy by intended difficulty: d1 39/42 (0.93); d2 37/42 (0.88); d4 24/42 (0.57).
- Accuracy by family: arithmetic 28/42 (0.67); deduction 39/42 (0.93); factual 33/42 (0.79).
- Calibration deviation flagged in the proposal: deduction-d4 = 13/14 correct (accuracy 0.93); the hardening target for d4 was 0.2-0.4. This is a corpus-calibration observation, not verdict evidence.
- Confident errors: 26 answerable items are labeled incorrect; 26 of them carry verbalized confidence >= 90 (max over B1 variants) — the overconfidence pattern the verbalized baseline is expected to show.
- Annotation vs measured diversity bands (expected_diversity label -> measured mean volume): high -30.9 (n=38); low -80.0 (n=70); mid -50.7 (n=92).

## Provenance

- Frozen-config SHA-256: `b3e1d214acba85933fee9e592cc851ce4bc910bf36a1807f26d2f5f015710129`
- Registration status (verbatim from manifest): `none — run ordered by operator 2026-07-15, pre-registration waived`
- Model: `mlx-community/Qwen2.5-7B-Instruct-4bit` @ `c26a38f6a37d0a51b4e9a1eb3026530fa35d9fed` (4-bit).
- Prompts loaded: 200 / 200; unreadable: 0.
- Volume-arm exclusions (refusal rule, < 10 valid continuations): 0 (none).
- Correctness arm: 126 answerable items scored (26 negatives, 100 positives); greedy-truncation exclusions: 0.
- Determinism: two independent compute passes; gate-block SHA-256 run 1 = `10205fcc9e83aa374513c95e7beda5cbd8ddc02c03d3d312844f8748cec8011a`, run 2 = `10205fcc9e83aa374513c95e7beda5cbd8ddc02c03d3d312844f8748cec8011a`; identical = True.
- Analysis wall time: 138.9 s. Seeds from the manifest formulas (base_seed 20260714).

## Honest limitations

This is one decoder-only model (Qwen2.5-7B-Instruct) at 4-bit quantization, read at a single layer via one forward pass, on a hand-authored 200-prompt battery across five task families. The run is UNREGISTERED (`registration: none` in the manifest; pre-registration was waived by the operator), so the thresholds, though fixed in the committed frozen config before analysis, carry the weaker evidential status of a frozen-but-unregistered instrument rather than a timestamped pre-registration. The volume target has no external R^2/Spearman anchor in the literature (the field reports binarized AUROC), the R^2 bars are modest by construction, and the correctness arm rests on a normalizer-scored greedy answer. The verdict generalizes no further than these conditions; the branch name states exactly what was and was not established.
