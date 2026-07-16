# E5 — Run protocol (frozen)

This is the frozen run protocol for E5. Every value here is transcribed from the on-disk frozen
config (`harness/src/closure_harness/config.py`) and decisions 0001/0002/0006/0007 as repaired. It
was committed to this public repository before any registered arm ran; the commit history is the
pre-registration timestamp record (§11).

Frozen config hash (SHA-256 of the sorted-key config JSON, `closure_harness.config.config_hash`):
`6dbe47a8e843ec1540f64ed6ddd8339c17b95688db363e31605502e374a8b9f0`
This value is also committed as `harness/config.sha256`; a pre-commit check fails on drift, and the
run entry point refuses to generate unless the live hash equals it (§11).

---

## 1. Question and hypothesis

When later evidence contradicts an earlier assumption, does programmatically rebuilding the
context without the assumption (an explicit contraction operation) reduce downstream
contamination more than instructing the model to disregard the assumption?

Hypothesis under test: H-RELEASE — "revision is an operation, not a request." The registered
claim is the three-arm isolation: A (naive append) vs B (instructed disregard) vs C
(mechanical contraction), with downstream-conclusion contamination as the primary measured
outcome and completeness as a co-primary guard.

---

## 2. Model pin and provider parameters

All values below are frozen in `closure_harness.config` and enter the freeze hash unless
explicitly marked as a non-frozen plumbing constant.

| Parameter | Value | Frozen? | Source |
|---|---|---|---|
| Generation model pin | `claude-sonnet-5` | yes (`generation.model_pin`) | 0001 working default |
| Sampling | `provider-default` (stochastic, non-zero; no explicit temperature/top_p sent) | yes (`sampler.sampling`) | 0001 repair |
| Thinking / reasoning mode | `disabled` (`thinking={"type":"disabled"}`) | yes (`sampler.thinking`) | 0001 repair |
| Structured output | JSON Schema constrained decoding, `additionalProperties:false`, explicit `required` | yes (schema shape is 0001) | `providers.py` `_OUTPUT_JSON_SCHEMA` |
| max_tokens | 4096 | no (plumbing constant in `providers.py`) | bounds a runaway generation only |
| Seed | `base_seed + draw_index`, logged as provenance only | n/a — API exposes no seed | 0001 / 0006 |

Sampler rationale (disclosed verbatim): decision 0001's original values (temperature 0.7,
top_p 0.95) predate checking the pinned model's API surface, which rejects explicit sampling
parameters. The repair — provider-default sampling + thinking disabled — was made before any
generation call (before the S3 pilot), so no data predates it; it is recorded in the frozen
config and therefore in the freeze hash. Provider-default sampling is stochastic and non-zero,
which satisfies 0001's non-degenerate-dispersion requirement.

### 2a. Structured-output schema (0001, verbatim)

The model returns exactly:

```json
{
  "claims": [{"id": <int>, "text": "<str>", "source_ids": [<int>, ...]}, ...],
  "conclusion": "<str>"
}
```

One claim = one atomic proposition. `source_ids` lists the provided document indices a claim
draws on; an empty `source_ids` marks a structurally decorative claim. `conclusion` is a single
sentence answering the question. The provider enforces this via `json_schema` constrained
decoding; the harness re-validates with `schema.parse_output` and halts on a model-identity
mismatch before the output is trusted (`generate.generate_row` → `ModelIdentityError`).

---

## 3. The generation prompt (VERBATIM, frozen)

This is the exact template shown to the model, from `closure_harness.pilot.PROMPT_TEMPLATE`. It
is the same template for the pilot and for all three arms — the arms differ only in the source
block and (Arm B) an appended instruction (§4). `{documents}` is the numbered source block and
`{question}` is the task question. Documents are numbered `0..len-1` so the indices the model
cites in `source_ids` line up with the positional source indices the harness uses everywhere.

```
You are given a set of source documents and a question. Read the documents and answer the question using only the information they contain.

Documents:
{documents}

Question: {question}

Provide your answer as structured output with two fields:
- "claims": a list of atomic factual claims, each an object with "id" (an integer), "text" (the claim as a single sentence), and "source_ids" (a list of the document numbers, as shown above, that the claim draws on; use an empty list if the claim draws on no specific document).
- "conclusion": a single sentence that directly answers the question, following from the claims.
```

