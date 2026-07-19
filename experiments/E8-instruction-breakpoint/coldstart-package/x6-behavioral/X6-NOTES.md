# X6 — Literature positioning notes

Companion to X6-DESIGN.md / X6-PROTOTYPE-SPEC.md. Records where X6 sits in the 2026 agentic-drift
subfield and the one-line differentiation from each nearest neighbor. Input source: campaign literature
sweep (task #23) + team-lead positioning brief. Bottom line: **the gap is confirmed novel — no cited work
operationalizes an explicit "R except when C" clause and tracks whether actions apply the exception when C
is FALSE, across turns, as the core DV — but the neighborhood is hot, so X6 must be positioned and, above
all, carry the omission/commission control arm (X6-DESIGN §1b) or a reviewer collapses it into SRD.**

## 1. The five neighbors and X6's one-line differentiation

1. **SRD — arXiv:2604.20911 (strongest quantitative anchor). VERIFIED against the PDF 2026-07-19** — title
   "Omission Constraints Decay While Commission Constraints Persist in Long-Context LLM Agents" (Yeran Gamage,
   USF). Confirmed numbers: Mistral Large 3 omission compliance **73%@turn5 → 33%@turn16**, commission **100%**,
   CMH χ²=147, **p<10⁻³³**; N=**4,416 trials, 12 models, 8 providers, six depths t∈{5,10,13,16,20,25}**;
   three-arm design (A no-dilution / B schema-dilution / C token-matched-padding) in a synthetic DevOps
   sandbox; compliance is **deterministic string-matching on formatting proxies** ("never use bullet points"),
   NOT an LLM judge.
   *Two facts that directly shape X6, both verified from the primary source, not the gloss:*
   - **The effect is a 3-of-4 SRD-susceptible CLUSTER with huge model variance, not a universal constant.**
     Figure 1: Mistral omission 73%→~20%; Nemotron Super 120B ~43%→~20%; Qwen 3.5 397B floored ~10% throughout;
     **Gemma 4 31B is an IMMUNE control at ~100% (near-zero violations, 363 trials).** So blanket-omission decay
     ranges from ~0% to ~80% depending on the model. **δ therefore CANNOT be transplanted from SRD's 73→33** —
     X6's pin `claude-sonnet-5` may sit anywhere in that range (Claude was not among the 12 identified). This
     is the decisive vindication of measuring the BLANKET arm in-harness (§1b) rather than assuming its level.
   - **SRD explicitly names X6's territory as its own untested next step.** Page 3, "Proxy Constraints": its
     constraints are *formatting proxies* deliberately chosen for deterministic scoring; the paper states
     verbatim that "**whether decay rates for semantically meaningful operational constraints match those we
     measure here is untested and is the direct next experiment**." SRD tests ONLY unconditional prohibitions/
     requirements — no `R except when C`. X6 occupies exactly that named gap AND adds the scoped-exception
     structure SRD never has.
   *Differentiation:* SRD's constraints are unconditioned blanket rules — no condition `C`, nothing to
   over-generalize; X6 tests a condition-gated exception wrongly applied when `C` is false, on semantically
   meaningful operational constraints.
   *Design consequence:* X6's BLANKET control arm (§1b) reproduces SRD's omission/commission split inside the
   same harness, so the scoped-exception effect is the increment `p_over − p_decay` over measured SRD-class
   decay, not a re-measurement of it. **δ-derivation:** freeze δ from the pilot's measured BLANKET dose-1→dose-3
   decay slope for `claude-sonnet-5` (the in-harness SRD analog), NOT from 73→33; require `p_over` to exceed the
   BLANKET arm by a margin larger than the BLANKET arm's own noise band. STD anchor for dose spacing: SRD's Safe
   Turn Depth = 10.6 [5.0,16.7] (Mistral) / 7.1 [5.0,10.5] (Qwen); X6's T3=9 intervening turns lands in that
   region by design.

2. **Constraint Drift — arXiv:2605.10481** (VERIFIED title: "Safe Multi-Agent Behavior Must Be Maintained,
   Not Merely Asserted: Constraint Drift in LLM-Based Multi-Agent Systems," Li et al.). Constraints erode
   through memory/delegation/communication/tool-use/audit/optimization in **MULTI-AGENT** systems.
   *Differentiation:* it characterizes *that* constraints erode via many channels in a multi-agent pipeline;
   X6 is **single-agent**, isolates ONE structural failure (scope-leak of a case-gated exception) with a
   paired control that subtracts general erosion out, and reads it off actions, not stated constraints.

3. **Governance Decay — arXiv:2606.22528** (VERIFIED title: "Governance Decay: How Context Compaction Silently
   Erases Safety Constraints in Long-Horizon LLM Agents," Chen; violations rise 0%→30%→59% after compaction).
   Compaction/summarization drops standing policies from context — a context-management (forgetting) mechanism.
   *Differentiation:* X6 is registered **operator-free and compaction-free**, and re-presents the exception
   verbatim at the scored turn (guard G), so the exception is provably still in front of the model — X6
   measures over-generalization *while the rule is present*, not policy loss from eviction. Governance Decay's
   compaction mechanism is exactly X5/H-COMPACT's territory, not X6's.

4. **"PhantomPolicy" — arXiv:2604.12177** (VERIFIED title: "Policy-Invisible Violations in LLM-Based Agents,"
   Wu & Gong — the informal name "PhantomPolicy" is ours; cite by real title). Agents violate policy because
   "facts needed for correct policy judgment are hidden at decision time" — a missing-information failure.
   *Differentiation:* the same guard-G separation applies — X6's exception is never hidden; the failure under
   test is mis-application of a fully-visible scoped rule, a reasoning/generalization error, not a
   missing-information error.

5. **Agent Drift — arXiv:2601.04170** (VERIFIED title: "Agent Drift: Quantifying Behavioral Degradation in
   Multi-Agent LLM Systems Over Extended Interactions," Rath; semantic/coordination/behavioral drift). Generic
   progressive degradation in **MULTI-AGENT** systems. *Differentiation:* X6 is single-agent, and its DV is not
   "does the agent get generally worse" but the specific paired event "applies `E_c` where `C` is
   false while still honoring `E_c` where `C` is true (guard D) and while the rule is visible (guard G)" —
   a targeted contrast that generic-degradation framing cannot express.

## 2. The confirmed-novel claim, stated precisely (for the writeup)

Not found anywhere in the cited neighborhood: an experiment that (a) establishes an explicit **`R except when
C`** scoped exception, (b) tracks whether the agent's **actions** apply the exception's treatment to cases
where **`C` is false** (RULE/NEW classes), (c) across increasing **turn-distance** as the dose, (d) with the
exception held **in context** throughout (no compaction), and (e) a **paired blanket-rule control arm** that
separates scope-leak from generic SRD-class decay. Each of the five neighbors touches one or two of these;
none combines (a)+(b)+(c)+(d)+(e). That combination is X6's contribution.

## 3. Positioning risks and the guard that neutralizes each

- **"This is just SRD."** → BLANKET control arm (§1b); the reported quantity is the separation `p_over −
  p_decay`, and X6 explicitly pre-registers the SRD-collapse outcome (§8 sub-case ii) as a real, reportable
  result rather than something to avoid.
- **"This is just compaction-forgetting (Governance Decay/PhantomPolicy)."** → guard G: exception re-presented
  verbatim at the scored turn, zero compaction; construction-time assert that the grant string is in the
  scored context.
- **"This is generic degradation (Agent Drift)."** → guard D conditioning: break events count only for
  trajectories that retained the exception on `c`; degradation that also breaks `c` lands in a separate stratum.
- **"The metric is a template/parse artifact (the Mission-X failure class)."** → guards A/B/C + paired
  positive/negative oracles + the (F,F)/(T,T) smoke cells routed to X-HUMAN (X6-DESIGN §4).

## 4. Verification status of these citations

- **SRD (2604.20911): VERIFIED against the arXiv abstract + full PDF, 2026-07-19** (this author). Title,
  authorship, the 73%→33% / commission-100% / p<10⁻³³ numbers, N=4,416/12-models/8-providers/6-depths, the
  three-arm design, the deterministic string-match measurement, the model-variance (Gemma immune control), and
  the paper's own "semantically meaningful operational constraints... untested... direct next experiment"
  statement are all confirmed from the primary source (§1). δ is now derived correctly (measured in-harness,
  SRD as range anchor, not the transplanted 73→33).
- **The other four (2605.10481 Constraint Drift, 2606.22528 Governance Decay, 2604.12177 PhantomPolicy,
  2601.04170 Agent Drift): title/abstract spot-checked** (see below). If any spot-check failed to resolve, it
  is flagged inline. Their headline mechanisms are used only for one-line differentiation, not for any X6
  numeric parameter, so they are lower-stakes than SRD — but a non-resolving ID must be corrected before
  writeup.
