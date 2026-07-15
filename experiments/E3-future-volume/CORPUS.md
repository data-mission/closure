# E3 corpus design — task-family battery for the volume probe

**STATUS: PROPOSED. Binds nothing.** This is a candidate corpus, not an approved one. It is the "real prompts
across ≥5 task families with the leave-one-family-out split designed in" that `LOG-e3.md` names as the next
session's first item, produced ahead of — and gated by — an explicit human go, exactly as `e3-0004` § Freeze
boundary and E0 `PLAN.md` step 6 require ("The corpus is a proposal until approved"). Approval, when and if it
comes, covers three things and nothing else: (1) that these 200 prompts are the confirmatory item set; (2) that
the family partition below is the leave-one-family-out rotation of `e3-0001`; (3) that the gold answers and
difficulty covariates recorded here are frozen at construction, before any hidden state or continuation exists.
Approval does **not** unfreeze any decision in `e3-0001`–`e3-0004`, and it does not itself authorize a run — the
run additionally requires the OSF pre-registration whose timestamp predates it (`e3-0004`).

The candidate prompts are `corpus/candidates.jsonl` (one JSON object per line, schema below). This document is the
design record for that file.

## What this corpus has to serve

Three fixed decisions constrain every choice here:

- **`e3-0001`** — the probe is evaluated in two regimes, and the load-bearing one is **leave-one-task-family-out**:
  train on all families but one, test on the held-out family, rotate over every family. The corpus must therefore
  be partitioned into families that are distinct enough that a shortcut learned on the training families genuinely
  fails to transfer to the held-out one — otherwise the OOD regime tests nothing.
- **`e3-0002`** — ground truth is `log det(G + 1e-6 I)` over **N = 10** seeded continuations per prompt. Every
  prompt (answerable or not) gets a continuous volume target; the regression and OOD analyses run over all 200.
- **`e3-0003`** — the correctness comparison (probe vs verbalized confidence and three other baselines) is scored
  by **AUROC over the answerable subset** — items with a correctness label. The answerable subset must be large
  enough for a stable AUROC and paired bootstrap.

## Family taxonomy

Five families, chosen to be genuinely distinct in **kind** — not paraphrases of one operation — and ordered by
expected continuation diversity from low to high. "Expected diversity" is a **design annotation, not a
measurement**: it is the band the author expects the `e3-0002` volume to fall in, recorded so it can be checked
against the measured volume later, never asserted as a result.

| # | family | kind (what the model must do) | central band | answerable |
|---|--------|-------------------------------|--------------|------------|
| 1 | `arithmetic`   | compute one number from given quantities            | low        | yes |
| 2 | `factual`      | retrieve one canonical world-knowledge fact         | low        | yes |
| 3 | `deduction`    | reason over stated relations to a forced conclusion | mid        | yes |
| 4 | `enumeration`  | produce one valid member of an open category        | mid → high | no  |
| 5 | `creative`     | generate open text (naming, description, invention) | mid → high | no  |

Rationale per family, and why its band is what it is:

- **`arithmetic` (low).** A well-posed computation has one correct number and one dominant solution path, so the
  set of semantically distinct 128–256-token continuations is small — the model converges. Diversity comes only
  from surface phrasing of the same answer, which the sentence embedder largely collapses. This is the low anchor
  of the volume range.
- **`factual` (low).** A closed factual question has one canonical answer; continuation diversity is again mostly
  phrasing. Distinct in kind from `arithmetic`: retrieval from parametric knowledge, not computation. Two
  low-band families that share a band but not a kind are deliberate — the OOD test needs surface-distinct families
  even where their volumes overlap (a probe keying on arithmetic token statistics must still fail on factual
  tokens).
- **`deduction` (mid).** The final answer is forced and unique (so the family is answerable), but the model
  verbalizes a multi-step chain to reach it, and the chain's wording and intermediate framing vary across draws
  even when the conclusion does not — lifting volume above the two recall/compute families while keeping a gold
  answer. This is the answerable family that occupies the middle of the range.
