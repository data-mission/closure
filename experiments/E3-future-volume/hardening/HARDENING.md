# E3 kind-based hardening — calibration record and frozen normalizer spec

**The dress rehearsal proved Qwen2.5-7B-Instruct-4bit makes ZERO genuine errors on the current
corpus material at any difficulty 1–4 (REHEARSAL.md). Hardening by DEGREE is dead. This record is
the empirical search for hard KINDS: prompt families where the 7B genuinely fails while the gold
stays single-answer-unambiguous, measured on 102 DISPOSABLE prompts across three calibration rounds,
scored by an improved normalizer that fixes the rehearsal's V1–V5 vagueness findings. The result:
arithmetic breaks cleanly, factual breaks only on a narrow reverse-lookup tail, and deduction breaks
only once its scoring bug is fixed — three in-band kinds, one per answerable family, and a stronger
empirical statement than the rehearsal's: even KIND-hardening leaves this model at ceiling on almost
everything except mechanical computation.**

All prompts here are THROWAWAY. They are enumerated in `calib_prompts.py`, listed in
`corpus/DISPOSABLE-MANIFEST.jsonl`, and MUST NEVER enter, or seed, `corpus/candidates.jsonl`. The
corpus's d4 items (`corpus/d4_items.py`) are authored SEPARATELY and disjointly (different operands,
different atomic numbers, different constraint sets) and were never shown to the model here.

## Run configuration (identical to the rehearsal greedy path)

Model `mlx-community/Qwen2.5-7B-Instruct-4bit`, pinned revision `c26a38f6a37d0a51b4e9a1eb3026530fa35d9fed`,
greedy decode (temperature 0, deterministic — no seed), chat-templated, EOS-terminated. The ONE
intentional change from the rehearsal greedy answer: the answer token cap is raised 256 → **640**
(round 3 deduction: 900), because the rehearsal's single "negative" was a 256-cap truncation, not a
wrong answer (improved-normalizer F1). Determinism: greedy is a function of (model, revision,
prompt); reproduced by `calibrate.py --rounds 1 2 3 --max-tokens 900`.

## Calibration curves — per kind, per round (greedy accuracy; truncated replies EXCLUDED, reported)

Scored by `improved_normalizer.py` (spec below). Accuracy is correct / (completed, non-truncated).

| round | kind | → family | correct / n | acc | trunc | band 0.30–0.80 |
|---|---|---|---|---|---|---|
| R1 | `arith_mult3x3`     | arithmetic | 1 / 8  | **0.125** | 0 | below (hardest) |
| R1 | `arith_multistep`   | arithmetic | 6 / 8  | 0.750 | 0 | **IN BAND** |
| R1 | `unit_convert`      | arithmetic | 6 / 6  | 1.000 | 0 | too easy |
| R1 | `letter_count`      | arithmetic | 4 / 8  | **0.500** | 0 | **IN BAND** |
| R1 | `fact_obscure`      | factual    | 15 / 15| 1.000 | 0 | ceiling |
| R1 | `ded_trap`          | deduction  | 7 / 8  | 0.875 | 0 | above |
| R2 | `arith_multistep`   | arithmetic | 6 / 7  | 0.857 | 0 | (pooled R1+R2 = 12/15 = **0.800**) |
| R2 | `fact_reverse`      | factual    | 13 / 14| 0.929 | 0 | ceiling |
| R2 | `ded_hard`          | deduction  | 1 / 5  | **0.200** | 3 | below |
| R3 | `fact_numeric_tail` | factual    | 11 / 14| **0.786** | 0 | **IN BAND** |
| R3 | `ded_harder`        | deduction  | 2 / 5  | **0.400** | 1 | **IN BAND** |

### Three chosen kinds (one per answerable family) and what they mean

- **arithmetic ← `arith_mult3x3` (0.125).** 3-digit × 3-digit multiplication. The model runs the
  standard long-multiplication algorithm correctly step by step, then makes a genuine addition/carry
  slip in the partial-product sum (`92996`→`93096`, `277508`→`277328`, `419986`→`419806`). Clean
  numeric gold, bit-exact scoring. `arith_multistep` (0.80) and `letter_count` (0.50) are two more
  in-band arithmetic kinds (trap word-problems: 5-machines/5-widgets → the model answers 100 not 5;
  tank fills; and letter counting: `strawberry` → the model says the letter r appears "twice").
- **factual ← `fact_numeric_tail` (0.786).** Reverse superheavy/transuranic element lookup
  (atomic number → element name). This is the ONLY factual kind that broke ceiling. `fact_obscure`
  (obscure capitals/currencies: Ngerulmud, Bandar Seri Begawan, Podgorica — all correct) and
  `fact_reverse` (Mo=42, W=74, weber, becquerel — all correct) stayed at 1.00 / 0.93. The model
  knows forward atomic numbers and famous transuranics (Oganesson, Mendelevium) but confuses the
  reverse names in the confusable middle (Z=113→"Copernicium" not Nihonium; Z=115→"nihonium" not
  Moscovium). **This is the load-bearing empirical finding for factual: within the unambiguous-
  single-answer constraint, this model's factual recall is essentially unbreakable except on the
  superheavy-name tail.**
- **deduction ← 6–7 entity seating puzzles (`ded_hard` 0.200 / `ded_harder` 0.400).** Multi-
  constraint orderings with immediate-adjacency, left-of relations and negations. The model produces
  a 300–900-token chain and either (a) violates a constraint and concludes a wrong seat, or (b) runs
  out of token budget mid-derivation (truncation). Golds are machine-derived and their uniqueness is
  proven by brute force (`ded_verify.py`).

### Two decision-grade cautions the calibration surfaced

