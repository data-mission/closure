# Research log

Append-only, dated, newest last. One entry per working session, written at the end of it. Each entry:
what was done, what was decided and why, and where the next session picks up. This is the program's working
memory — the polished docs say what is true now; this says how it got there and what happens next.

---

## 2026-07-13 — execution plan filed

**Done.** The program had protocols (what to test) and a results contract (how to report) but no plan for
building and running the measurement instrument — the gap CONTRIBUTING names as the highest-leverage
contribution. Filled it:
- `decisions/0001`–`0007` — the methodology choices each protocol leaves open, frozen with their reasoning
  (generation, grounding, rigidity, ambiguity, factor analysis, reproducibility/freeze, E5). All `proposed`
  until pre-registered.
- `experiments/E0-closure-existence/PLAN.md` — the ordered build-and-run path to a first verdict, with the
  guards as harness acceptance criteria.
- `background/methodology-provenance.md` — how the plan was derived (distilled; no transcripts).
- `CITATION.cff`; README Documents list points at the new layer.

**Decided, and why.**
- Kept the plan lightweight (research-artifact repo, not a tool repo): no CI/Makefile/CONTRIBUTING ceremony
  until there is code to coordinate — matches how frontier-lab research-artifact repos are actually shipped.
- Verdict rule gets validated on synthetic scores *before* the harness is built, so its correctness is checked
  while the data is still throwaway (building the scorer first means tuning it against real output, after which
  honest pre-registration is impossible).
- Two changes came out of adversarial review and are load-bearing: the generation API has no seed, so LLM
  output is distributional-not-exact and E5's contraction is algorithmic (not a re-generation); and a KMO/
  Bartlett factorability gate was added so a verdict is never computed on data that was never factor-analyzable.

**Next session starts here.**
1. Pin the generation model (decision 0001 — a cost/capability call). This unblocks the pre-registration.
2. Tracer-bullet run: take ONE task through the entire pipeline (generate → G/R/P → factor analysis → written
   verdict) at toy scale before building for 150. Fastest way to find "the approach or the metric is wrong."
3. When the first code lands, arm two deferred practices (not needed while the repo is markdown): a committed
   `uv.lock` + `.python-version` for the environment, and the config-freeze mechanism — serialize the frozen
   config to sorted-key JSON, SHA-256 it, put the hash in the OSF registration, and add a pre-commit check that
   fails on drift. That hash is what turns "we froze the plan before data" from a claim into something a reader
   can verify in one command.

---

## 2026-07-14 — public launch architecture + the E0 governance correction

**Done.** Two bodies of work landed on `main` (HEAD `fcdd346`).

Launch architecture: `AUTHORS.md` (originator + how contribution is credited), `STATUS.md` (present stage,
sectioned), `OBJECTIONS.md` (objections classified and answered), a `CITATION.cff` naming the author, and README
authorship + "Choose your entry point" navigation. Release notes, initial issues, discussion seeds, and outreach
copy are staged privately (not in this repo).

Governance: E0 was declared a gate over the whole program. A pre-execution audit found a category error — "one
object to specify over" was conflated with "one scalar latent factor," and a first fix over-corrected into a
single super-hypothesis. Corrected to a **claim lattice** under one rule: *each experiment may directly retire
only the claim it measures; broader claims survive, weaken, or die by their explicit dependencies*. H-CORE →
H-SCALAR (scalar aggregation only); H-ENFORCE / H-RELEASE / H-LOWER / H-COMPOSE each carry a scoped kill and no
E0 dependency; H-CONTROL-PLANE and H-NATIVE added as future architectural hypotheses (the control plane itself a
future lattice, not a monolith); a consequence matrix states what survives each result. The correction is
recorded in `background/reduction-history.md` as a versioned repair made before any run.

The README now also carries the long-term architectural thesis (`Human intent → structural specification →
lowering → mechanisms → execution → inspection → observable`) with its three stages (now / tested by E0–E7 /
possible later), labelled conditional. Both figures (dependency graph, claim structure) were regenerated from
their `.mmd` sources and visually verified.

