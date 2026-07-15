# E3 decision records

Operational choices the E3 protocol (`../README.md`) leaves open, recorded in the [MADR](https://adr.github.io/madr/)
format — same convention as the program-level set in `../../../decisions/`.

## Why e3-scoped numbering

These records are numbered `e3-0001`…, not `0008`+ in the global `decisions/` sequence. The global sequence and its
index are live machinery of E5, which is running concurrently on `main`; this branch does not modify it, and E5 work
could claim the same next numbers at the same time. A merge-time renumbering of these four records into the global
sequence is cheap and mechanical; a numbering collision between two branches editing the same index is not. The
`e3-` prefix keeps the two sequences from colliding until merge, at which point they can be folded in.

## Convention

The same MADR rules apply as in the global set: one file per decision area, numbered monotonically, numbers never
reused; status is `proposed` · `accepted` · `superseded by NNNN`; every record states the options considered and the
consequence of the chosen one, not only the choice. Each record here **refines** the E3 protocol — it adds precision
to what the protocol leaves open and never contradicts anything the protocol fixes.

## Status of this set

All records below are `proposed`. **No decision is binding until it is frozen in the pre-registration on OSF** (same
rule as the global set; see `../../../decisions/README.md` and `../../../decisions/0006-reproducibility-and-freeze.md`).
Until then these record the current best-justified choice, open to challenge like everything else in the program.

## Index

- [e3-0001](e3-0001-probe-design.md) — probe class, input vector, regression target, standardization, evaluation regimes
- [e3-0002](e3-0002-ground-truth-volume.md) — continuation sampling, embedding model, semantic-volume statistic, exclusions
- [e3-0003](e3-0003-baselines.md) — the comparator set (verbalized confidence, SEP-style probe, naive entropy, P(IK) probe) and the comparison procedure
- [e3-0004](e3-0004-reproducibility-standard.md) — E3's seeded-and-reported reproducibility posture, pins, and freeze boundary
- [e3-0005](e3-0005-audit-redesign.md) — audit-driven verdict-contract redesign (precondition layer, two-part fidelity, within-family + OOD-Spearman gates, added-value gates, kind-based d4 hardening, revision enforcement, full freeze-hash schema)
