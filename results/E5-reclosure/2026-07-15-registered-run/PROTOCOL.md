# E5 — Run protocol (DRAFT for freeze)

STATUS: FINAL, as run. This is the protocol text that was
frozen at S4 and cited by the OSF pre-registration. All values are transcribed from the
on-disk frozen config and decisions 0001/0002/0006/0007 as repaired; where a value is a
placeholder awaiting pilot completion it is marked `[[PILOT: …]]`.

Frozen config hash (SHA-256 of the sorted-key config JSON, `closure_harness.config.config_hash`):
`6dbe47a8e843ec1540f64ed6ddd8339c17b95688db363e31605502e374a8b9f0`
Harness commit at freeze: `af7c92d59a27e8a4b8ac689010ea08412d1bfa22` (to be re-read at the
moment of registration — if any further repair lands, both the hash and this line update
together).

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

Sampler rationale (disclose verbatim): decision 0001's original values (temperature 0.7,
top_p 0.95) predate checking the pinned tier's API surface, which rejects explicit sampling
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
  BEFORE the structured-output instruction lines. The instruction text is the composite winner
  selected in `ARM-B-CANDIDATES.md` (frozen at S4). It is authored once in this protocol, not
  per task, and applied identically to all 60 tasks.
- ARM-B INSTRUCTION (frozen text, candidate C1 selected 2026-07-14, appended after the question,
  before the structured-output instruction lines):

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
a C-win over a weak B is worthless. The instruction is red-teamed in `ARM-B-CANDIDATES.md`; it
demands explicit retraction of A, revision of every dependent conclusion, and a self-check —
the most any single prompt instruction can do. It remains a single-prompt instruction (no
multi-turn scaffold, no external tool) because Arm B represents the ceiling of "the best you can
do by asking."

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
`test_import_hygiene.py` — `outcomes.py` must not import `detector.py`).

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
  α, around the observed B-arm baseline contamination rate. `[[PILOT: baseline rate feeds the
  MDE number; report the numeric MDE once the B-arm rate is known from the run — the FORMULA and
  N are frozen, the numeric value is a run output, not a frozen choice.]]`
- **Effect sizes:** reported per task family (F1/F2/F3) and per contamination depth (direct vs
  second-order), per E5 README verdict requirement.

### 6a. Unit of analysis — PINNED
The z-test unit is **pooled must-change items** across the 60 tasks: successes = must-change
items still asserted, trials = total must-change items in the arm. This is what `stats.py`
computes (a proportion over pooled items) and what the MDE formula assumes.

DISCLOSED CAVEAT (must appear in the registration and the write-up): must-change items are
clustered within tasks (a task contributes ≥2 items that are not independent). The pooled
two-proportion z-test treats them as independent trials, which understates variance and can
inflate significance. This is stated as a known limitation of the pre-registered primary test.
The pre-registered secondary robustness read (exploratory, zero confirmatory weight) is the
task-level analysis: contamination as a per-task rate, compared paired across arms, which
respects the clustering. If the two disagree, the disagreement is reported, not resolved in
favor of the confirmatory test. (Rationale for pinning pooled-with-caveat rather than switching
the primary to task-level: `stats.py` as frozen computes the pooled proportion test; changing
the primary unit now would be a post-freeze analysis change. The honest move is to register the
frozen test as primary WITH its clustering caveat, and register the task-level read as the
pre-specified robustness companion.)

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
  crash the run. `[[PILOT/RUN: report the count of error draws per arm; a task with no usable
  draw in an arm is reported, not silently dropped.]]`
- **Model-identity mismatch HALTS the run** (not an exclusion): a provider-returned model id
  that differs from the pin raises `ModelIdentityError` and stops everything.

Exclusions are symmetric: the SAME task set (the 60 that survived the pilot) is run through all
three arms. No task is excluded from one arm and kept in another.

---

## 9. Pilot disclosure (honest, per 0006)

The A-dependency pilot is the pre-registered exclusion filter, run in S3 BEFORE freeze. It does
not void the freeze: all outcome-relevant choices (arms, detector, scoring, thresholds,
statistics) predate S3 and are in the frozen config; the pilot only selects which tasks have a
measurable A-dependency. Its procedure is disclosed here in full so a reviewer sees exactly what
was done.