**Decided, and why.** The governance now mirrors the ontology it tests — preserve distinctions, couple each
claim to its evidence, release only what evidence invalidates, don't collapse prematurely. That is the
strongest available protection against the originator's (and any collaborator's) positive bias: no single
result can be read as validating the whole.

**State.** HEAD `fcdd346`, clean, pushed. No experiment has run. All decision-record pins remain PROPOSED until
the OSF freeze. Hard rules unchanged: no AI/"Claude" mention anywhere in the repo or commit messages.

**Next session starts here.**
1. Two independent tracks — pick either:
   - **Launch (no code):** stage in `_dev_notes/closure-ir-research/LAUNCH-KIT.md`. Order: mint a Zenodo DOI on a
     `v0.1.0` tag (highest value — turns the self-asserted-timestamp nonconformance into an attested fact) →
     publish the v0.1 release → open the 7 issues → enable Discussions + seeds → outreach (repo first).
   - **Science:** pin the generation model (decision 0001) → tracer-bullet run (ONE task through the whole
     pipeline at toy scale) → OSF pre-register E0 before its first real run.
2. The E0-vs-E5 opener still hinges on one external fact: OSF pre-registration latency (self-serve days vs
   institutional weeks). Resolve that before committing the order.

---

## 2026-07-14 — E5 opens the program; the G-slice harness lands

**Decided, and why.** E5, not E0, is the opener. Re-deriving the experiment ordering against the claim lattice:
E0 decides scalar aggregation only (H-SCALAR) and is thesis-neutral by the consequence matrix — its likely
outcome is confounded with the instrument's own structure (each construct's sub-indicators share one method, so
per-construct separation is predicted by method variance alone; this mono-method debt is recorded for E0's own
protocol before its freeze). E5 is the cheapest thesis-relevant test: API-only, no GPU, no second key for the
registered primary run, and either outcome moves the thesis — a mechanical-contraction win is the first
controlled operator evidence, a null retires `release` cheaply.

**The E5 design repair, before any run.** A pre-execution audit found two defects in E5's protocol and both were
closed before any pilot or corpus exists. First, a selection-on-outcome loop: the contamination detector both
built Arm C (choosing what to delete) and scored the outcome (what contamination remains), so C won partly by
construction. The detector is now scoped to Arm C's contraction only; the outcome is referenced to per-task
ground-truth annotations — must-change and must-persist conclusions — that the contraction rule never touches.
Second, a missing dimension: with contamination the only measure an arm can win by deletion, so completeness
(retention of must-persist conclusions) is added as a co-primary with a pre-registered non-inferiority margin
(δ = 0.10), and a contamination win with inferior completeness is pre-registered as *contraction wins by
deletion* — a failure, not a confirmation. Recorded in `background/reduction-history.md`.

**Pre-flight facts (web-verified, 2026-07-14).** ReviseQA, DeltaLogic, and Belief-R do not preempt the 3-arm
design: each compares update *presentation* (all appends) or measures instruction-level revision — none carries a
mechanical-rebuild arm with downstream-contamination annotations, so the corpus is not duplicative. DeltaLogic's
changed/control labeling is the same shape as our must-change/must-persist outcomes — cited as metric lineage,
novelty claimed only on the 3-arm delivery comparison plus mechanical rebuild. XTrace advertises AGM contraction
as a runtime operation but its live API docs (fetched directly) expose only active/archived memory states and its
product is not released — the "first controlled comparison" priority claim is therefore claimable today but
time-pressured. Replication arm pinned to `gpt-5.4-mini-2026-03-17` (the only GPT tier with frozen dated
snapshots; the 5.6 family has none and is unusable for pre-registration).

