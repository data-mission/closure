# E3 research log

Append-only, dated, newest last. One entry per working session, written at the end of it — same
convention as the program log (`../../LOG.md`): what was done, what was decided and why, and where the
next session picks up. Scope: E3 instrument work only, on branch `e3-instrument`. E5 is live on `main`
while this branch exists; everything predating this branch is E5's frozen machinery and is not touched
here — E3 work adds files under `experiments/E3-future-volume/` and `e3-*` directories only. When E3
merges, these entries fold into the program log.

---

## 2026-07-14 — E3 instrument work opens: orientation, feasibility spike

**Done.**
- Branch `e3-instrument` cut from `main` at `1a76ad9`. Read the governing set end to end: the E3
  protocol (`README.md` here), H-VOL in `HYPOTHESES.md`, decisions `0001`–`0007`, `METHODOLOGY.md`,
  `STATUS.md`, E0 `PLAN.md` (order-of-work and §Guards), and the harness test conventions
  (`harness/tests/README.md`).
- **Pre-flight discharged at abstract level** (`PREFLIGHT.md`): arXiv:2503.14749 does not preempt
  (uncertainty distillation — SFT for better verbalization); the suspected verbalized-vs-semantic-
  entropy comparison exists in several forms (2505.23845, 2604.24070, 2502.06233) but none uses a
  hidden-state probe as the comparator. Both claimed edges stand, edge (b) narrowed and restated.
  Everything `abstract-checked`, not `verified` — primary-source reads by a named person still gate
  the run.
- **Feasibility spike** (`FEASIBILITY.md`, `spike/`): the local host runs E3. Qwen2.5-7B-Instruct
  4-bit via mlx-lm — 24.2 tok/s generation, 129 tok/s prompt processing, 4.44 GB peak, 12.7 GB
  headroom. Extraction point verified against installed source and proven by a 20/20 lm_head top-1
  sanity check; ground-truth sampling projects to ~3 h (200 prompts) / ~30 h (1000 prompts). No
  fallbacks needed.
- **Four decision records** (`decisions/e3-0001`–`e3-0004` + local README): probe design (ridge,
  linearity-is-the-claim, leave-one-family-out OOD as the load-bearing regime), ground-truth volume
  (N=10, enforced seeded 0.7/0.95, nomic-embed pinned at 768 dims, `log det(G + 1e-6 I)` with the
  centering deviation declared), baselines (frozen verbatim verbalized-confidence elicitation,
  SEP-binarized companion, naive entropy, P(IK)-style control, AUROC + paired bootstrap), and the
  E3 reproducibility standard (seeded-and-reported, not bit-frozen — stated openly against 0006,
  exactness scoped to the committed environment).
- **Synthetic validation** (`VALIDATION.md`, `validation/`): the analysis pipeline and the five
  verdict branches proven on planted fixtures — 47 tests. Linear signal → confirmed-shaped;
  no-signal control stays null; binary-only lands in the SEP-already-known branch via the
  class-mean-margin clause; volume statistic matches hand-computed values exactly; the OOD shortcut
  trap (in-dist R² 0.9997, leave-one-family-out −0.54) proves the OOD regime catches shortcut
  probes. Verdict thresholds are deliberately open parameters — the code invents no number.
- This log opened and closed the session.

**Decided, and why.**
- **E3 decision records are e3-scoped, not global-sequence.** They live in
  `experiments/E3-future-volume/decisions/` numbered `e3-0001`…, in the same MADR shape as
  `decisions/0001`–`0007`, rather than claiming `0008`+ in the global sequence. Two reasons: the global
  sequence and its index are live E5-era machinery this branch does not modify, and E5 work on `main`
  could claim the same numbers concurrently — a merge-time renumbering into the global sequence is
  cheap; a collision is not.
