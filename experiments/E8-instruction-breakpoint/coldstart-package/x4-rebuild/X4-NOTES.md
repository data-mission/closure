# X4 — A1 depth corpus rebuild (polarity fix + insurance drop)

**Deliverable:** `A1-depth-v2.jsonl` — the E8-A1 depth corpus with `must_change` corrected to hold the
STALE-world value (the inverse of the shipped bug), the insurance item dropped, and `verdict_item` /
`item_roles` kept consistent. Built by a deterministic transform, machine-checked, hand-spot-checked.
Zero model calls (deterministic transform, no generation).

## The bug this fixes

The registered A1 corpus put the CORRECTED-world value in every `must_change` item (e.g. "Basic MRR is
$3,000" = 30×100, the post-correction value). The scorer (`outcomes._still_asserts`) treats
`must_change` as the STALE assertion the model must revise AWAY from — so a correctly-revising Arm-B
model was scored CONTAMINATED. The axis measured the inverse of its claim (confirmed 450/450 by P2 and
the post-verdict red-check). X4 rewrites `must_change` to the stale value so the axis measures what it
claims: does the model still assert the pre-correction value.

## Novelty (deep-read verdict — X4 lands in an explicitly-flagged-open gap)

Depth-as-dose is NOVEL against the two nearest 2026 papers:
- **STALE (arXiv:2605.06527)** tests only binary 0-hop vs 1-hop stale-fact propagation (Type I/II) and
  explicitly names "multi-step cascading updates" as unaddressed future work. X4 = graded 1/2/3-hop
  derived-value chains (dose = chain depth), causally scored through the derivation graph, in-context.
- **TRACK (arXiv:2601.15495)** doses on fact-COUNT, not chain DEPTH. X4 doses on derivation depth (the
  number of dependent ops between the corrected node and the scored conclusion), a distinct axis.

X4 occupies the gap STALE flags open and TRACK does not fill: graded causal-depth revision, scored on
the intermediate/terminal derived values rather than on a flat fact set.

## Transform (`transform.py`, deterministic)

Per record:
1. **Stale-world recompute.** Substitute `corrected_node.a_value` for its `.value`, re-run
   `derivation.ops` in order (operators `* + - >= <= ceil_div`). Corrected op outputs match the corpus
   node values exactly (integrity check); stale op outputs are the new must_change numbers.
2. **Numeric items** (strata + numeric primaries): locate the corrected number in the prose and rewrite
   it to the stale number, preserving `$`/comma/decimal/sign style. Word-boundary aware so a stale
   `-60` is not misread as a leftover `60`, and entity labels like `Rosa-2` are never touched.
3. **Boolean primaries** (D3, final op is a `>=`/`<=` comparison; 145 records, 144 accepted): the
   free-form corrected verdict ("Finance flags the month as healthy") has NO deterministic English
   negation (82/145 uncovered by any antonym table — verified). Replaced with a deterministic canonical
   stale sentence built from the derivation: `"The <quantity> is <stale_intermediate>, which
   <meets or exceeds | falls short of | is within | exceeds> the <target> <target-noun>."` Polarity is
   the stale boolean. Same shape as the A3 threshold template; carries the correct stale proposition
   unambiguously for the NLI scorer. **Tradeoff (flagged):** these sentences use the derivation's node
   labels ("Combined MRR", "Printer due day"), so they read more clinically than the original prose.
   This is the price of full determinism on verdicts that cannot be mechanically negated; it is correct
   and scorer-valid.
4. **Insurance drop.** The insurance item (last `must_change` entry) is removed, along with its parallel
   `verdict_item` and `item_roles` entries. P2 proved its 2nd operand is a node in 0/450 records and
   unrecoverable from `sources` in the large majority of families — a deterministic transform has no
   data source for it, and P2's rule is "never leave it in place." 447 insurance items dropped, each
   recorded in `transform-register.json`.
5. **Fail-closed per record.** After transform, assert: every emitted numeric holds the stale value;
   zero corrected-world $/comma values remain (boundary-aware); `must_change`/`verdict_item`/
   `item_roles` lengths consistent; no `insurance` role survives. Any violation → the record is
   REJECTED (not half-transformed) with a reason in the register.

## Results

| | count |
|---|---|
| source records | 450 |
| **accepted (A1-depth-v2.jsonl)** | **447** (149 per dose D1/D2/D3) |
| rejected (fail-closed) | 3 |
| numeric items rewritten | 750 |
| boolean primaries canonicalized | 144 |
| insurance items dropped | 447 |
| verdict_item/item_roles consistency violations | 0 |

**The 3 rejects are one family, A1-D-0008 (D1/D2/D3)** — its primary is "Five plates are required",
a number spelled as an English WORD. Rewriting `5→8` would require an English number-word generator
(spelling, capitalization, singular/plural), a new fragile surface. Per fail-closed doctrine and the
0.7% cost (3/450), the family is dropped, not risked. Recorded in the register.

## Acceptance (`check_v2.py`) — the inverse-of-the-bug proof

Independent re-derivation of BOTH worlds from each accepted record's own derivation graph, then asserts
per record. Result (lead re-ran and confirmed): **447 records, 750 numeric + 144 boolean items, 894
checks, 0 corrected-world value leaks, 0 failures → ACCEPTANCE PASS.** Zero corrected-world values
remain anywhere in any `must_change` — the exact inverse of the shipped bug, machine-checked across all
447 (charter req 5).

## 10-record hand spot-check (both ends of the transform)

All read before→after by hand (reproducible via the register). Representative:
- **A1-D-0001-D1** (numeric, direct): `$3,000 → $2,500` (25×100). Insurance `$360` dropped. ✓
- **A1-D-0001-D3** (boolean primary): "…meets the board's $6,500 target" → "The Combined MRR is 6,100,
  which falls short of the 6,500 Monthly combined target." Polarity flipped (6,100 < 6,500). ✓
- **A1-D-0002-D3** (REVERSED polarity — correction downrates): stale "…which meets or exceeds the 900
  Order quantity" (1,000 ≥ 900, True); corrected verdict was "cannot be completed" (False). Flip
  correct. Entity label `Rosa-2` preserved (200 swapped, not the "-2"). ✓
- **A1-D-0017-D2** (negative value): surplus `60 → -60`. Sign handled; corrected `60` not left behind. ✓
- **A1-D-0099-D1** (decimal): contribution `$4.50 → $4.00`. Decimal style preserved. ✓
- **A1-D-0007-D2** (fraction op): rented units `240 → 180` (×0.75), revenue `$21,600 → $16,200`. ✓
- **A1-D-0004-D3** (free-form verdict): "Finance flags the month as healthy" → "The Monthly gross margin
  is 4,800, which falls short of the 5,000 Health threshold." The un-negatable verdict, canonicalized. ✓
- **A1-D-0003-D3** (`<=` op): "does not meet the working-day-20 deadline" (False) → "The Proofing finish
  day is 18, which is within the 20 Printer due day" (True, 18 ≤ 20). ✓

## Generation / scoring (PREPARED, not launched) — filter entry point VERIFIED

See `PREPARED-GENERATION-COMMANDS.md`. The filter-tier entry point is `filter_stage.py` (verified: it
generates the 2-state×3-draw `filter-gen.jsonl` with `filter_state`/`draw_index` and CPU-scores in one
command; `run_axis_gpu.sh` then GPU re-scores for certification). Fresh-gen workload: filter tier
**894 draws**; Stage-2 **447 draws**. Scoring is model-free (GPU NLI), adding no generation load.

**Reuse alternative flagged for the owner (⚑):** the transform changed ONLY scoring-side fields —
`sources`/`question`/`not_A_evidence` are byte-identical to the original A1 (verified 447/447), and the
existing registered A1 generation already covers all 447 task_ids. So X4 can be **re-scored with no new
generation** against the existing draws (the prompt is identical, only the stale-polarity `must_change`
changes). This isolates the polarity variable perfectly and is the recommended first pass; regenerate
(the 894 + 447 fresh draws) only if an independently-registered fresh run is required. Owner decides.

## Files

- `transform.py` — the deterministic transform (run: `python3 transform.py`).
- `A1-depth-v2.jsonl` — 447 corrected records.
- `transform-register.json` — every record's disposition, per-item before/after, drops, rejects+reasons.
- `check_v2.py` — acceptance checker (run: `python3 check_v2.py`; exits nonzero on any failure).
- `PREPARED-GENERATION-COMMANDS.md` — filter (`filter_stage.py`) + Stage-2 commands, workload estimates.

## Limitations / decisions flagged

1. **Boolean canonical sentences use node labels**, reading more clinically than original prose. Correct
   and scorer-valid; the alternative (LLM-negated prose) is not generation-free/deterministic. If the owner
   prefers natural prose for the 144 boolean primaries, that is a generation step, not a transform.
2. **A1-D-0008 dropped** (word-form number) — 3 records, fail-closed rather than risk a word-form
   transformer. Recoverable later if desired via an explicit number-word map with its own assertions.
3. **`must_change_depth`** entries for dropped insurance items are removed in lockstep; the depth list
   for surviving items is preserved in order.
4. The transform asserts corrected op outputs equal the corpus node values (integrity) — if any future
   corpus edit desyncs prose from nodes, those records fail-close rather than emit a wrong stale value.