- **`enumeration` (mid → high).** "Name an X" admits many correct members; the continuation set spans genuinely
  different answers, not rephrasings, so volume is high. It carries **no gold label** — there is no single correct
  member — so it contributes to regression and OOD only, never to AUROC.
- **`creative` (mid → high).** Open generation (naming, one-sentence description, invention) has the largest space
  of valid continuations. Distinct in kind from `enumeration`: `enumeration` samples from a bounded category,
  `creative` composes novel text. No gold label.

### Why THESE five make the shortcut test real

The OOD regime discriminates "probe read a real geometric quantity" from "probe found a dataset-specific
shortcut" only if the held-out family is different enough that a shortcut cannot survive the hold-out. The five
families differ along axes a shortcut could otherwise exploit:

- **Kind of cognition** — compute / retrieve / deduce / enumerate / compose are five different operations, not
  five surface skins on one. A probe that latched onto, say, the token signature of arithmetic prompts has nothing
  to grip when `factual` or `creative` is the held-out family.
- **Answer cardinality** — one answer (`arithmetic`, `factual`, `deduction`) vs many (`enumeration`, `creative`).
  A probe keyed to "does this prompt have a unique answer" would split the two groups but cannot rank *within*
  them, and the rotation holds out families from both groups.
- **Prompt surface** — bare numeric/lookup questions, multi-clause relational stories, and terse open imperatives
  have different length, vocabulary, and syntax, denying a probe any single lexical crutch that generalizes.

The rotation is only meaningful if, with one family removed, the training set still spans the whole volume range —
otherwise the held-out number is extrapolation, not transfer. This is enforced two ways. First, the bands overlap
(two families reach `low`, three reach `mid`, two reach `high`), so removing any one family leaves the remaining
four covering `low`, `mid`, and `high`. Second, and more important, **no family is volume-homogeneous** — spread
is put *inside* each family via the difficulty covariate (next section), so even a single family already spans two
bands. The union with any one family held out therefore always covers the full range.

## Difficulty covariate

Scheme: an integer **1–4** per prompt, **anchored per family** (a "3" means different things in `arithmetic` and
`creative`). Difficulties 1–3 are the original within-family degree ladder; **difficulty 4 is a distinct KIND, not a
harder degree** — added by the kind-based hardening (see § Kind-based d4 hardening) because the dress rehearsal
proved the model makes zero genuine errors anywhere on the 1–3 ladder. The open families (`enumeration`, `creative`)
carry no correctness labels and keep the 1–3 ladder; only the three ANSWERABLE families carry d4 items. Its purpose
is threefold: (a) it is the difficulty covariate E0 `PLAN.md` step 6 requires recorded at construction, so a later
analysis can check that difficulty is not confounded with family; (b) it is the knob that creates within-family
volume spread, so each family covers a sub-range rather than sitting at one volume; (c) the d4 tier is the knob that
creates a real CORRECTNESS-negative rate on the answerable subset (the e3-0003 AUROC arm), which the 1–3 ladder does
not — the model is at ceiling on all of it. Higher difficulty is expected to raise continuation diversity — harder
items admit more varied (and more varied-wrong) continuations — so the covariate is monotone in expected volume
within a family. Anchors:

- **`arithmetic`** — 1: single operation on small operands (`8 × 7`). 2: two operations, a percentage, or
  order-of-operations (`3 + 4 × 5`). 3: multi-step word problem with a real-world frame and unit handling
  (discount, area, rate, proportion).
- **`factual`** — 1: near-universal common knowledge (days in a week). 2: standard-schooling knowledge (bones in
  the body, SI unit of force). 3: more specialized but still single-canonical-answer (SI base unit of current,
  atomic number of carbon).
- **`deduction`** — 1: single-step (one syllogism or a two-entity comparison). 2: two-to-three-step transitive
  chain or ordering. 3: four-plus constraints requiring several relations tracked at once.