**Pilot procedure summary:** for each of ~150 candidate tasks, generate the model-under-test's
output in two evidence states — `withA` (all sources verbatim) and `withNotA` (the A-carrying
source's text REPLACED by `not_A_evidence.text`; ordering and count preserved so source indices
stay stable) — 3 draws per state (`N_PILOT_DRAWS = 3`, a pilot-only robustness knob OUTSIDE the
frozen config). Each output is scored with the frozen NLI scorer against the task's annotations.
A candidate PASSES iff at least one `must_change` item is asserted under A (majority of 3 withA
draws) and not asserted under ¬A (asserted in ≤1 of 3 withNotA draws) — `|flipped| ≥ 1`.
`persist_stability < 1.0` flags a candidate for human QA (suspected A-leak in a `must_persist`
item) even when it passes on the must-change side.

The substitution state (¬A in A's place) is a deliberate refinement of E5-TURNKEY line 105's
looser "with A removed": bare removal invites degenerate "insufficient information" outputs that
non-assert everything and pass the flip test trivially. Substitution puts the reasoner in the
real ¬A world, the state against which "must change" is defined. The pilot reuses
`generate.generate_row` (model-identity guard fires) and `outcomes._still_asserts` (no new
scoring logic).

**Pilot outcome (filled from `pilot-verdicts.jsonl` / `pilot-log.jsonl` at S3e, 2026-07-15):**
- Candidates run: **150** (draft target ~150; 50 per family, 900 generations = 150 × 2 states × 3 draws).
- PASS: **136**  · EXCLUDE: **14**.  Overall PASS rate **90.7%**.
- Exclusion reason histogram: `{"no must_change item flipped": 14}` (no other reason fired;
  no "insufficient draws" exclusion — every task had ≥2 clean draws per state, see §9a).
- Excluded task ids (14, retained in the log, never deleted): F1-0002, F1-0006, F1-0009, F1-0015,
  F1-0019, F1-0024, F1-0028, F1-0040, F2-0020, F2-0033, F2-0041, F2-0044, F2-0046, F2-0048.
- Per-family PASS rate: F1 **42/50 (84%)**, F2 **44/50 (88%)**, F3 **50/50 (100%)**.
- `flagged_for_qa` (persist_stability < 1.0): **23** — F1 2, F2 3, **F3 18** (persist_stability
  histogram: 0.5 ×16, 0.0 ×7). These flag a *suspected* A-leak in a `must_persist` item; the
  flag-aware selection amendment (§9c) EXCLUDES all 23 from the final-60 pool.
- Final selected 60: family-balanced **20/20/20** achieved, no family shortfall. Selection
  determinism and difficulty spread are recorded in §9d.

The pilot logs (`pilot-log.jsonl`, `pilot-verdicts.jsonl`) and the candidate pool stay in
private notes; the committed corpus carries only the 60 task records with model-identity fields
stripped. The pre-registration cites the exclusion COUNTS and the config hash.

### 9a. Two provider-overload draws (529), disclosed

Two of the 900 pilot generations hit an Anthropic 529 overload error and returned no output:
**F3-0044 withNotA draw 2** and **F3-0045 withA draw 0**. Each affected (task, state) pair therefore
had **2 clean draws instead of 3**; the majority pass rule (§5b: asserted under A if in ≥2 of the
withA draws; not-asserted under ¬A if in ≤1 of the withNotA draws) was evaluated on the 2 clean
draws for those pairs. Both tasks PASS with `n_flipped = 2/2` and `persist_stability = 1.0`; neither
is flagged. The 529s are unbilled (no generation produced) and are logged with an `error` field per
§8's generation-error handling, not silently dropped. This is the only instrument-noise event of the
pilot beyond the modeled sampler stochasticity.

### 9b. Instrument-noise characterization and the false-stale pruning rule

The pilot's 3-draw majority (§5b) is a sampler-robustness measure, but the majority verdict can still
carry residual noise: a `must_change` item can be a *genuine* A-dependency for the task (so the task
PASSes on some other item) yet, under the stochastic sampler, still be **asserted in the ¬A world in
the majority of withNotA draws** — i.e. the model failed to retract it not because it is A-independent
but because that particular item is a noisy scorer target. Such an item is **FALSE-STALE**: keeping
it in the scored `must_change` set would let all three arms be scored against a target the model does
not reliably flip even in the clean ¬A world, corrupting the contamination measure with an item that
carries no real A-signal.

**Pruning rule (verbatim, applied at S3e, disclosed here as a pre-registration corpus-construction
step):** for every PASS task, a `must_change` item is pruned FROM SCORING (not from the task record —
the sources and annotations are unchanged; the item is excluded from the scored must_change set) iff
it is asserted (per the logged `asserted_must_change` arrays) in **≥ 2 of that task's clean withNotA
draws**. The rule is applied identically to all PASS tasks before selection and is symmetric across
arms (the arms are scored against the pruned must_change set for every task). A sanity invariant is
enforced and held: **every PASS task retains ≥ 1 unpruned `must_change` item** (guaranteed by the
pass rule — a PASS requires ≥1 item that flips, i.e. asserted in ≤1 withNotA draw, which is never
pruned; verified, 0 violations).

**Pruning register (full count):** **26** must_change items pruned across **26** PASS tasks (each
affected task loses exactly one of its two items). Family split: **F1 = 12, F2 = 14, F3 = 0** — no F3
item is false-stale; F3's residual noise manifested entirely as persist-wobble (the §9 flags), not as
must_change false-staleness. Assert-count breakdown: 17 items asserted in all 3 withNotA draws, 9 in
exactly 2. False-stale floor: **26/272 = 9.6%** at the must_change-item level (**26/136 = 19.1%** at
the task level). The full register (task_id, item_index, text, withNotA_assert_count) is preserved in
private notes at `E5-CORPUS/pruned-items.json`. Pruned task ids: F1-0003, F1-0005, F1-0016, F1-0018,
F1-0025, F1-0027, F1-0034, F1-0037, F1-0038, F1-0044, F1-0045, F1-0049; F2-0005, F2-0006, F2-0009,
F2-0014, F2-0015, F2-0021, F2-0022, F2-0023, F2-0035, F2-0037, F2-0038, F2-0043, F2-0045, F2-0050.

### 9c. Flag-aware selection amendment (persist-wobble exclusion)

The pilot flagged 23 tasks with `persist_stability < 1.0` (a `must_persist` item changed assertion
state between the A and ¬A draws — a **suspected A-leak** in a persist item, §5b diagnostic). An
A-dependent persist item is the single most damaging construction error (§2a): it makes the
**completeness co-primary punish correct revision**. Rather than route the 23 to per-task human QA
adjudication, S3e adopts the conservative **flag-aware selection amendment**: the final-60 selection
pool is restricted to PASS tasks with `flagged_for_qa = false`. All 23 flagged tasks (F1 2, F2 3, F3
18) are excluded from selection.

Rationale (disclosed): the co-primary completeness guard is load-bearing for the verdict; admitting a
task whose persist item wobbles risks corrupting completeness in a way that could either mask or
manufacture a "contraction wins by deletion" outcome. Excluding on the flag is the choice that
protects the co-primary. This is a pre-registration decision made at S3e **before any arm ran**; it
does not touch the frozen scoring config, the arms, or the thresholds — it only restricts which tasks
enter the 60. The excluded flagged tasks are retained in the pilot logs and the candidate pool for
audit.

### 9d. Final-60 selection — determinism, the F3 spread relaxation, and achieved spread

**Selection procedure (deterministic, no hidden judgment).** Pool = PASS tasks with
`flagged_for_qa = false` (unflagged pool sizes: F1 40, F2 41, F3 32). Within each family, exactly 20
are selected, task_id ascending throughout:

- **F1, F2 (spec §6 unchanged):** reserve the 6 lowest-task_id tasks with `source_count ≤ 3` and the
  6 lowest-task_id tasks with `source_count ≥ 5` (satisfying the per-family spread quotas), then fill
  the remaining slots by task_id ascending from the family's unflagged pool.
- **F3 (spread relaxed, adjudicated at S3e):** the §6 quota "≥ 6 tasks with `source_count ≤ 3`" is
  **unsatisfiable from F3's unflagged pool** — see the observed finding in §10.6. The quota is relaxed
  to the feasible maximum: select the 1 available `source_count ≤ 3` task (F3-0028), plus all 4
  `source_count = 4` tasks and all 3 `source_count = 6` tasks (to keep the spread as non-degenerate as
  the pool permits), and fill the remaining 12 slots with `source_count = 5` tasks by task_id
  ascending. Spec §10 pre-authorizes this: the difficulty-spread thresholds "carry no verdict weight
  and can be adjusted at S3e if survivorship forces it — the requirement that matters is 'not
  clustered at one difficulty.'"

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

The 60 selected records (with provenance + `selected: true` + `pruned_item_indices`) and the 76
unselected PASS survivors (`selected: false`, audit trail) are in private notes at
`E5-CORPUS/final-60.jsonl`. The committed corpus (`~/repos/closure/.../corpus/tasks.jsonl`) carries
only the 60, task_id ascending, stripped per §7 (no provenance, no selected flag, no model ids).

---

## 10. Disclosed limitations

These are stated as pre-registered limitations, not hidden. Each has its mitigation named.

1. **Same-vendor drafting confound.** Corpus tasks are drafted by Anthropic Opus models; the
   model under test is an Anthropic Sonnet model — same vendor, different tier. This is a
   residual confound the primary run cannot eliminate: a model may score its own vendor's text
   more favorably. Mitigation is the pre-registered cross-family replication arm (S5b),
   `gpt-5.4-mini-2026-03-17` generating over the SAME Opus-drafted corpus. If the C≫B effect
   reproduces on a different vendor's model, the "drafter and testee share a vendor" objection is
   answered empirically. The primary run is NOT claimed vendor-clean.

2. **Short-context scope boundary.** The tasks are short structured-answer items (sources capped
   at ≤350 tokens each; small source counts). The published contamination-under-instruction
   results the premise rests on grow with context size; this run tests the small-context regime
   where the capability delta between tiers does not bite. The verdict claim is scoped to this
   regime — it does not license a claim about long-context or many-source revision.

3. **All-sources-cited detector edge.** The Arm-C contamination detector removes a claim's own
   `source_ids` and re-scores; a claim whose `source_ids` name EVERY source cannot be
   distinguished from a claim genuinely grounded in all sources (removing all sources leaves no
   premise, grounding → 0, so `grounding_without` is 0 and the claim is never flagged
   contaminated). This is a known blind spot of the detector: a claim that cites all sources is
   never contracted even if it is parametric. It is a conservative failure (under-contraction,
   not over-contraction) and affects only Arm C's construction, never the annotation-referenced
   outcome. Disclosed as a boundary of the contraction rule, not a scoring bias.

4. **Unit-of-analysis clustering.** See §6a — the pooled z-test treats clustered must-change
   items as independent; the task-level read is the registered robustness companion. Stated as a
   known property of the primary test.

5. **No seed / non-determinism in generation.** The provider API exposes no seed; Arms A and B
   are single stochastic draws per task. Arm C is deterministic given its input. `base_seed +
   draw_index` is logged as provenance only, not a determinism guarantee (0006).

6. **F3 short-context stratum is thin (observed finding + spread relaxation, disclosed).** In the
   pilot, F3's persist-wobble flags (`persist_stability < 1.0`, §9c) were **strongly correlated with
   F3's short-context tasks**: **16 of the 17 F3 tasks drafted with `source_count = 3` were flagged**;
   only F3-0028 (source_count 3) survived unflagged. Because the flag-aware amendment (§9c) excludes
   all flagged tasks, F3's unflagged pool retained only **one** task with `source_count ≤ 3`, making
   the spec §6 per-family quota "≥ 6 tasks with `source_count ≤ 3`" **unsatisfiable for F3 from the
   unflagged pool**. Per spec §10's own pre-authorization — the difficulty-spread thresholds "carry no
   verdict weight and can be adjusted at S3e if survivorship forces it; the requirement that matters
   is 'not clustered at one difficulty'" — the F3 `source_count ≤ 3` quota was **relaxed to the
   feasible maximum (1)**, with all sc=4 and sc=6 unflagged tasks additionally selected to keep F3's
   spread non-degenerate. The resulting F3 source-count spread is {3: 1, 4: 4, 5: 12, 6: 3}. F1 and
   F2 quotas were NOT relaxed (both feasible). **Consequence for the verdict:** F3's short-context
   stratum is thin (a single task at `source_count ≤ 3`), so any F3-specific short-context effect is
   **exploratory only** and carries no confirmatory weight; the depth-stratified report (direct vs
   second-order) is unaffected because it pools must_change items across families and F3 still
   contributes both depths. This relaxation is a pre-registration S3e decision made before any arm
   ran; it does not touch the frozen config, arms, or thresholds.

---

## 11. Registration gate (enforced by the S5 runner, recorded here)

The run entry point refuses to execute on real (non-pilot) data unless: (a) the OSF registration
resolves; (b) its timestamp predates the run AND the harness's first invocation on real data;
and (c) the committed `config_hash()` matches the registered token
(`6dbe47a8e843…`). Arm C is constructed exclusively via `contraction.contract()`. The run
manifest records torch/transformers versions (from `uv.lock`), NLI weight-file checksums,
device, and config hash.

### 9e. Run-time instrument repair (2026-07-15, applied before any outcome was computed)
During Arm-C construction, a recurring model-output defect surfaced: a single derived summary
claim per affected output citing a nonexistent source index (a hallucinated citation for the
model's own inference). The original guard excluded the entire task, which depleted the
second-order family differentially. Repair, applied BEFORE any outcome scoring existed: a claim
whose source_ids contain an invalid index has no valid support and is treated as unsupported —
stripped identically from every arm's output prior to contraction and scoring, with a per-output
sanitation register reported alongside the results. The repair is claim-granular and
arm-symmetric; no task is excluded by this class, and no contamination or completeness number
had been computed anywhere at the time of the repair.