- **Order of work is spike → decision records → synthetic validation, and only then (gated,
  future session) any real data.** The feasibility spike runs before the design records because the
  records must be written for the hardware that will actually host E3 — a probe design fixed for a
  model this machine cannot serve would be ceremony. The spike is an instrument check, not the
  experiment: it establishes that last-token pre-sampling hidden states can be extracted at usable
  throughput, nothing more.
- **The spike's prompts are throwaway by construction.** The 20 prompts used to exercise hidden-state
  extraction must never appear in, or seed, the real E3 corpus — the same anti-contamination ordering
  E0 PLAN step 4 and the harness's synthetic-fixtures convention encode: instruments are proven on
  disposable data first. Stated in `FEASIBILITY.md` alongside the numbers so the constraint travels
  with the artifact.

**Next session starts here.**
1. Corpus construction: real prompts across ≥4 task families with the leave-one-family-out split
   designed in (the protocol names OOD family design as the scientifically load-bearing part). The
   20 spike prompts and all validation fixtures are contaminated by construction and excluded.
2. Fix the verdict thresholds (`r2_fidelity_min`, `r2_margin_over_classmean_min`, `r2_ood_min`,
   `auc_binary_min`, `vc_ci_floor`, alpha grid, bootstrap parameters) — informed by a disposable
   pilot, disclosed per the program's pilot-testing discipline, then frozen into the config hash.
3. Primary-source verification of arXiv:2406.15927 and 2503.14749 by a named reader (citation
   ceiling).
4. OSF pre-registration; only then the confirmatory run. Registration, corpus approval, and the run
   are each gated on an explicit human go — none proceeds on automation alone.

---

## 2026-07-14 — pre-registration package: corpus proposal, pilot, thresholds, registration draft

Same day, second session — items 1–2 of the previous entry's list, plus the registration draft,
brought to registrant-ready state.

**Done.**
- **Corpus proposal** (`CORPUS.md`, `corpus/candidates.jsonl`, PROPOSED): 200 hand-authored prompts,
  five families distinct in kind (arithmetic / factual / deduction / enumeration / creative), 126
  with verified golds for the AUROC subset. Hand-authoring defended on E3-specific grounds: a
  memorized benchmark item depresses continuation diversity — contaminating the *dependent variable*,
  not just the labels. Spike-overlap checked (max token-set Jaccard 0.50, generic frame only);
  arithmetic golds recomputed in assembly; one edge-ambiguous factual item removed rather than
  caveated.
- **Pilot** (`PILOT.md`, `pilot/`): the full instrument end-to-end on 30 fresh throwaway prompts,
  21.7 min wall clock, zero sampling failures, zero verbalized-confidence parse failures. The
  plumbing answer is yes: volume separates prompt kinds with zero overlap between the low end
  (instruction, ≤ −107.7) and the high end (ambiguous/creative, ≥ −19.5); the degenerate floor
  observed in the wild equals the fixture-proven `10·log(1e-6)` exactly; six prompts sit on that
  floor, so the log-volume target carries a mass point at its minimum — recorded for the analysis
  plan. Verbalized confidence showed the literature's near-uniform overconfidence (median 100).
- **Pre-freeze repair to e3-0002/e3-0004** (dated, before any real datum, the 0001-repair pattern):
  the pilot exposed two implicit Gram-moving choices — the nomic task prefix (fixed: `clustering: `)
  and whether embeddings are preprocessed upstream (fixed: raw embeddings in, the instrument centers
  and normalizes once, internally). Embedding revision pinned live:
  `e9b6763023c676ca8431644204f50c2b100d9aab`.
- **Threshold proposal** (`THRESHOLDS-PROPOSAL.md`, PROPOSED): values with their evidence base split
  into literature anchors (SEP's own 0.7–0.95 binarized range → `auc_binary_min` 0.70; verbalized
  confidence at 0.50–0.70 on this model class → strict zero CI floor) and pilot observations (floor
  mass point → modest R² bars 0.10/0.05/0.05 with pre-registered sweeps and a "threshold-fragile"
  label if a verdict flips inside its band). Stated plainly: no published R²/Spearman anchor exists
  for continuous-target hidden-state regression — the field stops at binarized AUROC, so the R² bars
  are justified by construction, not citation.