- **`enumeration`** — 1: tightly bounded category, few valid members (a season, a cardinal direction). 2:
  moderately open (a musical instrument, a European country). 3: broadly open (something found in a kitchen, a
  reason to feel happy).
- **`creative`** — 1: constrained slot-fill (name/title for a specified thing). 2: short-form composition (a
  one-sentence description). 3: unbounded composition (invent a metaphor, a proverb, a creature).

**d4 — kind-based hardening anchors (answerable families only).** A d4 item is a genuinely-different KIND on which
the calibration (`hardening/HARDENING.md`) measured a real 7B error rate while the gold stays single-answer-
unambiguous — NOT a harder degree of the 1–3 anchor. Anchors:

- **`arithmetic` d4** — `arith_mult3x3`: 3-digit × 3-digit multiplication (`374 × 269`). The model runs the long-
  multiplication algorithm and makes a genuine carry/addition slip. Calibrated greedy accuracy **0.125**.
- **`factual` d4** — `fact_numeric_tail`: reverse superheavy/transuranic element lookup (atomic number → element,
  Z = 97…117, the confusable middle). The only factual kind that leaves ceiling; the model confuses the reverse
  names. Calibrated accuracy **≈ 0.55–0.79** (mixed superheavy 0.786; confusable-reverse subset lower).
- **`deduction` d4** — `ded_seat6`: unique 6–7-entity seating puzzles (immediate-adjacency + left-of + negations),
  uniqueness machine-proven by `hardening/ded_verify.py`. Calibrated accuracy **0.20–0.40** (with a truncation
  caveat — see the answer-cap recommendation in HARDENING.md).

Per-family/difficulty → expected-diversity band mapping (the design annotation stored in `expected_diversity`):

| family | difficulty 1 | difficulty 2 | difficulty 3 | difficulty 4 |
|--------|--------------|--------------|--------------|--------------|
| `arithmetic`  | low | low  | mid  | mid |
| `factual`     | low | low  | mid  | mid |
| `deduction`   | low | mid  | mid  | mid |
| `enumeration` | mid | mid  | high | —   |
| `creative`    | mid | high | high | —   |

d4 items are annotated `expected_diversity` "mid": their role is CORRECTNESS-negative injection for the AUROC arm,
not volume-band extension, so they are not claimed to raise the volume band beyond the existing d3 "mid". Every
family still spans at least two bands (`arithmetic`/`factual`/`deduction`: low→mid; `enumeration`/`creative`:
mid→high), which is what makes the leave-one-family-out training set volume-diverse under every rotation.

## Sourcing decision and defense

**Decision: hand-authored, in dataset-inspired formats. No item is copied from any published dataset.** Each
family is written to resemble a familiar benchmark *shape* (arithmetic ≈ GSM8K-style word problems; factual ≈
TriviaQA / Natural-Questions-style closed questions; deduction ≈ bAbI / ProofWriter-style forced-answer logic;
enumeration ≈ CommonGen-style open "name an X"; creative ≈ open-generation prompts) while every prompt string and
gold answer is original. Provenance is recorded per prompt in the `provenance` field.

Defense, in order of weight:

1. **Memorization would corrupt the target, not just the labels.** E3's ground truth is continuation *diversity*
   (`e3-0002` volume). If the model has memorized a benchmark item's answer, its continuations collapse toward
   that answer and the measured volume is artificially depressed — the corpus would then be measuring recall of a
   seen benchmark, not the quantity H-VOL is about. Dataset-derived items thus distort **both** the correctness
   labels **and** the diversity target that is E3's whole novelty. Hand-authoring is the only contamination-clean
   option, and contamination here is not a nuisance variable — it is a direct confound on the dependent variable.
2. **Program precedent.** The same anti-contamination ordering already governs the spike (the 20 throwaway prompts
   in `spike/run_spike.py`, "instruments proven on disposable data first", `FEASIBILITY.md` § Contamination rule)
   and E0 (`PLAN.md` step 4, synthetic fixtures before real data). Hand-authored, contamination-clean items are
   the house style.