**Built.** `harness/` — the first code in the repo, a `uv` project (`closure-harness`) with committed `uv.lock`
and `.python-version`, and the two deferred practices from the 2026-07-13 entry now armed: a frozen-config
mechanism (sorted-key JSON → SHA-256, committed hash file, `scripts/check_config_freeze.py` that fails on drift)
and the config hash itself as the pre-registration freeze token. The G-slice modules match decisions 0001/0002/
0006/0007: the NLI grounding scalar (pinned DeBERTa-MNLI checkpoint), the leave-one-out contrast, the
contamination detector (scoped to contraction), the deterministic Arm-C contraction with a derived — never
regenerated — conclusion, ground-truth outcome scoring, and the comparison test (two-proportion z-test with
Bonferroni correction, MDE for N=60, completeness non-inferiority). The scoring modules import no provider SDK —
generation takes an injected callable that halts on a model-identity mismatch.

Synthetic fixtures were committed with the harness, before any real data or model run exists — validating the
detector, contraction, outcome, and stats logic on hand-computed cases while the data is still throwaway is the
anti-fishing point. The detector flags exactly the planted set across the full sensitivity sweep; contraction
reaches a hand-computed fixpoint and serializes byte-identically across runs; the deletion trap scores
contamination 0 *and* completeness 0; the z-test matches scipy and non-inferiority is correct at the exact
boundary; an import-hygiene test proves the outcome scorer never reaches the detector. The single real-model test
is `slow`-marked and confirms NLI direction (entailed above contradicted) at measured throughput.

**Next session starts here:** S3 — corpus construction per the execution plan (60 tasks, verified A-dependency,
must-change / must-persist annotations authored at construction time).

---

## 2026-07-15 — the E5 pilot completes; the corpus freezes at 60

**The pilot ran, and the instrument's noise floor is now measured, not assumed.** All 150 candidate
tasks (50 per family) went through the two-state, three-draw A-dependency filter — 900 generations,
about $6.4 of metered cost, one instrument-noise event: two generations returned a provider-overload
error and were re-scored on their two clean draws (both tasks retained). 136 of 150 candidates passed
(91%); the 14 exclusions were all the same shape — no conclusion that flips when the correction
replaces the assumption — which is exactly the one thing the filter exists to remove. Per-family
retention was 42/50, 44/50, 50/50.

**The three-draw majority is robust but not noiseless, so the noise got a disclosed pruning rule.**
A conclusion can be a genuine assumption-dependency for its task yet, under the stochastic sampler,
still be asserted in the majority of correction-state draws — a scorer target the model does not
reliably retract even in the clean corrected world. Keeping such an item in the scored set would let
all three arms be measured against a target that carries no real signal. The rule: for every retained
task, drop from the scored set any conclusion still asserted in ≥2 of its correction-state draws.
26 items across 26 tasks were pruned (each affected task lost exactly one of two); the invariant that
every retained task keeps ≥1 scored conclusion held with no violations. The false-stale floor is
about 18% of retained tasks — characterized, disclosed, not swept under the sampler.

**Two selection amendments, both decided before any arm ran.** The pilot also flags a task when a
must-persist conclusion changes assertion state across the two evidence states — a suspected leak of
the assumption into a conclusion that was supposed to be assumption-independent, which would let the
completeness co-primary punish correct revision. 23 tasks were flagged. Rather than adjudicate them
one by one, the final set was restricted to unflagged tasks. That exclusion collided with a
difficulty-covariate target: the flagged tasks turned out to be almost exactly the quantitative
family's short-source-count tasks (16 of its 17), so removing them left that family unable to meet the
source-count spread quota. The quota — a covariate-reporting target that carries no verdict weight —
was relaxed to the feasible maximum for that family only; the other two families kept their quotas.
The consequence is stated as a limitation: that family's short-context stratum is thin, so any
short-context effect inside it is exploratory. Both amendments change only which tasks enter the
corpus, never the frozen scoring configuration.

**Frozen at 60, family-balanced 20/20/20.** Selection is deterministic — task_id ascending, quota
reservations then fill — recorded so nothing is a hidden judgment call. The committed corpus carries
only the task records: sources, the assumption and its correction, the question, and the two
annotation sets, with all drafting-provenance stripped. The pilot logs and the full candidate pool,
the selection audit trail, and the pruning register stay in private notes; the pre-registration will
cite the exclusion counts and the configuration hash.