1. **The deduction rate is only knowable after a scoring fix.** The naive "does the gold entity
   letter appear in the reply" scored deduction at 22/22 = 1.000 — a mirage, because in a long CoT
   the entity letters A–H appear THROUGHOUT the reasoning. The true rate (0.20–0.40) is visible only
   once the scorer extracts the model's CONCLUSION letter (F5b below). Any E3 run that scores
   deduction correctness by substring/token-presence will fabricate a ceiling; the frozen normalizer
   must use conclusion extraction.
2. **The token cap poisons deduction labels (REHEARSAL point #5, confirmed).** `ded_hard` truncated
   3/8 replies at cap 640; `ded_harder` 1/6 even at 900. A truncated reply is EXCLUDED, not a
   negative — so at a low answer cap the hard deduction items yield exclusions, not the negatives the
   AUROC arm needs. **Recommendation for the frozen run config (e3-0004): answer cap ≥ 768 tokens for
   the correctness-label decode**, with truncated replies flagged and excluded (never scored wrong).

## Improved normalizer — frozen spec (fixes rehearsal V1–V5), ready for registration

`improved_normalizer.py`. Self-check 27/27 (12 rehearsal-parity cases — every answer the rehearsal
scored is scored identically — plus 15 cases exercising each fix). `score(item, answer, eos_hit)`
returns `(is_correct, extracted, note, truncated)`; `item` = `{family, gold, accept?, tol?}`.

- **F1 (fixes V1 — "final number" undefined under truncation).** (a) The answer cap is raised so a
  completed chain-of-thought is not cut. (b) For a COMPLETED (EOS) arithmetic reply, extract the
  number after the LAST answer marker (`=`,`is`,`so`,`therefore`,`total`,`answer`,`:`), else the
  last number. (c) For a reply that did NOT hit EOS, return `truncated=True` UNCONDITIONALLY and
  EXCLUDE it — a truncated reply never emitted its final answer, so it is a flagged exclusion, never
  a scored error. A fake negative from truncation is therefore impossible.
- **F1c (fixes a V1 corollary — arithmetic vs factual number direction).** Arithmetic answers
  CONCLUDE a chain (take the LAST/after-marker number); factual answers are STATED UP FRONT ("the
  atomic number of fermium is 100. It was discovered in 1952…") so a trailing discovery-year or group
  number must not override the fact — factual-numeric golds take the FIRST number. Without this,
  correct forward-lookup facts scored wrong on the trailing year.
- **F2 (fixes V2 — no numeric tolerance).** Exact float equality after stripping `$ , %` by default;
  each item MAY declare `tol` (absolute). Correct iff `|got − want| ≤ max(1e-9, tol)`. Integer golds
  keep `tol=0` (bit-exact), so hard multiplication cannot be scored right by being "close".
- **F2b (spelled integers).** Number words 0–20 are digitized in the numeric path, so a correct count
  answered in words ("appears three times", "four vowels") is parsed, not a fake negative.
- **F3 (fixes V3 — token vs substring).** Whole-token / contiguous-token-run match; NEVER substring,
  so single-letter golds are safe.
- **F4 (fixes V4 — "obvious equivalents" not enumerable).** Per-item `accept` list of alternative
  acceptable golds, frozen at construction (e.g. `dong` accepts `Vietnamese dong`; `Vatican City`
  accepts `Vatican`). Digit↔word (0–20) and article stripping remain global.
- **F4b (diacritic/native-spelling folding).** NFKD + combining-mark stripping + a small non-
  decomposing-letter map (`ł→l`, `đ→d`) so a CORRECT answer written natively ("Polish złoty",
  "Vietnamese đồng") matches the ASCII gold — this alone lifted the measured `fact_obscure` rate
  from 0.867 to 1.000 by removing two fake negatives.
- **F5 (fixes V5 — deduction answer token).** Numeric deduction golds route through the numeric path
  (LAST-number direction); yes/no and named-entity golds through F3.
- **F5b (single-letter entity golds — the deduction-scoring fix).** A single-letter gold (`A`–`H`
  entity label, or chemical symbol `O`/`K`) is (i) case-ambiguous with the article `a`, and (ii) in a
  long CoT the letter appears throughout the reasoning. Resolution: extract the CONCLUSION letter —
  the standalone uppercase A–Z after the LAST answer marker, else the last standalone uppercase
  letter — and compare CASE-SENSITIVELY to the gold / accept letters. Truncated replies are excluded
  (F1). This is what turns the fabricated deduction ceiling (22/22) into the true rate (0.20–0.40).

## Disposable disclosure block

- **All 102 calibration prompts (rounds 1–3) are THROWAWAY.** They are marked DISPOSABLE in
  `calib_prompts.py`, listed in `corpus/DISPOSABLE-MANIFEST.jsonl` (with the spike-20, pilot-30 and
  rehearsal-41), and are disjoint from `corpus/candidates.jsonl` (checked by `assemble_verify.py`,
  0 hits, max token-Jaccard 0.800 = the pre-existing benign frame effect).
- **No number here is evidence for or against H-VOL.** These are per-kind accuracy measurements on
  disposable data whose only purpose is to select the corpus's d4 hard KINDS and their expected
  negative rate. No hidden state, volume, or probe was computed.
- **This calibration is pilot material and must be disclosed as such in the registration**, alongside
  the spike, pilot, and rehearsal. Every frozen choice traceable to it — the three d4 kinds, the
  improved-normalizer F1–F5b spec, the answer-cap recommendation, the expected-accuracy projection —
  is disclosed as calibration-informed. Per the program's pilot-testing discipline, the improved
  normalizer's fixes were surfaced by DISPOSABLE data and are frozen BEFORE any confirmatory datum.