`{documents}` renders as `[i] <source text>` joined by newlines, i ascending from 0.

---

## 4. The three arms — exact context construction

Every task supplies: an ordered `sources` list, `assumption_A` (which source carries A + the A
proposition), `not_A_evidence` (the ¬A text + which source it supersedes), a `question`, and
the two annotation sets `must_change` / `must_persist`. The arms consume these as follows.

### Arm A — naive append
- Source block = the task's `sources` verbatim (A present), then the `not_A_evidence.text`
  appended as an additional final numbered document.
- Prompt = §3 template with that block and the task `question`. No revision framing.
- One generation. Scored output = the returned `Output`.

### Arm B — instructed disregard
- Same source block as Arm A (A-present sources + ¬A appended as a final document).
- Plus the strongest single-prompt retract-and-revise instruction, appended after the question,
  BEFORE the structured-output instruction lines. The instruction is authored once here, not per
  task, and applied identically to all 60 tasks.
- ARM-B INSTRUCTION (frozen text, VERBATIM — also committed at `ARM-B-INSTRUCTION.md`):

  > A later document in the list above corrects an earlier statement. Before you answer, do all of
  > the following: (1) Identify the specific earlier statement the final document overrides, and
  > treat it as false from now on. (2) Find every claim and every intermediate conclusion that
  > relied on that now-false statement, and recompute each using the corrected information instead.
  > (3) Do not carry forward any figure, date, ranking, or verdict that was derived from the
  > superseded statement — re-derive it from the correction or drop it. (4) Before finalizing,
  > re-read your own claims and conclusion and confirm none still depends on the statement you
  > retracted. Answer as if the corrected information had been true all along.
- One generation. Scored output = the returned `Output`.

Rationale that Arm B is the strong instruction, not a weak one (E4 fair-instruction principle):
a C-win over a weak B is worthless. The instruction was selected after an adversarial candidate
review as the strongest single-prompt retract-and-revise instruction; it demands explicit
retraction of A, revision of every dependent conclusion, and a self-check — the most any single
prompt instruction can do. It remains a single-prompt instruction (no multi-turn scaffold, no
external tool) because Arm B represents the ceiling of "the best you can do by asking."

### Arm C — mechanical contraction (deterministic, zero generation)
- Input: the model's Arm-A-style output on the same task (the structured `Output` produced from
  the A-present-plus-¬A context). C does NOT generate.
- `contraction.contract()` iteratively removes, to a fixpoint, claims that are either decorative
  (`source_ids == []`) or contaminated per the 0007 detector — id-ascending, single pass per
  iteration, no re-scoring within a pass.
