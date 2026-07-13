# Contributing

This is an open research program. Contributions of experiment runs, tooling, corpora, citation verification, and adversarial review are all in scope. No timelines, no assigned roles — work proceeds when someone does it.

## Evidence standards

1. **Pre-registration before data.** Verdict conditions (confirm/refute thresholds) are written in the experiment's README *before* results exist. Runs are judged against the conditions as written; if a condition proves ill-posed, the amendment is recorded alongside the original, not in place of it.
2. **Negative results are first-class.** A refutation that meets the pre-registered condition changes [HYPOTHESES.md](HYPOTHESES.md) exactly as a confirmation would.
3. **Primary sources only.** A citation supports a claim only after someone has read the primary source. Agent-gathered or secondhand citations are marked as such in [VERIFICATION.md](VERIFICATION.md) and are not load-bearing until flipped.
4. **Baselines are steel, not straw.** Any comparison arm (an "instructed" baseline, a prior method) must be implemented in its strongest reasonable form. A win over a weak baseline is not a result.
5. **Report deviations.** Protocol deviations, excluded data, and failed runs are reported in the results folder, not absorbed.

## How to contribute

**Run or advance an experiment.** Each folder under [`/experiments`](experiments/) ends with a "Wanted from contributors" list. Open an issue declaring what you're taking on (so effort doesn't silently duplicate), then PR into [`/results/<experiment>/<run-id>/`](results/) with: protocol version used, raw artifacts, analysis code, and a verdict written against the pre-registered conditions.

**Verify a citation.** Pick any `unverified` row in [VERIFICATION.md](VERIFICATION.md), read the primary source, and PR the status flip with a one-line note on whether the claim attributed to it is accurate. If it isn't, that's a finding — say so; the dependent text gets corrected.

**Attack the program.** Kill conditions that are under-specified, confounds a protocol misses, prior art the map doesn't list — all accepted as issues or PRs against the relevant document. Adversarial review is a named contribution here, not a courtesy.

**Build the shared tooling.** The G/R/P measurement implementations serve five of the eight experiments (E0's score matrix, E1's labels, E5's contamination detector, E6's post-hoc backend, E7's checks). Clean, reusable, provider-agnostic implementations are the highest-leverage engineering contribution available.

## Ground rules

- MIT license; by contributing you license your contribution the same way.
- Claims in prose must trace to either a verified citation or a results folder. "It is known that" without a pointer gets flagged.
- Discussions in issues; decisions that change a hypothesis's status happen in PRs where the diff is visible.
