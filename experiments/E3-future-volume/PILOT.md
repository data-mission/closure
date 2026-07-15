# E3 pilot — the full instrument on 30 disposable prompts

## What this is

A tracer-bullet. The entire E3 pipeline — hidden-state extraction, seeded continuation sampling,
nomic embedding, the ground-truth semantic-volume statistic, and two of the four baselines
(verbalized confidence B1, predictive entropy B3) — run end to end on the local host (Apple M4,
16 GB) against **30 throwaway prompts**. It answers one plumbing question: does the wired-up
instrument produce finite, sane numbers with usable dynamic range before any real corpus exists?
It is **not** a result about the H-VOL hypothesis and contains no confirmatory datum.

The 30 prompts live in `pilot/run_pilot.py`, are marked THROWAWAY, are disjoint from the spike's
20, and span five kinds (6 each): factual QA, math, instruction-following, ambiguous/underspecified,
open-ended creative. The spread exists solely to see the volume statistic's dynamic range across
kinds — whether it separates near-deterministic kinds (factual/math) from high-diversity kinds
(ambiguous/creative).

## What ran, exactly (per the decision records)

Per prompt:

1. **Extraction + entropy (e3-0001, e3-0003 B3).** The prompt is chat-templated and run through
   one forward pass with **no generation**. The pre-sampling vector is
   `model.model(ids)[:, -1, :]` — the post-final-RMSNorm hidden state at the last prompt token
   (hidden dim 3584, fp16 activation cast to fp32). From the **same forward pass**, the head is
   applied to that exact hidden state to get the next-token logits, and B3 (naive predictive
   entropy) is the Shannon entropy of that distribution (float32 softmax). This reuses the spike's
   verified extraction pattern (spike sanity: 20/20 lm_head top-1 match, max abs logit diff 0.03).
2. **Ground-truth sampling (e3-0002).** N = 10 continuations, temperature 0.7 / top-p 0.95,
   max 256 tokens, early EOS kept (EOS id 151645 = `<|im_end|>`). Seed per draw =
   `base_seed + prompt_index * 10 + draw_index`, base_seed = 20260714. Realized lengths and
   per-continuation wall time recorded.
3. **Embedding + volume (e3-0002).** The 10 continuations are embedded with
   `nomic-ai/nomic-embed-text-v1.5` (pinned revision `e9b6763023c676ca8431644204f50c2b100d9aab`,
   output dim 768, CPU). The volume is computed by **calling the validation package**
   (`e3_validation.volume.semantic_volume`) — the exact instrument, not a reimplementation:
   `log det(G + 1e-6 I)` over the mean-centered-then-L2-normalized embeddings.
