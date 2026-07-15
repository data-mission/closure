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
- This log opened.

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

**Next in this session:** feasibility spike (MLX first, Qwen2.5-7B-Instruct 4-bit; fallbacks
Llama-3.1-8B-Instruct 4-bit, then transformers-on-MPS with hidden-state output) → `FEASIBILITY.md` →
the four e3 decision records (probe design, ground-truth volume protocol, baselines including
verbalized confidence, E3 reproducibility standard) → synthetic validation of the analysis logic on
planted fixtures.
