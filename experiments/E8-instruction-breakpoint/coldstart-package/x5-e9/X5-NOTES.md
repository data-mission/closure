# E9 — Related work and novelty differentiation

Written after the lead flagged HIGH OVERLAP RISK against arXiv:2607.08032. All three papers below
were fetched and read (abstracts fully; 2607.08032 body partially — see the evidence boundary noted).
Verdict: **the differentiation holds and is NOT too thin**, on three independent axes. One evidence
boundary is flagged honestly rather than papered over.

## The three prior works

### arXiv:2607.08032 — "What to Keep, What to Forget: A Rate–Distortion View of Memory Compaction in LLMs and Agents" (Colaco & Lahjouji)
The nearest neighbor and the real overlap. What it actually does (verified from abstract + the paper's
HTML §13–14):
- A **theory/framework** paper: a single rate–distortion compaction objective, a layer-agnostic lower
  bound, and a **seven-axis taxonomy** of what to retain vs discard under a token budget.
- It DOES iterate compaction: **§14.2 "Experiment 2: error accumulation under repeated compaction,"**
  with **Prediction 4** — *"under repeated irreversible summarization, end-task error should grow
  super-linearly in the number of compaction events."* So cycle-count-as-dose + super-linear
  accumulation IS their framing and their prediction.
- Its own abstract states the field gap directly: *"the repeated compaction that agents actually
  perform is almost never measured."*

**EVIDENCE BOUNDARY (disclosed, re-probed twice — still open):** the paper's HTML consistently
truncates before Experiment 2's numerical results across multiple fetch routes (abstract page, PDF,
`/html/` endpoint); firecrawl is out of credits. On the last probe the fetcher read §14.2 as a
"proposed but not executed" experiment (Prediction 4 stated, results section not reachable). I could
NOT confirm whether the super-linear curve was measured with numbers or how many cycles were run. So
E9 must NOT claim "they failed to find X," "their numbers were Y," OR "they only proposed it" — all
three are beyond what I verified. The safe, disclosed statement: 2607.08032 PREDICTS super-linear
end-task-error accumulation under repeated compaction and frames it as an open measurement gap; the
executed magnitude is unverified here. To close this before registration: obtain a text-extractable
copy of §14.2 (author page, OpenReview, or a credited firecrawl fetch) and record the measured curve.
E9's novelty does NOT depend on the resolution — its DV (revision fidelity), matched baseline, and E5
tie stand regardless of whether 2607.08032's end-task-error experiment was run.

### arXiv:2606.22528 — "Governance Decay: How Context Compaction Silently Erases Safety Constraints in Long-Horizon LLM Agents" (Chen)
The strongest *empirical* compaction result and E9's direct motivation cite:
- Introduces **ConstraintRot** (long-horizon agent scenarios, deterministic tool-call grading).
- Across 1,323 episodes, constraint violation **rises 0% (policy in full context) → 30% after
  compaction, up to 59%** for some models; and a matched contrast — *"when the constraint survives the
  summary, violation remains 0%, but when it is dropped, violation reaches 38%."*
- DV = **safety-constraint erasure** (prohibited tool actions), not revision fidelity; **single**
  compaction, not an iterated dose; proposes **Constraint Pinning** as a mitigation.

### arXiv:2510.07777 — "Drift No More? Context Equilibria in Multi-Turn LLM Interactions" (Dongre et al.)
The field's counter-result, which E9's dose design exploits:
- Finds **bounded, non-accumulating equilibria**: *"Our experiments consistently reveal stable,
  noise-limited equilibria rather than runaway degradation … multi-turn drift can be understood as a
  controllable equilibrium phenomenon rather than as inevitable decay."*
- Scope = **plain multi-turn conversation** (no compaction operator); DV = **turn-wise KL divergence**
  between the model's and a goal-consistent reference's token distributions; **no belief revision**.

## Related-Work paragraph (drop-in for the E9 registration)