4. **Verbalized confidence (e3-0003 B1).** Two-turn: the model answers the task (greedy), then in
   a second turn is asked the frozen verbatim elicitation
   ("On a scale from 0 to 100, what is the probability that your answer above is correct? Reply
   with a single integer between 0 and 100 and nothing else."), greedy-decoded. Parse = first
   integer in [0, 100]; one identical retry on parse failure; still-unparsed counted **missing**.

Pins recorded in `pilot/results/run_config.json` (model + revision, mlx-lm version, nomic model +
revision + dim + prefix, base seed and seed formula, sampler, VC elicitation verbatim, sorted-key
SHA-256 config hash).

## DECISION GAP — the nomic task prefix (must be closed before freeze)

`nomic-embed-text-v1.5` **requires** a task-instruction prefix on every input
(`search_document:` / `search_query:` / `classification:` / `clustering:`); the prefix changes
the embedding and therefore **every Gram entry and every volume**. **e3-0002 does not fix this
choice.** This pilot uses **`clustering: `** — the rationale being that measuring the diversity /
dispersion of a set of continuations is a clustering-family use, not a retrieval query/document
pairing. This is a genuine open choice that a reader could reasonably dispute (e.g.
`classification:` or `search_document:` would yield a different volume distribution). **The
decision records MUST close this gap — fix the prefix explicitly in e3-0002 and pin it in
e3-0004 — before the confirmatory freeze.** A second, smaller un-fixed knob surfaced while wiring:
e3-0002 does not state whether the embeddings fed to the volume are pre-normalized; this pilot
feeds the embedder's **raw (un-normalized) 768-dim output** and lets `semantic_volume` do the
mean-center-then-L2-normalize itself. Flagging both so the records can decide, not the code.

## Numbers

All 30 prompts computed, 0 skipped, 0 sampling failures (every prompt produced its 10 valid
continuations — the e3-0002 exclusion rule fired zero times). Machine-readable copy:
`pilot/results/summary.json`; per-prompt records: `pilot/results/prompt_XX.json` (+ `.npz` with
the 3584-dim hidden state and the 10×768 continuation embeddings).

### Semantic volume `log det(G + 1e-6 I)` — overall and per kind

| set | n | min | q1 | median | q3 | max | mean |
|---|---|---|---|---|---|---|---|
| **overall** | 30 | −138.155 | −118.444 | −27.213 | −15.578 | −13.806 | −58.427 |
| factual | 6 | −138.155 | −118.021 | −50.359 | −23.538 | −14.541 | −68.098 |
| math | 6 | −138.155 | −87.736 | −52.007 | −35.204 | −17.579 | −64.833 |
| instruction | 6 | −138.155 | −138.155 | −130.096 | −122.037 | −107.663 | −127.700 |
| ambiguous | 6 | −18.068 | −17.271 | −16.083 | −14.663 | −14.216 | −16.051 |
| creative | 6 | −19.530 | −16.051 | −14.468 | −14.014 | −13.806 | −15.452 |

The key plumbing observation: **the statistic separates the kinds it should separate.** The
degenerate floor −138.155 = 10·log(1e-6) — all 10 continuations semantically identical — is hit
exactly by 6 prompts (2 factual, 1 math, 3 instruction), matching the validation suite's
hand-computed fixture-D minimum, i.e. the floor observed in the wild equals the floor proven on
planted fixtures. Instruction prompts cluster hard against the floor (median −130); ambiguous and
creative prompts occupy a tight high band (−13.8 to −19.5) that does not overlap the
instruction distribution at all; factual and math span the full range depending on how much
elaboration the sampler produces around a fixed answer. Dynamic range overall: ~124 log units.

### Predictive entropy (nats, B3 — same forward pass as the probe vector)

| set | n | min | q1 | median | q3 | max | mean |
|---|---|---|---|---|---|---|---|
| **overall** | 30 | 0.000 | 0.000 | 0.011 | 0.468 | 2.317 | 0.324 |
| factual | 6 | 0.000 | 0.000 | 0.000 | 0.000 | 0.012 | 0.002 |
| math | 6 | 0.000 | 0.000 | 0.000 | 0.002 | 0.365 | 0.061 |
| instruction | 6 | 0.000 | 0.000 | 0.000 | 0.008 | 0.011 | 0.004 |
| ambiguous | 6 | 0.204 | 0.268 | 0.523 | 0.872 | 0.965 | 0.564 |
| creative | 6 | 0.395 | 0.579 | 0.845 | 0.990 | 2.317 | 0.989 |

Near-zero for factual/math/instruction (the first token is essentially determined), clearly
non-zero for ambiguous/creative — B3 is wired correctly and behaves as the cheap floor it is
meant to be.

### Continuation realized lengths (tokens, all 300 draws)

| set | n | min | q1 | median | q3 | max | mean |
|---|---|---|---|---|---|---|---|
| **overall** | 300 | 3 | 14 | 49.5 | 118.5 | 256 | 85.2 |
| factual | 60 | 7 | 8 | 49.5 | 80 | 256 | 72.9 |
| math | 60 | 10 | 32.25 | 82 | 118 | 233 | 85.7 |
| instruction | 60 | 3 | 4 | 12 | 13 | 95 | 10.6 |
| ambiguous | 60 | 30 | 44.75 | 58.5 | 75 | 256 | 89.5 |
| creative | 60 | 16 | 40.75 | 241 | 256 | 256 | 167.1 |

260 / 300 continuations hit EOS before the 256-token cap (early EOS kept per e3-0002); the 40
cap-hitting draws are concentrated in creative prompts. Realized lengths are recorded per draw in
each `prompt_XX.json` for any later length-confound analysis.

### Verbalized confidence (B1)

- **Parse failures: 0. Missing: 0. Retries used: 0 of 30.** All 30 confidences parsed on the
  first greedy attempt (the model reliably emits a bare integer under the frozen elicitation).
- Value distribution: min 70, q1 95, median 100, q3 100, max 100, mean 95.5.
- Histogram (bins of 10): 70–79: 1 · 80–89: 6 · 90–100: 23 · all lower bins: 0.
- The model is near-uniformly overconfident on throwaway prompts — it verbalizes 100 even for
  open-ended creative tasks. Descriptively, this is the known overconfidence of verbalized
  channels; for plumbing purposes what matters is that elicitation, parse, and retry logic all
  executed and the missing-count machinery reported zero.

### Correlations (Spearman, descriptive plumbing observation — NOT a hypothesis test)

Over 30 disposable points, reported only to confirm the wired-up statistics move together in
sane directions — no inference is drawn and none is licensed:

- volume vs next-token entropy: rho = **+0.827** (n = 30)
- volume vs verbalized confidence: rho = **−0.532** (n = 30)

Higher volume ↔ higher entropy, higher volume ↔ lower verbalized confidence: both signs are the
directions one would expect if the plumbing is connected correctly. Nothing more is claimed.

### Wall clock

- Total per-prompt pipeline wall: **1303.5 s (21.7 min)** for 30 prompts, dominated by
  generation (1150.9 s); embedding 9.4 s total on CPU; verbalized-confidence turns 134.7 s.
- Under the FEASIBILITY.md ~60–80 min envelope because most non-creative continuations hit EOS
  long before the 256-token cap.
- Model load 2.1 s (Qwen2.5-7B-Instruct-4bit, cached); nomic embedder load 3.5 s.

## Disclosure block

- **The pilot data is disposable.** Every number here comes from throwaway prompts run to exercise
  plumbing; none of it is evidence for or against H-VOL.
- **The pilot prompts never enter the real corpus.** The 30 prompts in `pilot/run_pilot.py` are
  marked THROWAWAY, are disjoint from the spike's 20, and MUST NOT appear in, or seed, the real E3
  corpus — same anti-contamination ordering as the spike and the synthetic-fixtures rule.
- **Any threshold informed by pilot observations is pilot-informed.** If any choice in the frozen
  config (e.g. a volume cutoff, an expected dynamic range, the nomic prefix) is set with reference
  to what this pilot showed, it will be **disclosed as pilot-informed in the registration** — the
  program's pilot-testing discipline: the pilot may inform choices, but the fact that it did is
  itself registered.
