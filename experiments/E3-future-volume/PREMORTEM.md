# E3 pre-mortem — the failure post-mortem, written before the run

Method: assume E3 ran and the outcome is worthless or embarrassing; write the post-mortem now, while
every fix is still free. Each scenario states the death, the current evidence for/against it, and the
disposition: **fix now** (design change before freeze), **control** (pre-registered check that would
catch it), or **accept openly** (a real limitation the registration states rather than hides).
Companion to the five-lens adversarial audit and the labeled dress rehearsal running alongside; their
findings supersede the guesses here where they disagree. Written 2026-07-14, before corpus approval,
before registration, before any confirmatory datum.

## 1. "The probe was reading answer length, not semantic width"

**The death.** Volume correlates with continuation length variance (long creative rambles spread in
embedding space; short answers cluster). The probe learned "this prompt yields long answers" — a
banality — and every headline number followed. A reviewer computes ρ(volume, length) from our own
released data and the paper dies in a tweet.
**Evidence now.** Plausible-to-likely at some strength: pilot creative continuations hit the 256 cap
40/40 times while factual ones EOS'd at ~10 tokens. The rehearsal computes ρ(volume, mean length) and
ρ(volume, std length) on labeled disposable data.
**Disposition: control, possibly fix.** If ρ is high: pre-register a length-residualized volume as
co-target and within-family fidelity as a co-metric (families are internally more length-homogeneous);
consider a length-capped generation variant as a sensitivity arm. Not registering any length control
when the confound is this obvious would be negligence — this one is mandatory regardless of the
rehearsal number.

## 2. "The probe beat verbalized confidence but lost to free entropy — and the verdict called it CONFIRMED"

**The death.** Next-token entropy (B3) costs nothing, comes from the same forward pass, and pilot
showed ρ(volume, entropy) = 0.827. E3 'confirms', then someone shows B3 predicts correctness as well
as the probe. "Your geometric quantity is a softmax statistic with extra steps." The CONFIRMED verdict
never required beating B3 — only verbalized confidence.
**Evidence now.** The strongest known hole in the verdict contract: the README's confirmation clause
names only verbalized confidence; B3 is specified in e3-0003 but orphaned from every verdict branch.
**Disposition: fix now.** The confirmation conditions should require the probe to add value over B3
(at minimum: probe AUROC − B3 AUROC with a pre-registered floor, or volume-probe R² above what
entropy alone regresses). This is a protocol-refinement question — the README's CONFIRMED wording
("useful fidelity") arguably intends it, but arguably is not a standard. Needs an explicit clause
before freeze.

## 3. "R² was meaningless on the actual target distribution"

**The death.** The log-volume target has a point mass at the degenerate floor (pilot: 6/30 prompts at
exactly 10·log(1e-6)) plus a continuous cluster ~120 log-units away. R² on a bimodal
target with an atom rewards predicting the mode split, not the continuum; the "continuous quantity"
claim was scored by a metric the target's own shape had already gamed.
**Evidence now.** Real: the pilot distribution is visibly two-lobed. Unknown how the 200-prompt corpus
distributes — the hardening may shrink the floor mass (harder items rarely produce 10 identical
continuations).
**Disposition: fix now + control.** Candidate fix: pre-register a two-part treatment (degeneracy
classifier + regression on the non-degenerate part) or at minimum pre-register Spearman as co-primary
with R², and report the floor-mass fraction as a corpus property. The statistician lens owns this;
adopt its recommendation before freeze.

## 4. "The verbalized-confidence arm was a strawman"

**The death.** One frozen phrasing, zero-shot, greedy. Reviewers: "2503.14749 fine-tunes models to
verbalize calibrated confidence; you compared against the weakest possible verbal channel and
declared victory."
**Evidence now.** Partly answered: e3-0003 froze the strongest *simple* form deliberately and cites
the SFT variant as the stronger conceivable arm; pilot confirmed the known overconfidence pathology
(median 100). The honest scope is "beats *zero-shot* verbalized confidence."
**Disposition: accept openly + scope the claim.** The registration and any write-up must say
"zero-shot verbalized confidence" in the claim sentence, every time. An SFT-verbalization arm is a
follow-up, not this experiment. If the audit finds a cheap strengthening (e.g., a second elicitation
phrasing as robustness), consider it; do not let the claim's wording exceed the arm actually run.