- Contamination detector (drives contraction ONLY, never scores an outcome): a claim is
  contaminated iff its grounding stays `>= grounding_floor` (0.70) with all its `source_ids`
  removed AND `grounding_drop < drop_ceiling` (0.10) — reproduced from parametric memory, not
  the provided sources. Grounding here is the deterministic single-evaluation NLI scalar (NOT
  0002's mean-over-K form — regenerating inside Arm C would void bit-for-bit reproducibility).
- The contracted conclusion is DERIVED from the surviving claims by a committed deterministic
  template — never re-generated by the model (0007, load-bearing). No code path accepts a
  per-task hand-authored contraction.
- Reproducibility clause: the entire Arm-C set is regenerable bit-for-bit from (task, committed
  algorithm, frozen config). An independent party regenerating a different result voids the
  experiment. Registered runs pin `device="cpu"` because MPS/CUDA float paths are not
  bit-identical.
- Construction seam: Arm C is built EXCLUSIVELY via `contraction.contract()`; no direct
  `is_contaminated` calls in the run path. The sensitivity sweep is a separate read-only report
  over stored scores (§7).

---

## 5. Outcome scoring (repaired 0007, identical across arms)

Two annotation sets are authored per task at construction time, independent of any model output:
`must_change` (conclusions that must change under ¬A — A-dependent) and `must_persist`
(conclusions that must survive — A-independent). Both are standalone declarative sentences.

An arm output "still asserts" an annotated conclusion iff the bidirectional NLI scalar of that
conclusion against the arm's asserted text is `>= assert_threshold` (0.70). The asserted text is
the output's `conclusion` plus every surviving claim's `text`; the score is the max over that
premise set (matching 0002 multi-source aggregation).

- Primary outcome — **contamination** = fraction of `must_change` conclusions the output still
  asserts. Lower is better.
- Co-primary outcome — **completeness** = fraction of `must_persist` conclusions the output
  still asserts. Higher is better.

Scoring is by the same `outcomes.score()` for every arm, referenced only to the annotations,
never to the detector that built Arm C (0007 anti-circularity; enforced by
`test_import_hygiene.py` — `outcomes.py` must not import `detector.py`, and `run_e5.py` builds
Arm C only through `contraction.contract()`, never through a direct detector call).

Deletion trap (why completeness is co-primary): an output that deleted everything asserts only
an empty-support sentinel conclusion, so it fails to entail any `must_change` (contamination 0)
AND any `must_persist` (completeness 0) — the deletion trap is caught by scoring both sides
against the same asserted set. `outcomes.score()` raises on an empty `must_change` or
`must_persist` set: such a task is a construction error, excluded upstream.

### 5a. NLI scorer (frozen)
- Checkpoint `MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli`, revision
  `b3546ea6b0346eb6f8d5d68b13c7dc6d0376b3d7`. CPU-lighter fallback
  `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` (revision `6f5cf0a2…`) pre-registered and
  selectable; `use_fallback=False` for the registered run.
- Per-pair scalar `(P(entail) − P(contradict) + 1)/2` ∈ [0,1]; bidirectional = both
  premise/hypothesis orderings averaged; multi-source = max over premises.
- `device="cpu"`, `max_length=512`, deterministic algorithms on. Truncation FAILS CLOSED (raises
  rather than silently clipping) — the corpus caps sources at ≤350 tokens under this exact
  tokenizer so pairs fit.

---

## 6. Statistics (0007)

- **Primary test:** pairwise two-proportion z-test on contamination, two-sided, pooled,
  Bonferroni-corrected for 3 comparisons (A vs B, B vs C, A vs C), α = 0.05. Judged against the
  corrected α. "C beats B" requires this test to clear significance AND the completeness
  non-inferiority check below to hold.
- **Completeness non-inferiority:** paired at the task level, absolute margin δ = 0.10. C is
  non-inferior iff `mean(completeness_C) >= mean(completeness_B) − 0.10`. Boundary (exactly
  B − δ) counts as non-inferior.
- **MDE:** minimum detectable effect reported for N = 60 at power 0.80 and Bonferroni-corrected
  α, around the observed B-arm baseline contamination rate. The FORMULA and N are frozen; the
  numeric MDE is a run output computed from the observed B-arm rate, not a frozen choice.
- **Effect sizes:** reported per task family (F1/F2/F3) and per contamination depth (direct vs
  second-order), per the E5 README verdict requirement.

### 6a. Unit of analysis — PINNED
The z-test unit is **pooled must-change items** across the 60 tasks: successes = must-change
items still asserted, trials = total must-change items in the arm. This is what `stats.py`
computes (a proportion over pooled items) and what the MDE formula assumes.

DISCLOSED CAVEAT (appears in the write-up): must-change items are clustered within tasks (a task
contributes ≥2 items that are not independent). The pooled two-proportion z-test treats them as
independent trials, which understates variance and can inflate significance. This is a known
limitation of the pre-registered primary test. The pre-registered secondary robustness read
(exploratory, zero confirmatory weight) is the task-level analysis: contamination as a per-task
rate, compared paired across arms, which respects the clustering. If the two disagree, the
disagreement is reported, not resolved in favor of the confirmatory test. Rationale for pinning
pooled-with-caveat rather than switching the primary to task-level: `stats.py` as frozen computes
the pooled proportion test; changing the primary unit now would be a post-freeze analysis change.
The honest move is to register the frozen test as primary WITH its clustering caveat, and register
the task-level read as the pre-specified robustness companion.

---

## 7. Sensitivity sweep (read-only, exploratory)

The detector thresholds are swept over the pre-registered grid `grounding_floor ∈ {0.65, 0.70,
0.75} × drop_ceiling ∈ {0.05, 0.10, 0.15}` (frozen point = the centre, 0.70/0.10). The sweep is
a SEPARATE read-only report over stored scores; it does not re-run generation and does not enter
the confirmatory verdict. It exists to show the C-vs-B result is not an artifact of the exact
threshold. Threshold comparisons quantize to 9 decimals before comparing (frozen
`quantize_decimals`) so a float64 exactly-at-ceiling drop does not flip the registered boundary.

---

## 8. Exclusion rules (pre-registered, applied identically to all arms)

- **A-dependency pilot exclusion (primary exclusion rule):** a candidate is EXCLUDED before any
  arm runs if no `must_change` item flips between the A-present and ¬A-substituted states in the
  pilot (§9). Excluded tasks are counted and reported; they never enter the 60.
- **Scoring-degenerate exclusion:** a task with an empty `must_change` or `must_persist` set is a
  construction error and cannot be scored (`outcomes.score()` raises); excluded at corpus
  construction, not at run time.
- **Generation-error handling within an arm:** a draw that hits a provider error, refusal,
  max-token truncation, or schema-parse failure is logged with an `error` field and does not
  crash the run. The count of error draws per arm is reported; a task with no usable draw in an
  arm is reported, not silently dropped.
- **Model-identity mismatch HALTS the run** (not an exclusion): a provider-returned model id
  that differs from the pin raises `ModelIdentityError` and stops everything.

Exclusions are symmetric: the SAME task set (the 60 that survived the pilot) is run through all
three arms. No task is excluded from one arm and kept in another.

---

## 9. Pilot disclosure (honest, per 0006)

The A-dependency pilot is the pre-registered exclusion filter, run before freeze. It does not void
the freeze: all outcome-relevant choices (arms, detector, scoring, thresholds, statistics) predate
the pilot and are in the frozen config; the pilot only selects which tasks have a measurable
A-dependency. Its procedure is disclosed here in full so a reviewer sees exactly what was done.

**Pilot procedure summary:** for each of 150 candidate tasks, generate the model-under-test's
output in two evidence states — `withA` (all sources verbatim) and `withNotA` (the A-carrying
source's text REPLACED by `not_A_evidence.text`; ordering and count preserved so source indices
stay stable) — 3 draws per state (`N_PILOT_DRAWS = 3`, a pilot-only robustness knob OUTSIDE the
frozen config). Each output is scored with the frozen NLI scorer against the task's annotations.
A candidate PASSES iff at least one `must_change` item is asserted under A (majority of 3 withA
draws) and not asserted under ¬A (asserted in ≤1 of 3 withNotA draws) — `|flipped| ≥ 1`.
`persist_stability < 1.0` flags a candidate for human QA (suspected A-leak in a `must_persist`
item) even when it passes on the must-change side.

The substitution state (¬A in A's place) is a deliberate refinement of a looser "with A removed"
design: bare removal invites degenerate "insufficient information" outputs that non-assert
everything and pass the flip test trivially. Substitution puts the reasoner in the real ¬A world,
the state against which "must change" is defined. The pilot reuses `generate.generate_row`
(model-identity guard fires) and `outcomes._still_asserts` (no new scoring logic).

**Pilot outcome:**
- Candidates run: **150** (50 per family; 900 generations = 150 × 2 states × 3 draws).
- PASS: **136** · EXCLUDE: **14**. Overall PASS rate **90.7%**.
- Exclusion reason histogram: `{"no must_change item flipped": 14}` (no other reason fired).
- Per-family PASS rate: F1 **42/50 (84%)**, F2 **44/50 (88%)**, F3 **50/50 (100%)**.
- `flagged_for_qa` (persist_stability < 1.0): **23** — F1 2, F2 3, **F3 18**. These flag a
  *suspected* A-leak in a `must_persist` item; the flag-aware selection amendment (§9c) EXCLUDES
  all 23 from the final-60 pool.
- Final selected 60: family-balanced **20/20/20**, no family shortfall (§9d).

The pre-registration cites the exclusion COUNTS and the config hash. The committed corpus
(`corpus/tasks.jsonl`) carries only the 60 task records with model-identity fields stripped.

### 9a. Two provider-overload draws (529), disclosed

Two of the 900 pilot generations hit a provider 529 overload error and returned no output:
**F3-0044 withNotA draw 2** and **F3-0045 withA draw 0**. Each affected (task, state) pair therefore
had **2 clean draws instead of 3**; the majority pass rule (asserted under A if in ≥2 of the withA
draws; not-asserted under ¬A if in ≤1 of the withNotA draws) was evaluated on the 2 clean draws for
those pairs. Both tasks PASS with `n_flipped = 2/2` and `persist_stability = 1.0`; neither is
flagged. The 529s produced no billed generation and are logged with an `error` field per §8's
generation-error handling, not silently dropped. This is the only instrument-noise event of the
pilot beyond the modeled sampler stochasticity.

### 9b. Instrument-noise characterization and the false-stale pruning rule

The pilot's 3-draw majority is a sampler-robustness measure, but the majority verdict can still
carry residual noise: a `must_change` item can be a *genuine* A-dependency for the task (so the task
PASSes on some other item) yet, under the stochastic sampler, still be **asserted in the ¬A world in
the majority of withNotA draws** — i.e. the model failed to retract it not because it is A-independent
but because that particular item is a noisy scorer target. Such an item is **FALSE-STALE**: keeping
it in the scored `must_change` set would let all three arms be scored against a target the model does
not reliably flip even in the clean ¬A world, corrupting the contamination measure with an item that
carries no real A-signal.

**Pruning rule (verbatim, applied before freeze as a pre-registered corpus-construction step):** for
every PASS task, a `must_change` item is pruned FROM SCORING (not from the task record — the sources
and annotations are unchanged; the item is excluded from the scored must_change set) iff it is
asserted in **≥ 2 of that task's clean withNotA draws**. The rule is applied identically to all PASS
tasks before selection and is symmetric across arms (the arms are scored against the pruned
must_change set for every task). A sanity invariant is enforced and held: **every PASS task retains
≥ 1 unpruned `must_change` item** (guaranteed by the pass rule — a PASS requires ≥1 item that flips,
i.e. asserted in ≤1 withNotA draw, which is never pruned; verified, 0 violations).

**Pruning register (full count):** **26** must_change items pruned across **26** PASS tasks (each
affected task loses exactly one of its two items). Family split: **F1 = 12, F2 = 14, F3 = 0** — no F3
item is false-stale; F3's residual noise manifested entirely as persist-wobble (the §9 flags), not as
must_change false-staleness. Assert-count breakdown: 17 items asserted in all 3 withNotA draws, 9 in
exactly 2. False-stale floor: **26/272 = 9.6%** at the must_change-item level (**26/136 = 19.1%** at
the task level). The full register is reproduced in Appendix A; the runner
(`closure_harness.run_e5`) applies it by `(task_id, item_index)`, logs the register's SHA-256, and
excludes the listed items from scoring for every arm. Of the 26 register entries, **13** fall on
tasks selected into the final 60; the rest are on unselected PASS tasks and are harmless no-ops.

### 9c. Flag-aware selection amendment (persist-wobble exclusion)

The pilot flagged 23 tasks with `persist_stability < 1.0` (a `must_persist` item changed assertion
state between the A and ¬A draws — a **suspected A-leak** in a persist item). An A-dependent persist
item is the single most damaging construction error: it makes the **completeness co-primary punish
correct revision**. Rather than route the 23 to per-task human QA adjudication, selection adopts the
conservative **flag-aware selection amendment**: the final-60 selection pool is restricted to PASS
tasks with `flagged_for_qa = false`. All 23 flagged tasks (F1 2, F2 3, F3 18) are excluded from
selection.

Rationale (disclosed): the co-primary completeness guard is load-bearing for the verdict; admitting a
task whose persist item wobbles risks corrupting completeness in a way that could either mask or
manufacture a "contraction wins by deletion" outcome. Excluding on the flag is the choice that
protects the co-primary. This is a pre-registration decision made **before any arm ran**; it does not
touch the frozen scoring config, the arms, or the thresholds — it only restricts which tasks enter
the 60. The excluded flagged tasks are retained in the pilot logs for audit.

### 9d. Final-60 selection — determinism, the F3 spread relaxation, and achieved spread

**Selection procedure (deterministic, no hidden judgment).** Pool = PASS tasks with
`flagged_for_qa = false` (unflagged pool sizes: F1 40, F2 41, F3 32). Within each family, exactly 20
are selected, task_id ascending throughout:

- **F1, F2 (spec unchanged):** reserve the 6 lowest-task_id tasks with `source_count ≤ 3` and the 6
  lowest-task_id tasks with `source_count ≥ 5` (satisfying the per-family spread quotas), then fill
  the remaining slots by task_id ascending from the family's unflagged pool.
- **F3 (spread relaxed):** the quota "≥ 6 tasks with `source_count ≤ 3`" is **unsatisfiable from F3's
  unflagged pool** — see §10.6. The quota is relaxed to the feasible maximum: select the 1 available
  `source_count ≤ 3` task (F3-0028), plus all 4 `source_count = 4` tasks and all 3 `source_count = 6`
  tasks (to keep the spread as non-degenerate as the pool permits), and fill the remaining 12 slots
  with `source_count = 5` tasks by task_id ascending. The corpus spec pre-authorizes this: the
  difficulty-spread thresholds "carry no verdict weight and can be adjusted if survivorship forces
  it — the requirement that matters is 'not clustered at one difficulty.'"

**Achieved spread (source_count within each family's 20):**
- F1: {2: 2, 3: 6, 4: 1, 5: 9, 6: 2} — sc ≤ 3: 8 (≥6 ✓), sc ≥ 5: 11 (≥6 ✓).
- F2: {3: 10, 4: 3, 5: 7} — sc ≤ 3: 10 (≥6 ✓), sc ≥ 5: 7 (≥6 ✓).
- F3: {3: 1, 4: 4, 5: 12, 6: 3} — sc ≤ 3: 1 (relaxed max), sc ≥ 5: 15. Not clustered at one
  difficulty; F3's short-context stratum is thin (see §10.6).

**Depth spread (pooled across families, counted on RETAINED — post-prune — must_change items of the
60):** 56 `direct` + 51 `second_order` items — both ≥ 20 (✓), powering the depth-stratified report.

**Final 60 (task_id ascending per family):**
- F1: F1-0003, F1-0004, F1-0005, F1-0007, F1-0008, F1-0010, F1-0011, F1-0012, F1-0013, F1-0014,
  F1-0016, F1-0017, F1-0018, F1-0020, F1-0021, F1-0022, F1-0023, F1-0025, F1-0026, F1-0029.
- F2: F2-0002, F2-0003, F2-0004, F2-0005, F2-0006, F2-0009, F2-0010, F2-0011, F2-0012, F2-0013,
  F2-0014, F2-0015, F2-0016, F2-0017, F2-0018, F2-0019, F2-0021, F2-0022, F2-0023, F2-0024.
- F3: F3-0011, F3-0012, F3-0013, F3-0014, F3-0015, F3-0016, F3-0017, F3-0018, F3-0019, F3-0020,
  F3-0023, F3-0024, F3-0025, F3-0027, F3-0028, F3-0032, F3-0038, F3-0041, F3-0044, F3-0048.

The committed corpus (`corpus/tasks.jsonl`) carries only these 60, task_id ascending, stripped (no
provenance, no selected flag, no model ids).

---

## 10. Disclosed limitations

These are stated as pre-registered limitations, not hidden. Each has its mitigation named.

1. **Same-vendor drafting confound.** Corpus tasks were drafted by a different model tier than the
   pinned model under test. This is a residual confound the primary run cannot eliminate: a model may
   score its own vendor's text more favorably. Mitigation is the pre-registered cross-family
   replication arm, `gpt-5.4-mini-2026-03-17` generating over the SAME corpus. If the C≫B effect
   reproduces on a different vendor's model, the "drafter and testee share a vendor" objection is
   answered empirically. The primary run is NOT claimed vendor-clean.

2. **Short-context scope boundary.** The tasks are short structured-answer items (sources capped at
   ≤350 tokens each; small source counts). The published contamination-under-instruction results the
   premise rests on grow with context size; this run tests the small-context regime where the
   capability delta between tiers does not bite. The verdict claim is scoped to this regime — it does
   not license a claim about long-context or many-source revision.

3. **All-sources-cited detector edge.** The Arm-C contamination detector removes a claim's own
   `source_ids` and re-scores; a claim whose `source_ids` name EVERY source cannot be distinguished
   from a claim genuinely grounded in all sources (removing all sources leaves no premise, grounding
   → 0, so `grounding_without` is 0 and the claim is never flagged contaminated). This is a known
   blind spot of the detector: a claim that cites all sources is never contracted even if it is
   parametric. It is a conservative failure (under-contraction, not over-contraction) and affects only
   Arm C's construction, never the annotation-referenced outcome. Disclosed as a boundary of the
   contraction rule, not a scoring bias.

4. **Unit-of-analysis clustering.** See §6a — the pooled z-test treats clustered must-change items as
   independent; the task-level read is the registered robustness companion. Stated as a known property
   of the primary test.

5. **No seed / non-determinism in generation.** The provider API exposes no seed; Arms A and B are
   single stochastic draws per task. Arm C is deterministic given its input. `base_seed + draw_index`
   is logged as provenance only, not a determinism guarantee (0006).

6. **F3 short-context stratum is thin (observed finding + spread relaxation, disclosed).** In the
   pilot, F3's persist-wobble flags (`persist_stability < 1.0`) were **strongly correlated with F3's
   short-context tasks**: **16 of the 17 F3 tasks drafted with `source_count = 3` were flagged**; only
   F3-0028 (source_count 3) survived unflagged. Because the flag-aware amendment (§9c) excludes all
   flagged tasks, F3's unflagged pool retained only **one** task with `source_count ≤ 3`, making the
   per-family quota "≥ 6 tasks with `source_count ≤ 3`" **unsatisfiable for F3 from the unflagged
   pool**. Per the corpus spec's own pre-authorization — the difficulty-spread thresholds "carry no
   verdict weight and can be adjusted if survivorship forces it; the requirement that matters is 'not
   clustered at one difficulty'" — the F3 `source_count ≤ 3` quota was **relaxed to the feasible
   maximum (1)**, with all sc=4 and sc=6 unflagged tasks additionally selected to keep F3's spread
   non-degenerate. The resulting F3 source-count spread is {3: 1, 4: 4, 5: 12, 6: 3}. F1 and F2 quotas
   were NOT relaxed (both feasible). **Consequence for the verdict:** F3's short-context stratum is
   thin (a single task at `source_count ≤ 3`), so any F3-specific short-context effect is
   **exploratory only** and carries no confirmatory weight; the depth-stratified report (direct vs
   second-order) is unaffected because it pools must_change items across families and F3 still
   contributes both depths. This relaxation is a pre-registration decision made before any arm ran; it
   does not touch the frozen config, arms, or thresholds.

---

## 11. Pre-registration record (freeze-commit gate, enforced by the run entry point)

E5 uses this public repository's commit history as its pre-registration timestamp record. An
independent third-party registry deposit (e.g. OSF) was considered and omitted by operator decision:
the design, thresholds, prompts, corpus, and analysis plan were frozen and committed here — publicly,
timestamped by the Git host — before any registered arm ran, and that public commit record is the
timestamp evidence.

The frozen artifacts and the commits that froze them:
- **Config / analysis plan** (`harness/src/closure_harness/config.py`, hash
  `6dbe47a8e843…`, also committed as `harness/config.sha256`): the frozen model pin, sampler,
  thresholds, detector rule, outcome definitions, and statistics. Frozen in the harness commits that
  resolved the sampler and hardened the scorer.
- **Corpus** (`corpus/tasks.jsonl`, 60 tasks): frozen in the corpus-freeze commit.
- **Arm-B instruction** (`ARM-B-INSTRUCTION.md`, reproduced §4 verbatim): frozen in the Arm-B-freeze
  commit.
- **This protocol** (`PROTOCOL.md`): committed before the first registered generation.

**The run entry point (`closure_harness.run_e5`) refuses to execute any generation unless ALL hold:**
1. the working tree is clean AND local `HEAD` equals `origin/main` — the freeze commit is PUBLIC
   (pushed), verified after a `git fetch origin`; a run against unpushed local commits is refused;
2. the live `config_hash()` equals the committed `config.sha256` freeze token;
3. `PROTOCOL.md` exists at `HEAD` (this frozen protocol is committed, not a private draft);
4. `corpus/tasks.jsonl` exists at `HEAD`.

There is no flag to skip this gate. The run manifest records the `HEAD` and `origin/main` hashes, the
committed and live config hashes, this protocol file's SHA-256, the corpus SHA-256, the pruning
register SHA-256, the torch/transformers versions, the NLI checkpoint/revision, the device, and the
per-arm error counts — the full provenance needed to reproduce the registered numbers.

---

## Appendix A — Pruning register (must_change items excluded from scoring, §9b)

26 items pruned across 26 PASS tasks (each affected task loses one of its two must_change items). The
runner applies this by `(task_id, item_index)` and logs the register's SHA-256; the items are
excluded from scoring for every arm. `withNotA_assert_count` is the number of the task's clean
withNotA pilot draws in which the item was asserted (≥ 2 triggers the prune).

| task_id | item_index | withNotA_assert_count | must_change item text |
|---|---|---|---|
| F1-0003 | 0 | 2 | The footings will not have cured in time for the Thursday crane loading. |
| F1-0005 | 1 | 3 | The tart shells cannot all be baked before the 09:30 dispatch. |
| F1-0016 | 0 | 3 | All twenty-seven sample tubes cannot be spun in the single booked run. |
| F1-0018 | 1 | 2 | At least one more certified pressure-vessel welder must be added for the welding to proceed. |
| F1-0025 | 1 | 2 | About twenty-four trays have no chilled holding space. |
| F1-0027 | 0 | 3 | Duties will accrue before the buyer's day-27 pickup. |
| F1-0034 | 1 | 3 | At least three more accessible vehicles are needed for the outing. |
| F1-0037 | 1 | 3 | Some cartons must wait for the next flight in two days. |
| F1-0038 | 1 | 3 | At least eight closings cannot be handled by the available notary capacity. |
| F1-0044 | 1 | 2 | The route duration exceeds the drone's per-charge flight time. |
| F1-0045 | 1 | 2 | About 180 plates will remain unwashed at service time. |
| F1-0049 | 0 | 3 | The formwork cannot be struck in time to reuse the panels for the Thursday pour. |
| F2-0005 | 1 | 2 | The annual rent for the Tarn Street unit is $4,000 above Ferro Cafe's ceiling. |
| F2-0006 | 1 | 3 | The Dellmoor plant's monthly electricity cost is $600 under the $9,000 budget. |
| F2-0009 | 1 | 3 | Each active picking lane clears 540 orders over the evening shift. |
| F2-0014 | 0 | 3 | Each bus's peak-hour carrying capacity on the Riverline route is 220 commuters. |
| F2-0015 | 1 | 3 | The Larkfield shoot needs 3 shooting days. |
| F2-0021 | 1 | 3 | The 15 rostered nurses adequately staff the day shift. |
| F2-0022 | 1 | 2 | The Thornbury concert leaves 40 seats empty. |
| F2-0023 | 0 | 3 | The 12-batch run yields 2,880 bottles. |
| F2-0035 | 1 | 3 | The hourly capacity keeps up with the 380-call inbound volume, so no backlog forms. |
| F2-0037 | 1 | 3 | The 90-tonne daily intake is fully cleared in one shift. |
| F2-0038 | 1 | 2 | The Ashworth gala needs 2 more tables than the ballroom can hold. |
| F2-0043 | 1 | 2 | The schedule is over-subscribed against the 50 usable nights. |
| F2-0045 | 1 | 3 | The Ashvale plant treats 6 megaliters above monthly demand. |
| F2-0050 | 1 | 3 | The Oakhurst crew fills 96 bins per day. |
