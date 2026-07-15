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

Scheme: an integer **1–3** per prompt, **anchored per family** (a "3" means different things in `arithmetic` and
`creative`). Its purpose is twofold: (a) it is the difficulty covariate E0 `PLAN.md` step 6 requires recorded at
construction, so a later analysis can check that difficulty is not confounded with family; (b) it is the knob that
creates within-family volume spread, so each family covers a sub-range rather than sitting at one volume. Higher
difficulty is expected to raise continuation diversity — harder items admit more varied (and more varied-wrong)
continuations — so the covariate is monotone in expected volume within a family. Anchors:

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

Per-family/difficulty → expected-diversity band mapping (the design annotation stored in `expected_diversity`):

| family | difficulty 1 | difficulty 2 | difficulty 3 |
|--------|--------------|--------------|--------------|
| `arithmetic`  | low | low  | mid  |
| `factual`     | low | low  | mid  |
| `deduction`   | low | mid  | mid  |
| `enumeration` | mid | mid  | high |
| `creative`    | mid | high | high |

Every family spans at least two bands (`arithmetic`/`factual`/`deduction`: low→mid; `enumeration`/`creative`:
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

| family | total | answerable | difficulty 1 / 2 / 3 | bands spanned |
|--------|------:|-----------:|----------------------|---------------|
| `arithmetic`  |  42 |  42 | 14 / 14 / 14 | low, mid  |
| `factual`     |  42 |  42 | 14 / 14 / 14 | low, mid  |
| `deduction`   |  42 |  42 | 14 / 14 / 14 | low, mid  |
| `enumeration` |  37 |   0 | 12 / 12 / 13 | mid, high |
| `creative`    |  37 |   0 | 12 / 12 / 13 | mid, high |
| **total**     | **200** | **126** | 66 / 66 / 68 | low, mid, high |

Answerable subset = **126 of 200** (the three labeled families), comfortably above the ≥120 target with margin for
any exclusions (below). Corpus-wide expected-diversity bands: 70 low, 92 mid, 38 high.

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
| `difficulty` | int 1–3 | difficulty covariate, anchored per family (above) |
| `expected_diversity` | "low"/"mid"/"high" | **design annotation** of expected volume band, not a measurement |
| `provenance` | string | sourcing note; hand-authored, with the dataset format it is styled after |
| `answerable` | bool | `true` iff a gold answer exists (drives the AUROC subset) |

## Anti-contamination guarantee

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
