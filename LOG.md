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