3. **Licensing.** Original prompts carry no dataset licence or redistribution constraint into the OSF deposit.

The cost of hand-authoring — that gold answers must be verified unambiguous by the author rather than inherited —
is paid explicitly (labeling protocol below). The one item where a hand-authored fact turned out to have a
research-literature edge case ("hardest natural material", diamond vs lonsdaleite) was **removed** rather than
carried with a caveat, because the answerable families' value depends on their golds being uncontestable.

## Labeling protocol (answerable subset)

Recorded at construction, per the "difficulty covariates recorded at construction / gold recorded at construction"
convention of E0 `PLAN.md` step 6:

- **Which families carry labels.** `arithmetic`, `factual`, `deduction` — each item has a single, unambiguous gold
  string in `gold`. `enumeration` and `creative` have `gold: null` and `answerable: false`; they have no defined
  correct answer and are excluded from the AUROC subset by construction. This split is explicit in the data (the
  `answerable` boolean) and is stated here so a reader does not mistake an open family for a mislabeled one.
- **What "gold" is.** The canonical answer, recorded as the author verified it. `arithmetic` golds are numeric and
  were **recomputed independently in the build script** — the assembly aborts if any stated gold disagrees with a
  from-scratch recomputation. `factual` golds are single canonical facts, each adjudicated correct/incorrect/
  ambiguous by an independent source check; the one ambiguous item was replaced. `deduction` golds are the forced
  conclusion, each checked by re-deriving it from the stated premises.
- **How correctness is scored at run time** (specified now, executed later, never re-tuned after seeing scores).
  A model answer is correct iff it matches `gold` under a family-appropriate normalization: `arithmetic` — extract
  the final number, compare numerically (so `30`, `30.0`, `$30`, `37.5`/`37.50` all match their gold); `factual` —
  case-insensitive match against the gold plus obvious equivalents (digit/word forms `8`≈`eight`; articles
  ignored, so `the Sun`≈`Sun`); `deduction` — normalized match of the answer token (`yes`/`no`/the named entity).
  The exact normalizer is frozen in the run config (`e3-0004`) before any correctness label is scored. The corpus
  supplies `gold`; the harness computes per-item correctness.
- **The correctness label feeding AUROC** is whether the model's answer to the prompt is correct — one label per
  answerable prompt.

## Counts

Built and checked by `corpus/candidates.jsonl`'s assembly (duplicate-prompt check, spike near-duplication check,
arithmetic-gold recomputation all pass).

| family | total | answerable | difficulty 1 / 2 / 3 / 4 | bands spanned |
|--------|------:|-----------:|----------------------|---------------|
| `arithmetic`  |  42 |  42 | 14 / 14 / 0 / 14 | low, mid  |
| `factual`     |  42 |  42 | 14 / 14 / 0 / 14 | low, mid  |
| `deduction`   |  42 |  42 | 14 / 14 / 0 / 14 | low, mid  |
| `enumeration` |  37 |   0 | 12 / 12 / 13 / 0 | mid, high |
| `creative`    |  37 |   0 | 12 / 12 / 13 / 0 | mid, high |
| **total**     | **200** | **126** | 66 / 66 / 26 / 42 | low, mid, high |

Answerable subset = **126 of 200** (the three labeled families), comfortably above the ≥120 target with margin for
any exclusions (below). Each answerable family's original 14 d3 items were REPLACED by 14 calibrated d4 hard-kind
items (the hardening; § Kind-based d4 hardening), so the answerable families now span difficulties {1, 2, 4} — three
crossed levels — and the open families keep {1, 2, 3}. Counts are unchanged (42/42/42/37/37); the replacement is
in-place. Corpus-wide difficulty distribution: 66 d1, 66 d2, 26 d3, 42 d4 (verified by `corpus/assemble_verify.py`).

## Kind-based d4 hardening

