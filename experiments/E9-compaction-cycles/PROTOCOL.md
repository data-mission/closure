# E9 — Run protocol (exploratory; frozen apparatus, procedure as executed)

This is the run protocol for E9. Unlike E5/E3 it is EXPLORATORY, not pre-registered: there is no
commit-timestamp pre-registration gate. The instrument, corpus grammar, and pins below were frozen in
the apparatus (`../E8-instruction-breakpoint/coldstart-package/x5-e9/`) before the run; this document
records the design as frozen AND the procedure as actually executed, with every execution deviation
disclosed in the Deviations section. It is written to the E5 canvas so E9 reads as a first-class
experiment.

Frozen config hash (SHA-256 of the sorted-key config JSON, `closure_harness.config.config_hash`):
`6dbe47a8e843ec1540f64ed6ddd8339c17b95688db363e31605502e374a8b9f0`
Carried forward bit-for-bit from E5/E8 so E9's frozen-NLI numbers are directly comparable.

---

## 1. Question and hypothesis

Does an iterated summarize-and-continue operator applied to a live reasoning context accumulate revision
contamination across cycles, exceeding a no-compaction instruction baseline over the same turns?

Hypothesis under test: **H-COMPACT** — compaction contamination rises monotonically with cycle count and
crosses a frozen absolute threshold, while the instruction baseline over identical turns stays at its
measured floor. The registered claim is the two-arm matched contrast (N: no compaction vs S: compaction),
with `must_change` contamination as the primary measured outcome and `must_persist` completeness as a
guard.

---

## 2. Model pin and provider parameters

Identical to E5/E8; carried forward so the two experiments are directly comparable.

| Parameter | Value | Source |
|---|---|---|
| Generation model pin | `claude-sonnet-5` | `generation.model_pin` (frozen config) |
| Sampling | provider-default (stochastic, non-zero; no explicit temperature/top_p) | E5 0001 repair |
| Thinking / reasoning mode | `disabled` | E5 `sampler.thinking` |
| Structured output | JSON Schema constrained decoding, `additionalProperties:false` | E5 `_OUTPUT_JSON_SCHEMA` |
| Model-identity halt | per-call, inside `generate_row` (`ModelIdentityError`) | frozen generation path |

The summarizer (Arm S) uses the SAME frozen generation model — the compaction operator is the same model
under a different, pinned instruction, not a separate model.

---

## 3. Pins and startup guards (all fail-loud, all HALT)

`run_e9.startup_guards` refuses to run unless every guard holds:

| Guard | Pinned value |
|---|---|
| Config hash | `6dbe47a8e843ec1540f64ed6ddd8339c17b95688db363e31605502e374a8b9f0` |
| Arm-B instruction file hash | `f9c24295…` (the frozen E5 retract-and-revise instruction, byte-for-byte) |
| Summarizer instruction file hash | `305f7e27a63696dc96046fbe40208224287cd099142d6fec73b01623490426e4` (`driver/SUMMARIZER-INSTRUCTION.md` file-bytes sha256) |
| Generation model identity | `== config.generation.model_pin`, checked per call |
| Corpus manifest | every E9 task passed `build_e9_corpus` grammar + polarity guards; manifest hash `958d77c4` |

Any edit to the summarizer instruction changes its hash — the guard makes a silent prose drift impossible.

---

## 4. The two arms — exact context construction

Every matched task is run at each dose `k ∈ {1, 2, 3}` in BOTH arms. A matched family therefore appears
6 times (3 doses × 2 arms). Per matched task, for each dose `k` (`driver/run_e9.py`):

### Arm N — no-compaction instruction baseline
```
live_docs = base_sources + corrections[:k]        # full transcript retained at every turn
answer    = generate(build_answer_prompt(live_docs, …, ARM_B))     # 1 generation
```
Arm N is the control: the model saw every source and every correction, and was given the frozen
retract-and-revise instruction at the final turn.

