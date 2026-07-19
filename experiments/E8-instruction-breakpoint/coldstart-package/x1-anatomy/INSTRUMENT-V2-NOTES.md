# instrument-v2 — design notes + prior-art positioning

## What instrument-v2 is
A claim-grounded REVISION-FIDELITY test. Given a task carrying a stale→corrected value/verdict pair, it
scores whether a model output ECHOES the STALE (superseded) computed value and/or the STALE verdict
DIRECTION as a live proposition — after excluding (a) the shared threshold constant, (b) the correct-
final value, (c) supersession/retraction clauses, (d) unit collisions, (e) label ordinals. It replaces
whole-sentence NLI entailment, which fires on the shared "{quantity} {computed} {verdict} {threshold}"
scaffold and produced E8-A3's phantom ~26% and E5's phantom Arm-C 10.3% (both re-adjudicated to 0 real).
Two channels: value_echo + verdict_echo, both gated on the stale VALUE being asserted live (a corrected-
value assertion cannot trip either). Acceptance gates: 200 A3 flags→0 real, 30-item hand sample→0,
5 spot-checks clean, 10/10 synthetic positive controls (must FIRE). Adversarially hardened: 60/60 hard
positives, 0/60 negative-control false fires, 40/40 subtle F2 echoes, 30/30 verdict channel.

## Prior art (owner-ordered novelty sweep; a reviewer WILL find PCN immediately)

### Proof-Carrying Numbers — arXiv:2509.06902 · github.com/worldbank/pcn  (ARCHITECTURALLY CLOSEST)
PCN emits numeric spans as **claim-bound tokens** and runs a **renderer-layer verifier** that checks each
token against a **declared policy**; policy vocabulary = **{exact equality, rounding, aliases, tolerance
with qualifiers}**. It formally proves **soundness, completeness under honest tokens, fail-closed
behaviour, and monotonicity under policy refinement**, and OUTPUTS a **binary verified/unverified
marking** (unmarked ⇒ unverified — fail-closed). It verifies FAITHFULNESS TO STRUCTURED SOURCE DATA
(is this emitted number a policy-compliant copy of an available source value?) — a hallucination/misquote
guard; ground truth = the source table; question = span-vs-source. NO concept of revision, stale-vs-
corrected, or directional echo (confirmed absent from the paper).

DIFFERENTIATION PARAGRAPH (the defensible positioning):
> instrument-v2 shares PCN's substrate — extract numeric spans from generated text and mechanically
> compare them to reference values under declared policies — but the two answer different questions.
> PCN is a FAITHFULNESS verifier: it marks each number verified/unverified against structured source
> data and displays the mark, fail-closed. instrument-v2 is a REVISION-FIDELITY scorer over UNSTRUCTURED
> CLAIM TEXT against a STALE↔CORRECTED value/verdict PAIR: it asks which side of a known supersession the
> model landed on — did it echo the superseded value/verdict, or assert the corrected one — while
> excluding the value that DIDN'T change (the shared threshold) and any mention inside a retraction
> clause. PCN has no supersession relation, no stale/corrected pair, and no directional-echo notion; its
> policies compare a span to one source value, whereas v2's policy is defined over a *pair with a
> supersession relation* and scores *which version was asserted*. v2's verdict channel (echo of a stale
> VERDICT direction embedded in an identical requirement sentence — "meets" vs "fails" on the same
> "X vs threshold" template) has no PCN analog at all.

HONEST thinness assessment + ADOPTION:
- The mechanical core (span extraction + reference comparison + exclude-the-shared-constant) IS genuinely
  PCN-adjacent. v2 should ADOPT PCN's policy vocabulary rather than invent parallel terms:
  · value_echo's "stale == out-span, ≠ threshold, ≠ correct, unit-compatible" = a PCN **alias +
    tolerance(exact)** comparison run against the STALE value instead of the source value.
  · the unit guard = PCN's **alias/qualifier** notion (a value must carry a compatible measure).
  · number-format variants ($, commas, plain) = PCN **aliases**.
- Genuinely NEW past PCN (name these as the revision-specific extensions): (i) the stale↔corrected PAIR
  as the reference, not a single source value; (ii) directional echo — stale side vs corrected side of a
  supersession; (iii) the SUPERSESSION-CLAUSE exclusion (not in PCN); (iv) the verdict-word echo channel.
- If a reviewer says "this is PCN": same span-verification substrate, but the policy is defined over a
  supersession relation and scores which version was asserted — which PCN does not model. That is the
  honest line; the extraction/comparison plumbing is not novel, the revision-echo task is.

### QuanTemp — arXiv:2403.17169
A multi-domain benchmark of real-world NUMERICAL CLAIMS for fact-checking: verify a numerical claim
against collected evidence, labelled, macro-F1 (baseline ~58.32), supports claim-decomposition methods.
Task = claim-vs-evidence VERIFICATION, NOT stale-value echo.
APPLICABILITY to v2 (assessed):
- As a v2 TASK benchmark: NOT applicable. QuanTemp has no stale↔corrected pairs, no supersession relation,
  no directional-echo label — it labels a claim true/false/conflicting against evidence. v2's question
  (did the output echo the superseded value) is not representable in QuanTemp, so QuanTemp cannot grade
  v2's verdict.
- As a v2 EXTRACTOR validation: PARTIALLY applicable, worth doing as OPTIONAL hardening (not a gate).
  v2's numeric-span + value-assignment slot parser (stale_value_from_mc, unit extraction) could be
  spot-validated for extraction precision/recall against QuanTemp's numerical claims (which carry gold
  claim structures / decompositions) to show the extractor generalizes past A3's templates. Document as
  "extractor validated on QuanTemp numerical claims; the revision-echo task itself has no QuanTemp
  analog." Not required for the A3/E5 conclusions (those are hand-adjudicated + positive-controlled).

## Coordination note
x1-anatomy delivered rescore.py::verify_item + positive_controls.py (3/3 fire, 3/3 clear) as the
instrument-v2 prototype and owns the full A3 rescore. This file's instrument_v2.py is my parallel build
(4/4 gates, 10 synthetic controls, E5-adapted). The PRODUCTIONIZED instrument-v2 should be ONE tool built
on x1's verify_item as the base + x1's positive_controls AS the acceptance fixture, extended with my 10
synthetic-injection controls and the E5-corpus slot logic (E5 templates differ from A3 — qualitative
verdict conclusions, no "X is <val>, which <verdict> <threshold>" numeric template; the E5 adaptation
lives in the per-item logic used in E5-ARMC-REEXAM.md). Merge target: agree with x1 on one verify_item
signature + one positive_controls fixture, then layer PCN's {exact/rounding/alias/tolerance} policy
vocabulary on top and name the supersession-exclusion + directional-pair as the revision extensions.