> Repeated context compaction is an active and unsettled measurement target. Colaco & Lahjouji
> (2607.08032) give a rate–distortion account of compaction and a seven-axis retain/discard taxonomy,
> and explicitly predict that "under repeated irreversible summarization, end-task error should grow
> super-linearly in the number of compaction events," noting that "the repeated compaction that agents
> actually perform is almost never measured." Chen (2606.22528) measures a single compaction step
> empirically with ConstraintRot, showing safety-constraint violation rising from 0% in full context
> to 30–59% after compaction, with a matched constraint-survives-vs-dropped contrast (0% vs 38%).
> Against these, Dongre et al. (2510.07777) find that plain multi-turn interaction settles into
> bounded, noise-limited equilibria rather than runaway decay. E9 sits in the gap none of them fill.
> Its dependent variable is neither end-task accuracy (2607.08032) nor safety-constraint erasure
> (2606.22528) nor distributional drift (2510.07777), but **instructed-revision fidelity**: given an
> explicit retract-and-revise instruction, does the model still assert conclusions that depended on a
> retracted premise (contamination of `must_change`) and does it retain the conclusions that should
> survive (`must_persist`) — scored causally per item by a claim-grounded value/verdict test
> (instrument-v2) that the program has already shown is necessary because whole-sentence NLI produces
> ~99% false positives on this family. E9 is the **operator-vs-instruction** experiment: a
> compaction/summarizer arm run against a **matched no-compaction retract-and-revise baseline over the
> identical turns**, so any delta is attributable to the compaction operator, not to turn count,
> correction count, or task difficulty. No prior work contrasts a compaction operator against a
> no-compaction instruction baseline on a revision task; ConstraintRot's survives-vs-dropped contrast
> is the closest, but it compares two compaction OUTCOMES, not compaction against a non-compacting
> control. Finally, E9's threshold and hypothesis are anchored to the program's own registered result
> — E5's single mechanical contraction of a live context injected 10.3% contamination vs 0.9%
> instructed — making E9 the direct test of whether that single-shot operator effect scales into an
> iterated-compaction regime. The field's disagreement (super-linear-accumulation prediction vs
> bounded-equilibrium finding) is exactly what E9's ≥3-level cycle dose is powered to adjudicate on a
> revision DV.

## Why the differentiation is not too thin — the three load-bearing axes

1. **Dependent variable = correction fidelity, causally scored.** 2607.08032 = end-task error;
   2606.22528 = safety-constraint violation; 2510.07777 = KL drift. NONE score whether a retracted
   premise's downstream conclusions are still asserted. This is the whole point of the closure program
   and is unique to E9. VERIFIED: no belief-revision / correction-propagation task in any of the three.

2. **Operator-vs-no-compaction matched baseline.** E9's Arm N (retract-and-revise instruction, full
   transcript retained) vs Arm S (same turns, compacted) is a clean operator-vs-instruction contrast.
   2607.08032 measures compaction against itself across cycles (no non-compacting control on the same
   task); 2606.22528's closest analog (survives-vs-dropped) compares two compaction outcomes, still
   both compacted. VERIFIED: none has a no-compaction baseline arm on a revision task.

3. **Tie to E5's registered contraction result.** E9's H-COMPACT is specifically "does E5's single
   mechanical contraction (10.3% vs 0.9%) scale under iteration by a model summarizer?" — a hypothesis
   only this program can pose, because only this program has that registered prior. None of the three
   share it.

## Design consequences (folded into DESIGN.md)

- **Narrowing already present:** E9's scored strings are numeric-only F3-grammar and its DV is
  contamination/persistence — this is the correction-fidelity DV, already distinct from all three.
  No further narrowing needed; the differentiation is structural, not cosmetic.
- **Positioning:** cite 2606.22528 as direct motivation (compaction empirically erases in-context
  information), 2607.08032 as the theoretical frame + the accumulation prediction E9 tests on a
  revision DV, 2510.07777 as the counter-result E9's dose adjudicates. Add the Related-Work paragraph
  above to the registration.
- **One honest hedge to carry:** because I could not read 2607.08032's Experiment-2 numbers, the
  registration must say E9 tests the accumulation prediction *on a revision DV they do not measure*,
  NOT that E9 is the first to iterate compaction (it is not — 2607.08032 iterates it for end-task
  error). E9's novelty is the DV + the matched baseline + the E5 tie, not "first to vary cycle count."

## Net verdict
CAN-DELIVER differentiation. The overlap with 2607.08032 is real on the cycle-count-as-dose axis, but
E9's dependent variable (instructed-revision fidelity, not end-task error), its operator-vs-instruction
matched baseline, and its E5 anchor are three independent, verified points of separation. The one
thing E9 must NOT claim is primacy on "iterating compaction" — that belongs to 2607.08032; E9's claim
is primacy on iterating compaction against a matched baseline on a correction-fidelity DV.