## 5. "The OOD test tested extrapolation, not transfer"

**The death.** Hold out creative: training families' volumes top out at mid-band, creative sits at the
high extreme — the probe fails OOD not because it read a shortcut but because the held-out family's
target range was never spanned in training. REFUTED/ood-failure fires on a design artifact, and the
registry records a false kill. (Mirror image: family bands overlap so much the rotation proves
nothing.)
**Evidence now.** CORPUS.md § rotation-viability claims every leave-one-out training set spans
low/mid/high via within-family difficulty spread — a design assertion not yet verified against
measured volumes.
**Disposition: control.** Pre-register the check: for each rotation, report the training-set volume
range vs the held-out family's range; an OOD failure where the held-out range lies outside the trained
range is reported as *range-uncovered*, distinct from shortcut-collapse. The verdict branch should not
be allowed to call extrapolation failure a refutation without this distinction.

## 6. "Confirmed, and nobody cared — the corpus was a toy"

**The death.** Every number perfect; reviewers ask where TriviaQA / GSM8K / any deployed-relevance
task is, note the model is one 7B at 4-bit, and file the result under "cute." No refutation — worse:
indifference.
**Evidence now.** True by construction: 200 hand-authored short prompts, one small quantized model.
The contamination argument for hand-authoring is real and stands; the size/model limits are cost
facts.
**Disposition: accept openly + scope the claim.** The registration's claim sentence is about *this
model on this battery* — the maximal defensible claim, stated narrowly (the hostile-reviewer lens is
drafting that sentence). A multi-model, benchmark-family replication is the explicit follow-up if E3
confirms. The one cheap strengthening worth considering now: whether one dataset-derived family with
documented contamination risk is worth the external-validity purchase — a design decision for Vlad,
both options defensible.

## 7. "The verdict flipped inside its own sweep band"

**The death.** Verdict says confirmed at r2_ood_min = 0.05, refuted at 0.10; the pre-registered
"threshold-fragile" label fires; the result is technically honest and rhetorically dead.
**Evidence now.** Unknowable pre-run; the modest bars were chosen exactly because no literature anchor
exists.
**Disposition: accept openly.** This is the sweep discipline working. One addition worth making: the
registration should state *in advance* how a threshold-fragile outcome is reported and what follow-up
it triggers (wider corpus? more N?), so fragility has a pre-registered response instead of an
improvised one.

## 8. "Quantization objection"

**The death.** "You probed a 4-bit model; the geometry you read is quantization artifact." No cited
probe paper used a quantized host.
**Evidence now.** Weights are 4-bit; activations and the probed hidden state are fp16. The extraction
sanity check (20/20 top-1 agreement) shows the state drives the head faithfully. Whether
quantization *changes* linear readability is unknown and untestable on this hardware (the fp16 model
needs ~15 GB; the mini has 16 with an OS).
**Disposition: accept openly.** State it as a scope limit: "linear readability in the 4-bit-quantized
deployment form" — which is arguably the *more* deployment-relevant claim. Note the fp16 replication
as follow-up hardware permitting.

## Summary of pre-freeze actions this document demands

1. **Mandatory:** length-confound control pre-registered (§1); probe-vs-entropy clause added to the
   confirmation conditions (§2); target-distribution treatment decided (§3); range-uncovered vs
   shortcut-collapse distinction in the OOD branch (§5).
2. **Claim wording:** "zero-shot verbalized confidence" (§4); maximal-defensible-claim sentence
   adopted verbatim from the reviewer lens (§6).
3. **Reporting rules:** threshold-fragile response pre-stated (§7); quantization scope line (§8).

Anything the audit or rehearsal proves harmless gets a one-line refutation note here rather than
deletion — refuted scenarios are armor, not embarrassment.