- **Registration draft** (`REGISTRATION-DRAFT.md`, DRAFT — NOT SUBMITTED): the full OSF package
  assembled from the records — verdict conditions verbatim, all pins, analysis plan with the five
  proven branches, honest spike+pilot disclosure, prior-art positioning, and a gaps-for-the-
  registrant section listing exactly what only a human may close.

**Decided, and why.** The thresholds are proposed, not set — the registration act decides them, and
that act is human. The corpus is proposed, not approved. Both documents say precisely what approval
covers so the sign-off is informed, not ceremonial.

**Next session starts here.**
1. Registrant acts, in order: read the two load-bearing papers (2406.15927 § binarized target;
   2503.14749) and flip their ledger status; approve or amend the corpus; confirm or adjust the
   thresholds; submit the registration on OSF.
2. After the OSF timestamp exists and predates it: the confirmatory run (~3 h for 200 prompts on
   this host), on an explicit go.
3. At merge time: renumber `e3-000N` into the global decision sequence, fold this log into `LOG.md`.

---

## 2026-07-14 — the audit round: five lenses, a rehearsal, and a redesigned contract

Third session of the day. Before freezing anything, the package was attacked: a five-lens adversarial
audit (statistician, hostile reviewer, replication skeptic, interpretability, methodologist — mutually
blind), a labeled dress rehearsal of the full stats path, a pre-mortem (`PREMORTEM.md`), and a
full-text deep-read of every load-bearing citation. The mechanisms mirror the program's E5
pre-execution audit; the yield was larger.

**Found, and fixed (28-defect ledger; the fatal ones):**
- Both claimed novelty edges were preempted at full-text depth: probe-beats-verbalized-confidence by
  arXiv:2509.10625 (same model), continuous-uncertainty regression by the SEP authors' own workshop
  follow-up (BbZKxrZCNn, Wayback-accessed). The claim is re-scoped (REGISTRATION-DRAFT §1): does a
  VOLUME direction transfer across families where correctness directions provably do not
  (arXiv:2506.08572), and does it add value over the correctness probe, entropy, and verbalized
  confidence.
- The verdict machine could confirm on an entropy re-reader, on family-band recognition, or on one
  mislabeled negative (the rehearsal proved the last empirically — it fired confirmed-shaped off a
  single truncation artifact). Rebuilt (`decisions/e3-0005-audit-redesign.md`, instrument at 99
  tests): precondition layer with NOT_EVALUABLE, two-part fidelity on the non-degenerate subset,
  within-family + family-oracle gates, within-held-out-family OOD Spearman with per-family floor and
  range-coverage flag, a length-residualization gate (rehearsal: ρ(volume, length) = 0.910), and
  added-value gates over B3, B4, and the max over verbalized arms — eleven honest branches.
- The corpus made no negatives anywhere (Qwen 100% at every planned difficulty band) and was
  contaminated with pilot prompts. Repaired: kind-calibrated d4 hardening (3×3 multiplication 0.125,
  superheavy-element reverse facts ~0.6, six-seat puzzles 0.2–0.4 — measured, not assumed; expected
  answerable accuracy ≈ 0.78), decontamination against a committed 193-prompt disposable manifest,
  and a committed assembly-verification script.
- Reproducibility spine: model revision now enforced at load; the freeze-hash schema covers the full
  result-moving surface; normalizer and refusal rules are frozen text, not promises.

**Decided, and why.** Fidelity is measured within family or not at all — between-family structure is
the corpus's own design and proves nothing. A verdict that can say "not evaluable" is worth more than
one that always answers. And the claim is now the maximal defensible sentence, no larger.

**Next session starts here.** The registrant package is ready: corpus approval, threshold
confirmation (10 new open parameters), named-reader verification of six papers, OSF submission, then
the gated run. All human acts, in that order.