### Arm S — summarizer / compaction operator
```
live_docs = base_sources
for t in 1..k:
    summary   = generate(build_summarizer_prompt(live_docs, SUMMARIZER_INSTRUCTION))
    assert_compression_band(summary, live_docs)   # 30–50% band; re-draw if out of band
    live_docs = [summary, corrections[t-1]]        # continue from summary + new correction
answer = generate(build_answer_prompt(live_docs, …, ARM_B))        # k summaries + 1 answer
```
Arm S is the operator: the model revised through `k` compaction boundaries. Generation count per matched
task = Arm N 3 (one answer per dose) + Arm S 9 (2+3+4) = **12 generations per matched task**.

### Matched-turn discipline (the anti-confound)
Arm N and Arm S at the same `k` have the IDENTICAL number of turns, the IDENTICAL corrections in the
IDENTICAL order, and the IDENTICAL final instruction. The ONLY difference is the compaction step. This is
what makes any contamination delta attributable to the operator and not to turn count, correction count,
or context growth.

Every individual model call — answer generations AND summarizer calls — goes through the FROZEN generation
path (`e8-driver/generation_driver.generate_one → closure_harness.generate.generate_row`): model-identity
halt, schema validation, resumable append-only log — reused verbatim, not re-implemented.

---

## 5. Corpus (numeric-only F3 grammar — the artifact dodge)

150 fresh F3-family scenarios (fresh construction, not an A3 transform — the A3→E9 transform yields only
~4 base scenarios and is retained only as a schema-and-guard proof). Binding rules:

1. **All scored strings are numeric-only, single-proposition, F3 grammar:** every `must_change` and
   `must_persist` item is `"The <label> is <value>."` — a bare computed value, NO threshold clause, NO
   verdict word (`fails`/`exceeds`/`within`). This is the grammar the frozen NLI scores correctly (F3: 0
   artifacts across 344 items in the X1 rescore); it dodges the compound-string collision at the corpus
   level, not the scorer level.
2. **Polarity guard (the A1-class guard, fail-closed):** at construction a static check asserts every
   `must_change` value equals the STALE-world computed value (pre-final-correction) and differs from the
   correct-final value; any `must_change` equal to the correct-final value HALTS construction. Enforced in
   `driver/build_e9_corpus.py` — the exact guard whose absence produced the A1 inversion.

---

## 6. Outcome scoring — dual instrument + comparability gate

Every final answer is scored by BOTH instruments and they must agree:

- **Frozen NLI** (`harness/.../outcomes.py`, `nli.py`, config hash `6dbe47a8…`, bs=16, threshold 0.70) —
  the registered instrument, carried forward bit-for-bit so E9's numbers are directly comparable to E5/E8.
- **instrument-v2** (`../E8-instruction-breakpoint/coldstart-package/x1-anatomy/instrument_v2.py`) — the
  claim-grounded value-echo test; on F3-grammar numeric-only strings, value_echo is the sound
  contamination signal.
- **Comparability gate (pre-stated):** because strings are numeric-only, the two instruments must agree on
  ≥ 98% of items. Any disagreement is HAND-ADJUDICATED and published; a disagreement rate > 2% VOIDS the
  numeric-only construction (a compound string leaked in) and halts before verdict. The reported
  contamination number is instrument-v2's, with the NLI number alongside.

Contamination = fraction of `must_change` (stale value) items the final answer still asserts as live.
Completeness = fraction of `must_persist` items retained. `outcomes.py` semantics unchanged; only the
corpus grammar is constrained.

---

## 7. Statistics (pre-stated, two verdict tiers)

- **Primary — paired S-vs-N McNemar** (operator beats matched baseline), N=150 tasks: power 0.99 at the
  design effect (S~10% vs N~1% discordance). The paired contrast is the load-bearing test.
- **Top-dose crossing** of frozen θ=5%, exact binomial, α=0.05 (Arm S, pooled must_change items/dose).
- **E8 three-conjunct break gate** (Cochran–Armitage trend Z>0 AND strict rise p̂₁<p̂₂<p̂₃ AND top-level
  θ-crossing), inherited so E9 is commensurable with the E8 axes — this is the monotone-accumulation
  secondary, honestly reported as underpowered for a shallow curve (a bounded read, not a powered slope).

