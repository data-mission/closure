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
