# E5 verdict numbers

Numbers only. Verdict interpretation against the three pre-registered outcomes is
written in VERDICT.md — not here.

## Per-arm rates

| arm | contamination (pooled) | change succ/trials | mean completeness | tasks scored |
|---|---|---|---|---|
| A | 0.0280 | 3/107 | 0.9500 | 60 |
| B | 0.0093 | 1/107 | 0.9417 | 60 |
| C | 0.1028 | 11/107 | 0.9917 | 60 |

## Pairwise two-proportion z-tests on pooled contamination (Bonferroni x3, alpha=0.05)

| pair | p_hat_a | p_hat_b | z | p | p_corrected | significant |
|---|---|---|---|---|---|---|
| A vs B | 0.0280 | 0.0093 | 1.0095 | 0.3127 | 0.9382 | False |
| B vs C | 0.0093 | 0.1028 | -2.9713 | 0.0030 | 0.0089 | True |
| A vs C | 0.0280 | 0.1028 | -2.2117 | 0.0270 | 0.0810 | False |

## Completeness non-inferiority (C vs B, paired, delta=0.10)

- mean completeness C: 0.9917
- mean completeness B: 0.9417
- diff (C - B): 0.0500   margin: 0.1000
- non-inferior: true   (paired tasks: 60)

## MDE at the observed B baseline

- B baseline contamination: 0.0093
- MDE (absolute, N=60, power=0.8): 0.0568

## Error draws per arm

- Arm A: 0
- Arm B: 0
- Arm C (uncomputable — Arm A errored): 0