**Next session starts here:** S4 — the OSF pre-registration. The protocol and the public registration
draft are filled with the pilot's real numbers and the two amendments; the remaining step is to freeze
the harness commit, re-read the configuration hash at the moment of registration, and deposit the
pre-registration before the first registered arm runs.

## 2026-07-16 — E5 registered run: H-RELEASE refuted

**The gate changed form before the run.** The freeze-before-data gate was executed as
freeze-by-public-commit rather than an OSF deposit: the corpus (`5deb8eb`, 15:11:40Z) and
the Arm-B instruction (`379c767`, 15:25:40Z) were public on origin before the first paid generation
(15:28:29Z). The verifiable chain is recorded in the run folder's `GATE-RECORD.md`. The gate was
executed manually with the lean driver rather than the in-code-gated runner; recorded as a deviation,
not absorbed.

**The run.** 60 tasks, three arms, 120 generations, zero provider errors; Arm C derived
deterministically from Arm A by the frozen contraction; a claim-level sanitation repair (invalid source
citations stripped identically in every arm) was applied before any outcome existed and is disclosed as
PROTOCOL §9a–9e. The statistics phase crashed on a JSON serialization defect after all 180 score rows
were banked; the summary was regenerated from the banked rows via the frozen stats functions and every
test statistic was independently re-derived by hand — exact match.

**The verdict is REFUTED, in a form sharper than registered.** Contamination: naive append 3/107
(2.8%), instructed disregard 1/107 (0.9%), mechanical contraction 11/107 (10.3%). B-vs-C cleared the
Bonferroni-corrected threshold with contraction WORSE (p = 0.0089); A-vs-C did not survive correction;
contraction's completeness was non-inferior (0.992 vs 0.942) — no win-by-deletion in either direction.
None of the three registered outcome blocks fires literally: the registered REFUTED wording assumed no
significant separation, and the run produced a significant reversal. Recorded as a pre-registration
wording defect and adjudicated REFUTED-in-stronger-form; `release` as formulated is retired. The
task-level robustness read agrees with the pooled test (contraction worse on 9 tasks, instruction worse
on 0; sign test p = 0.0039); the observed gap is 2.2× the minimum detectable effect.

**Post-verdict analyses armor the result.** An exhaustive per-item rescore (681 items) reproduced every
banked aggregate exactly; the Arm-C regeneration check matched all 60 logged fingerprints bit-for-bit
(the pre-registered validity gate, affirmed with evidence); the threshold sensitivity sweep shows
contraction losing at all nine grid cells — stricter thresholds make it worse, not better. The depth
split is the cleanest single table of why the hypothesis died: both instruction and even naive append
keep ZERO stale second-order inferences; the contraction operator is the only arm that contaminates the
second-order layer at all (7.8%). The published instructed-disregard-fails premise did not reproduce in
this regime.

**A commissioned hostile audit bounds the claim.** The corpus is arithmetically flawless (91/91
recomputed figures), contamination-free of viral puzzles, and realistic — and shallow: 1–2 reasoning
operations per task, a naive baseline flooring near zero on two of three families, persist items largely
source echoes. The verdict is therefore scoped to shallow document-revision tasks; it says nothing about
long contexts, stacked corrections, or deep dependency chains.

**The refutation derives E8.** Every remaining operator experiment silently assumes instructed revision
fails somewhere; in the E5 regime it did not. E8 (instruction breakpoint, decision 0008) is registered:
a dose-response study on the instruction baseline alone, no operators, with Phase 0 — the axis-selection
research itself — as a gating sub-registration frozen before any probe. Outcome (a) gives the remaining
operators their terrain; outcome (b) concludes the revision line with a negative of record.

**Next session starts here:** publish the results record and the E8 registration; then either E8
Phase 0 (the axis-selection study) or the pre-registered cross-vendor replication of E5.