The dress rehearsal (`REHEARSAL.md`) established that Qwen2.5-7B-Instruct-4bit makes **zero genuine errors** on the
1–3 difficulty ladder — trivial through very-hard single-answer prompts, including the band the original hardening
plan intended to add. Hardening by degree buys ~zero correctness negatives, so the entire e3-0003 AUROC arm (probe
vs verbalized confidence and the three baselines) would rest on a handful of accidental labels. The fix is to change
KIND, not degree. The calibration (`hardening/HARDENING.md`, 102 disposable prompts, 3 rounds, improved normalizer)
searched for kinds where the 7B genuinely fails while the gold stays single-answer-unambiguous, and found one per
answerable family. Each answerable family's 14 d3 items were replaced in place by 14 items of that family's d4 kind
(`corpus/d4_items.py`, golds verified — arithmetic recomputed from `expr`, factual sourced to IUPAC, deduction
uniqueness proven by brute force in `hardening/ded_verify.py`):

| family | d4 kind | what it is | calibrated greedy accuracy |
|--------|---------|------------|----------------------------|
| `arithmetic` | `arith_mult3x3`     | 3-digit × 3-digit multiplication (`374 × 269`) | 0.125 |
| `factual`    | `fact_numeric_tail` | reverse superheavy lookup (Z 97–117 → element name) | ≈ 0.55–0.79 |
| `deduction`  | `ded_seat6`         | unique 6–7-entity seating puzzles | 0.20–0.40 |

### Expected answerable accuracy (the negative-rate design, stated as arithmetic)

This is a **projection** from the disposable calibration rates — the corpus d4 items are NOT run before registration,
so their exact accuracy is unknown; it is estimated from the same-kind disposable measurements. Model, per family
(42 answerable items = 28 non-d4 at 1–2 difficulty + 14 d4):

    family_accuracy = ( 28 · p_easy + 14 · r_kind ) / 42

with `p_easy ≈ 1.00` (the rehearsal measured d1/d2 answerable accuracy at 10/10, 10/10) and `r_kind` the calibrated
d4 rate. Using the central estimates `r_arith = 0.125`, `r_fact = 0.60`, `r_ded = 0.30`:

- `arithmetic`: (28 + 14·0.125)/42 = 29.75/42 = **0.708**
- `factual`:    (28 + 14·0.60)/42 = 36.4/42  = **0.867**
- `deduction`:  (28 + 14·0.30)/42 = 32.2/42  = **0.767**
- **overall answerable accuracy = mean = (0.708 + 0.867 + 0.767) / 3 = 0.781 ≈ 0.78**, i.e. an answerable **negative
  rate ≈ 0.22**.

Sensitivity over the calibration's uncertainty (`p_easy` 0.98–1.00; `r_fact` 0.55–0.70; `r_ded` 0.20–0.40;
`r_arith` fixed at the measured 0.125): overall answerable accuracy lands in **0.75–0.80**, negative rate **0.20–0.25** —
inside the 60–80% target with margin, and meeting the rehearsal's "≥ 25% preferred negative rate" at the lower edge.
`factual` is the least-certain and highest family (its kind is the hardest to break — the model's factual recall is
near-unbreakable while single-answer-unambiguous), so it contributes the fewest negatives; `arithmetic` contributes
the most. **Caveat (from calibration):** hard `ded_seat6` items produce long chains that can hit the answer cap; a
truncated correctness decode is EXCLUDED, not a negative, so the deduction negative rate above is only realized if the
frozen run config sets the correctness-label answer cap ≥ 768 tokens (HARDENING.md § cautions). At a low cap the
deduction contribution shifts from negatives to exclusions and the overall accuracy rises toward the upper edge.

## Decontamination and repair