A confirmed primary with a failed secondary would read "compaction degrades revision but the per-cycle
accumulation shape is below our resolution" — a true bounded result, not a null.

---

## 8. Procedure as executed + deviations (disclosed)

E9 ran as part of Mission X. The apparatus was frozen as above; the following execution deviations are
disclosed, each with its effect on the scored values:

1. **10-shard parallel generation.** The 900-final generation was sharded across 10 parallel workers with
   a lossless resume-bank re-shard (1→4→10). Effect: throughput only; zero science change — the banked
   rows are the same rows in the same schema, resume-bank verified lossless.
2. **Device-ported MPS scorer.** The frozen NLI scoring was run on Apple MPS via a derived scorer (sha
   `b0aae68d → 5dbadf43`, a 3-line device change, diff-verified) rather than CPU. Effect: device only; the
   comparability gate and the equivalence discipline from the E8 GPU rewire certify zero boolean flips
   from the device change. instrument-v2 is deterministic CPU and unaffected.
3. **Exploratory grade.** No pre-registration timestamp exists; the verdict is reported at exploratory
   grade (see README Status).

Provenance: corpus manifest `958d77c4` (150 families, guards 150/150); 900/900 finals with 0 errors;
on-Mini driver + scorer at `~/e9-driver/`.

---

## 9. Verdict (exploratory, RE-SCOPED post-verdict) — corrections survive NEAR-LOSSLESS summarization; the registered band was not achieved

Kill condition (b) fired on the data as scored. But a post-verdict adversarial re-check (2026-07-19) found
the summarizer never achieved the registered 30–50% band: mean length ratio 0.963 / median 0.943 across
all 2,683 S-arm summary rows, 13/2,683 (0.5%) in-band, 448/450 chains redraw-exhausted out-of-band —
and the exclusion flag was INERT (`_score_run` filters only on the FINAL-row regex; `e9_meta.redraw_exhausted`
is never read), so out-of-band chains were silently scored. Harness defect, disclosed. Consequently the
verdict is: corrections survive repeated near-lossless summarization (achieved ratio ≈0.94) with zero real
contamination; **H-COMPACT at real compression ratios is UNTESTED and remains open — fixed re-run required**
(enforce the band or report achieved-ratio as covariate; make the exclusion flag live).

- instrument-v2 contamination **0 / 1800 real at every (arm, dose)**: N-arm 0/150, 0/300, 0/450; S-arm
  0/150, 0/300, 0/450.
- Frozen NLI produced a rising S-arm curve **0 / 9 / 18** — the exact shape that would have falsely
  confirmed H-COMPACT under the pre-audit instrument — but the screen found **0/27 real, all
  supersession-scaffold artifact** (all 900 stale-total pairs screened: stale absent 900/900, corrected
  totals asserted). N-arm frozen NLI is 2/2/2 flat. Same template-collision class as A3 / E5 Arm-C; E9 is
  its fifth independent confirmation. Screen detail:
  `../E8-instruction-breakpoint/coldstart-package/mission-x/E9-SCREEN-APPENDIX.md`.
- Comparability gate **33/1800 = 1.83% ≤ 2% → PASS**.

---

## 10. Scope and limitations

- One model (`claude-sonnet-5`), one summarizer instruction (`305f7e27`), and an ACHIEVED operating point
  of near-lossless summarization (median ratio 0.94 — the registered 30–50% band was NOT achieved, see §9).
  The verdict is AT that achieved point; it does not generalize to other models, summarizers, or real
  compression ratios.
- The dose-response secondary is honestly bounded (shallow at-floor curve, underpowered) — the verdict
  rests on the flat, at-floor contamination, not on a powered monotone slope.
- Exploratory grade: no pre-registration. The frozen apparatus + disclosed deviations are the integrity
  substitute, not a registration timestamp.
