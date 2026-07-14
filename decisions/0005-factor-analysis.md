# 0005 — Factor analysis: library, factorability gate, parallel analysis, rotation, confound control

- Status: proposed
- Deciders: closure research program contributors
- Scope: E0 (the verdict-producing analysis)

## Context
E0's protocol fits "exploratory factor analysis + parallel analysis over the sub-indicator matrix (retention by
Horn's parallel analysis, not eigenvalue > 1)" and partials out length and difficulty. It does not fix the
library, whether the data is even checked for factor-analyzability, the parallel-analysis variant, the rotation,
the correlation type, or the partialling method — and several of these determine the verdict.

## Decision
- **Library:** `factor-analyzer` v0.5.1 (pin the exact version; oblique rotations are built in). It is ~2.5 years
  since its last release but remains the standard tool; pinning the version is supply-chain hygiene.
- **Factorability gate (before fitting):** compute KMO and Bartlett's test of sphericity; proceed only if KMO ≥
  0.6 and Bartlett p < 0.05. If it fails, the pre-registered verdict is **"not factor-analyzable at this N"** — a
  legitimate outcome in its own right, never silently recoded as "closure is a metaphor" (which requires a
  different condition, pairwise |r| < 0.2). This closes a real failure mode: EFA returns a factor structure even
  on data that was never suitable for it.
- **Parallel analysis:** Horn's, implemented as a **manual deterministic routine** — `factor-analyzer` has no
  built-in parallel analysis. Simulate 1000 random datasets of the same shape; retain a factor iff its real
  eigenvalue exceeds the 95th percentile (not the mean) of the simulated eigenvalues; log the RNG seed. The
  unverified `horns` package is deliberately not depended on.
- **Extraction and rotation:** principal-axis extraction, **oblique (promax)** rotation. Orthogonal rotation
  assumes the factors are uncorrelated, which prejudges E0's exact question ("do G, R, P separate?"); oblique lets
  them correlate and reports it.
- **Correlation type:** Spearman rank correlation feeding the EFA — several sub-indicators are bounded or skewed
  (fraction-decorative is near-binary, the min/worst-case indicators are truncated).
- **Confound control:** partial out the difficulty covariates recorded per task in 0001's corpus (token length,
  task family as categorical, source count) as **partial correlations on the correlation matrix before EFA**
  (chosen over residualizing raw scores then re-correlating — the two differ numerically; this one is fixed). E0's
  disproof condition (single factor vanishes after controlling for difficulty) is evaluated on the partialled
  matrix.

## Consequences
Fixes the exact analysis that turns seven sub-indicators into a verdict, including the three outcomes the program
recognizes (closure exists / metaphor / partial collapse) plus the "not factor-analyzable" rail. The rotation and
the factorability gate are the two most consequential choices: oblique-vs-orthogonal decides whether the question
is even askable, and the KMO gate prevents a confident verdict on unsuitable data.