The anti-contamination check was extended from the spike-20 to the full DISPOSABLE MANIFEST
(`corpus/DISPOSABLE-MANIFEST.jsonl` — spike-20 + pilot-30 + rehearsal-41 + the 102 calibration prompts = 193
throwaway prompts). `corpus/decontaminate.py` audits every corpus prompt against every disposable prompt under three
content rules: **E** (exact/normalized duplicate), **S** (same-scenario near-dup in an open family, gold null), **G**
(same-gold near-identical clone, Jaccard ≥ 0.85, in an answerable family). The generic short-question frame and the
seating-puzzle boilerplate (Jaccard ≤ 0.80 with a different gold, or a colliding single-letter gold under the frame)
are the accepted frame effect — the same one `REHEARSAL.md` accepted for "9 times 8" vs "9 times 9" — and never flag.

Six contaminated ids were found and replaced in place (same id, new disposable-disjoint content):

| id | original (contaminated) | rule | replacement |
|----|-------------------------|------|-------------|
| `arith-015` | "What is 15 percent of 200?" | E — byte-exact vs pilot-30 | d2 "What is 45 percent of 80?" (gold 36) |
| `fact-003`  | "What is the largest planet in our Solar System?" | E — case-variant vs pilot-30 | d1 "How many wheels does a standard bicycle have?" (gold 2) |
| `fact-028`  | "In what year did World War II end?" | E — byte-exact vs pilot-30 | d2 "How many sides does a pentagon have?" (gold 5) |
| `fact-037`  | "What is the currency of Japan?" | topic+template collision with the calibration `official currency of <country>` items (REHEARSAL-era audit) | **d4** factual (Z=109 → Meitnerium) — decontaminates AND hardens in one move |
| `crea-031`  | "Imagine a new holiday and describe how people celebrate it." | S — same scenario as pilot-30 (verb-swap) | "Invent a board game and describe how it is played." |
| `crea-036`  | "Imagine a creature that lives in the clouds and describe it." | S — same scenario as pilot-30 ("Imagine"/"Design") | "Invent a musical instrument and describe the sound it makes." |

`fact-037` is a borderline case: by the automated content rules it is a frame effect (different country, different
gold), but it shares both the topic (currency) and the template with the calibration currency items, so it is
replaced precautionarily per the REHEARSAL-era audit — and because it is a d3 slot, its replacement doubles as one of
the factual d4 hardening items. The 42 hardening replacements are the d3 answerable ids `arith-029…042`,
`fact-029…042` (including `fact-037`), `ded-029…042` → d4 hard-kind items.

## Assembly and verification

The corpus assembly script — missing from the original deposit — is now `corpus/assemble.py` (declarative,
re-runnable): it attaches a machine-checkable `verify` expression to every arithmetic item, applies the six
decontamination replacements, and applies the 42 d4 conversions from `corpus/d4_items.py`. `corpus/assemble_verify.py`
is the commit-grade proof and must PASS before the corpus is used; it verifies schema, counts (42/42/42/37/37, total
200, answerable 126), difficulty-crossing, no duplicate prompts, **every arithmetic gold recomputed from its `verify`
expression**, **every deduction d4 gold re-derived to a unique solution by `ded_verify`**, and **zero contamination
hits** against the disposable manifest (reporting the residual max token-Jaccard, 0.800 — the pre-existing benign
"9 times 9" vs "9 times 8" frame effect between a corpus d1 item and the rehearsal set, present before this work).

## Exclusion handling

Verbatim from `e3-0002` / `README.md` § Exclusion criteria: a prompt is **excluded, counted, and reported** if
ground-truth sampling fails to yield **N = 10 valid continuations**. Never excluded on probe error — hard and OOD
items are the test, not noise.

- **"Valid" (operational).** A continuation is valid iff, after stripping whitespace, it is (a) non-empty and (b)
  not a refusal — where a refusal is a reply matching the pre-registered refusal patterns (e.g. leading "I can't",
  "I cannot", "I'm unable", "I won't"). The exact pattern list is frozen in the run config (`e3-0004`); it is
  fixed before sampling and not adjusted after seeing outputs.
