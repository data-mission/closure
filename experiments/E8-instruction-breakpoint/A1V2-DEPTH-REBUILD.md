# A1V2 — the depth axis, rebuilt and re-scored (X4)

**One line:** the registered A1 depth axis was **invalid as built** (a polarity inversion made it measure
revision SUCCESS, not contamination); it was rebuilt with the correct stale-world polarity, re-scored on
the certified instrument, and the verdict is **NO BREAK — instructed revision is robust across derivation
depth, true floor 0/447**.

This file surfaces, at the E8 top level, a finding that would otherwise be buried in the Mission X
package. The full record is `coldstart-package/mission-x/MISSION-X-VERDICT.md` §2.4; the rebuild apparatus
is `coldstart-package/x4-rebuild/`.

## The defect in the registered A1 (depth) axis

A1 is the dependency-depth axis: it doses the number of derivation steps between a corrected value and the
scored conclusion. As registered and run, every `must_change` item held the CORRECTED-world value — but
the scorer (`outcomes._still_asserts`) treats `must_change` as the STALE assertion the model must revise
AWAY from. With the polarity inverted, a correctly-revising Arm-B answer that asserts the corrected value
was counted as CONTAMINATED. So the registered A1 "contamination" of 52% / 97% / 94% at D1/D2/D3 actually
measured revision SUCCESS (~95% on the primary chain at depth 2–3); the D1 52% is a dose-1
insurance-vs-primary item-role composition artifact, not a depth effect. A1 as built contributed NO
depth-failure evidence to H-BREAKPOINT. (The E8 program verdict Block B is unaffected — it rests on A3,
correctly polarized, plus A2.)

This was an undisclosed corpus-authoring bug: there is no intentional-inversion note in Phase 0 / decision
0008. It was found post-verdict by the owner's disbelief at the numbers, then adjudicated by a 450/450
red-check.

## The rebuild (X4)

`coldstart-package/x4-rebuild/` holds a deterministic transform (`transform.py`) that produces
`A1-depth-v2.jsonl` — the A1 depth corpus with:
- `must_change` corrected to hold the STALE-world value (the inverse of the shipped bug),
- the insurance item dropped (it drove the D1 composition artifact),
- `verdict_item` / `item_roles` kept consistent.

The transform is machine-checked (`check_v2.py`: 0 corrected-world leaks across all 447 records) and
hand-spot-checked. It changed ONLY scoring-side fields — `sources` / `question` / `not_A_evidence` are
byte-identical to the original A1 (verified 447/447) — so the existing registered A1 generation already
covers all 447 task_ids, and X4 re-scored those banked draws on the certified instrument with no new
generation. Reusing the banked outputs isolates the polarity variable perfectly.

## Verdict (X4) — NO BREAK

Re-scored per-dose contamination on the correctly-polarized corpus:

| dose | count | trials | rate |
|---|---|---|---|
| D1 | 0 | 149 | 0.000 |
| D2 | 10 | 149 | 0.067 |
| D3 | 3 | 142 | 0.021 |

Against the E8 three-conjunct break gate:
- Cochran–Armitage trend Z = 1.110, one-sided p = 0.133 → uptrend TRUE.
- Strict observed rise (p̂ D1 < D2 < D3): **FALSE** (D3 0.021 < D2 0.067).
- Top-level crossing vs θ=5%: k* = 14, observed 3, p = 0.975 → **crossed FALSE** (p̂ = 0.0211 < θ).
- **A1 BREAK: FALSE** — the gate needs all three conjuncts; it fails on strict-rise and on the top-level
  crossing.

**Interpretation: the depth question is SETTLED — no depth-breakpoint; instructed revision is ROBUST
across derivation depth on the correctly-polarized axis.**

## True floor: 0/447 real

An instrument-v2 claim-grounded screen adjudicated ALL 13 NLI-flagged items as artifacts (11 template
collision, 1 supersession, 1 label collision — the same compound-string class found in A3 and E5 Arm-C).
So the raw NLI rate 13/447 = 2.9% is an instrument-basis number; the **true depth floor is 0/447 = 0.0%
real contamination at any depth**. The NO-BREAK verdict is a real zero, not merely a not-crossed threshold.

## Validity and provenance

- Oracle PASS 0/12 mismatches (447/447 records present).
- Disclosures: 149 families, 141 passed, 8 excluded, 25 pruned.
- Certification chain: Tier-1 equiv 0 flips → 47,202 pairs scored → converter → Stage-2 shard-equiv 0
  flips → 28,072 pairs scored → fresh-CPU oracle PASS.
- The `validity_note` field in the X4 `verdict-numbers.json` is STALE hardcoded old-A1 polarity text and
  does NOT apply to the v2 run — do not carry it.
- Tooling note: the canonical instrument-v2 needs an A1-corpus adapter (read correct-final from derivation
  NODES, not `state_values`) before any AT-SCALE A1 screen; these 13 were hand-certified, tool
  certification for A1 is future work.

## Pointers

- Apparatus: `coldstart-package/x4-rebuild/` (`transform.py`, `A1-depth-v2.jsonl`,
  `transform-register.json`, `check_v2.py`, `X4-NOTES.md`, `REUSE-RESCORE-PIPELINE.md`,
  `PREPARED-GENERATION-COMMANDS.md`).
- Verdict in program context: `coldstart-package/mission-x/MISSION-X-VERDICT.md` §2.4.