- **Excluded prompts are dropped from every downstream set** — regression, OOD, and (if answerable) AUROC — and
  the excluded ids and counts are reported alongside results. Re-sampling to force N = 10 is prohibited: it would
  bias the volume toward whatever continuations happened to be valid.
- **Expected exclusion rate.** Near zero for `arithmetic`/`factual`/`deduction` (clean, benign, unambiguous — no
  refusal trigger), so the answerable count is robust and the 126→≥120 margin is not expected to be spent. Slightly
  higher but still low risk for the open families; because they carry no labels, any exclusion there affects only
  the regression/OOD n, not the AUROC subset.

## Field schema

One JSON object per line in `corpus/candidates.jsonl`:

| field | type | meaning |
|-------|------|---------|
| `id` | string | stable id, `<family-prefix>-<NNN>` (`arith`/`fact`/`ded`/`enum`/`crea`) |
| `family` | string | one of the five family names |
| `prompt` | string | the exact prompt text (chat-templated and run per `e3-0001`) |
| `gold` | string or null | canonical answer for answerable families; `null` for `enumeration`/`creative` |
| `difficulty` | int 1–4 | difficulty covariate, anchored per family (above); 4 = kind-based hardening tier |
| `expected_diversity` | "low"/"mid"/"high" | **design annotation** of expected volume band, not a measurement |
| `provenance` | string | sourcing note; hand-authored, with the dataset format it is styled after |
| `answerable` | bool | `true` iff a gold answer exists (drives the AUROC subset) |
| `verify` | string (optional) | arithmetic expression recomputed by `assemble_verify.py` to equal the numeric gold; present on every `arithmetic` item and numeric-gold factual items — the gold is machine-recomputed, never asserted |
| `ded_spec` | object (optional) | `{entities, spec, ask}` for d4 deduction items; `ded_verify` re-proves a UNIQUE solution and that seat `ask` == `gold` |
| `accept` | list (optional) | per-item enumerated acceptable equivalents for the run-time normalizer (F4) |
| `hard_kind` | string (optional) | on d4 items only: the calibrated kind label (`arith_mult3x3`/`fact_numeric_tail`/`ded_seat6`) |

## Anti-contamination guarantee

**Updated for the full disposable manifest.** Zero of the 200 prompts is the same as, or a near-duplicate of, any of
the **193** throwaway prompts now on record — the spike-20, the pilot-30, the rehearsal-41, and the 102 hardening-
calibration prompts (`corpus/DISPOSABLE-MANIFEST.jsonl`). This is verified by `corpus/assemble_verify.py` calling
`corpus/decontaminate.py` (§ Decontamination and repair): **0 contamination hits** under the E/S/G rules, residual
max token-Jaccard **0.800** (the benign frame effect between corpus `arith-008` "9 times 9" and the rehearsal's
"9 times 8" — different content, different gold — present before this work). The six items that DID overlap the
pilot/calibration sets were found and replaced (table above). The original spike-only guarantee is preserved below.

Zero of the 200 prompts is the same as, or a near-duplicate of, any of the 20 throwaway prompts in
`spike/run_spike.py` (`FEASIBILITY.md` § Contamination rule). Checked in assembly: no exact overlap; and the
maximum token-set (Jaccard) similarity between any candidate and any spike prompt is **0.50**, that maximum being
"What is the currency of Japan?" vs the spike's "What is the capital of France?" — a match on the generic
`What is the <X> of <Y>?` function-word frame with **zero shared content words** (currency ≠ capital, Japan ≠
France). Every residual similarity ≥ 0.3 is this same generic-question-frame effect; no candidate shares a topic
*and* a template with any spike item. The spike's distinctive items — capital of France, chemical symbol for gold,
17 × 23, derivative of x³, sum of the first 10 integers, three primary colors, translating "hello", antonym of
"hot", opening line of a mystery novel, an imaginary color, naming a new planet — have no topical counterpart in
the corpus (the early draft's six "chemical symbol for <element>" items, which shared both topic and template with
the spike's gold-symbol prompt, were removed for exactly this reason).
