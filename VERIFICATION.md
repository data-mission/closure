# Citation Verification Ledger

Every citation used in this repository, with its verification status. **A citation is not load-bearing until a human has read the primary source and flipped its status here.** Flipping one row (read the source, check that the claim attributed to it is accurate, PR the change with a one-line note) is the smallest complete contribution to this program.

**Provenance:** the underlying literature review was executed as structured search by AI research agents (two independent efforts, different decompositions of the concept, 2026-07), with per-paper closeness grading and mandatory reporting of negative queries. That process is good at coverage and bad at guarantees: IDs can be wrong, findings can be misread. Hence this ledger. Statuses:

- `unverified` — agent-reported; primary source not independently read.
- `abstract-checked` — an agent fetched and read the abstract directly; still not human-verified.
- `verified` — a named human has read the primary source and confirmed the attributed claim. (None yet.)
- `disputed` — readings conflict; see notes.

| Citation | Attributed claim (short) | Used in | Status |
|---|---|---|---|
| arXiv:2510.04933 "Geometry of Truth" | Layer-wise convergence detector, AUROC 0.959; velocity inert (d≈0.01); hallucinations converge ~layer 4.3 vs 8.2 | README, E1 | unverified |
| arXiv:2604.15400 (Akarlar) | Hallucination = early commitment to stable-wrong attractor; causal patching; 87.5% corruption | README, E1 | **disputed** — two independent readings differ (step-level bifurcation vs layer-KL trajectory); resolve at source |
| arXiv:2602.09825 (SAKED) | CLSS = 1−JSD(lens_l, lens_{l−1}); hallucination ↔ late-layer instability | README, E1 | unverified |
| arXiv:2507.06722 | Late-settling predictions → more hallucination | README, E1 | unverified |
| arXiv:2502.03199 | Token-wise cross-layer entropy improves decoding factuality | E1 | unverified |
| arXiv:2606.01033 (TriLens) | Per-layer logit-lens entropy trajectory detector | E1 | unverified |
| arXiv:2507.16488 (ICR Probe, ACL 2025) | ICR = JSD(Proj, Attn) per layer; peak AUROC 0.769 @ layer 11 | E1 | unverified |
| arXiv:2410.20210 | Saturation/rank-fixation events across layers; no hallucination link attached | E1 | unverified |
| arXiv:2410.11414 (ReDeEP) | RAG hallucination = FFN over-weights parametric knowledge | E1 | unverified |
| arXiv:2604.04743 "Hallucination Basins" | Task-dependent basin structure; geometry-aware steering | E1, prior-art | abstract-checked |
| arXiv:2508.14496, arXiv:2602.18671 | Energy-landscape accounts of hallucination | prior-art | unverified |
| arXiv:2605.24396 | Premature confidence at step level predicts flawed reasoning | E1 | unverified |
| arXiv:2603.01437 | Answer decodable pre-CoT (AUC>0.9); steering → confabulation | E1 | unverified |
| arXiv:2506.06194 (Marcotte et al., ICML 2025) | Conservation laws for *training* gradient flow of ResNets/Transformers | E2 | abstract-checked |
| arXiv:2502.12131 | Residual stream as dynamical system; cross-layer unit continuity | E2 | abstract-checked |
| arXiv:2605.14258 | Jacobian eigendecomposition; learned depth-wise spectral gradient | E2 | abstract-checked |
| arXiv:2602.09783 (ICML 2026) | Invariant-subspace necessity theorem (static) | E2 | abstract-checked |
| arXiv:2406.15927 (Semantic Entropy Probes) | Linear probes predict binarized SE class, incl. before generation | README, E3 | unverified |
| arXiv:2502.13329 (Ashok & May) | Conformal probes on input states predict behaviors + eventual confidence | E3 | unverified — an earlier automated summary of this paper was wrong and corrected during review; treat with care |
| arXiv:2405.15943 (Shai et al.) | Belief-state geometry linear in residual stream (small models, HMM data) | E3 | unverified |
| arXiv:2603.18940 | Entropy-trajectory shape predicts reliability (68.8% vs 46.8%, p=0.0005) | E3 | abstract-checked |
| arXiv:2604.06192 | Stepwise informativeness; lock-in/separability/saturation shapes | E3 | abstract-checked |
| arXiv:2502.21239 (Semantic Volume) | Gram-determinant dispersion metric, endpoint-only | E3 | abstract-checked |
| arXiv:2503.14749 | Possibly adjacent to E3's verbalized-confidence comparison | E3 pre-flight | unverified — flagged, not yet assessed |
| arXiv:2512.13478 (NRR-Core), arXiv:2601.19933 (NRR-Phi) | Architectural ambiguity preservation; H=0.91 vs 0.15 bits, 2-arm | E4 | unverified — single-author unreviewed preprints, high revision churn |
| arXiv:2405.16908 | Instructed hedging misaligns with intrinsic uncertainty | E4 | unverified |
| arXiv:2511.10453 | Enumerate-interpretations prompting (+11.75/+7.15) | E4 | unverified |
| arXiv:2511.01323, arXiv:2502.01523 | Coverage metrics; ~1.17 vs 2.19 interpretations/question | E4 | unverified |
| arXiv:2410.00382 | "Pretend to forget": final layer says forgotten, earlier layers still compute from content | E5 | unverified |
| arXiv:2506.08184 | Outdated/irrelevant annotations barely modulate retrieval | E5 | unverified |
| arXiv:2602.04288 (Contextual Drag) | Context errors bias later generations; feedback doesn't eliminate | E5 | abstract-checked |
| arXiv:2605.08563 (CCRM) | Contamination cascade ε₁/ε₀ = 7.1 on SWE-bench Verified | E5 | unverified — PDF partially unreadable during review |
| arXiv:2505.15392, arXiv:2412.06593 | Anchoring resists "ignore the anchor" instructions | E5 | unverified |
| arXiv:2605.30219 (BeliefTrack) | Contextual hijacking; RL reduces failed-isolation 70.9%, prompting doesn't | E5 | abstract-checked |
| arXiv:2406.19764 (Wilie et al.) | Belief-revision near floor across ~30 models; AGM as motivation only | E5 | abstract-checked |
| arXiv:2606.01435 | Deterministic freshness resolver beats LLM judgment +10–21pp | E5 | abstract-checked |
| XTrace (xtrace.ai) | Product page claims AGM ops at runtime | E5 | unverified — commercial marketing; no paper; assess before any priority claim |
| ReviseQA (OpenReview) | Possibly per-turn fact add/remove belief reassessment benchmark | E5 pre-flight | unverified — access blocked during review |
| arXiv:2503.01804 (SEM-CTRL) | MCTS decoding under answer-set-grammar constraints | E6 | unverified |
| arXiv:2601.21969 (Token-Guard, ICLR 2026) | Per-token self-checking decode pipeline | E6 | unverified |
| arXiv:2306.03081, arXiv:2504.13139 | Sequential Monte Carlo steering | E6 | unverified |
| arXiv:2510.25890 (ATLAS) | One constraint model → two layers, sequential, schema validity | E6 | abstract-checked |
| arXiv:2310.03714 (DSPy) | Compiles prompts/weights against metrics; no decode-time enforcement backend (checked vs 3.x) | E6 | unverified |
| arXiv:2507.20208 | Factor analysis on 60×44 model×benchmark matrix; low-rank structure | E0 | abstract-checked |
| arXiv:2605.08522 (MTMM) | Withdrawn by authors May 2026 citing fatal flaw | E0 | abstract-checked — verify the withdrawal notice itself |
| arXiv:2511.04703 | Construct-validity critique of LLM benchmarks | E0 | unverified |
| arXiv:2508.03665 | Neurosymbolic DbC layer for LLM agents | closure-vs-dbc | unverified |
| ContextCite (NeurIPS 2024); AttriBoT; ARC-JSD | Log-prob LOO context attribution | prior-art | unverified |
| Sclar et al. (ICLR 2024); ProSA | Prompt-formatting sensitivity, up to 76pp | prior-art | unverified |
| Farquhar et al. (Nature 2024) | Semantic entropy | prior-art | unverified |
| Alchourrón, Gärdenfors, Makinson (1985) | AGM belief revision: expansion/revision/contraction | E5 | unverified (classical; verify edition/formulation used) |
| arXiv:2511.04683 (zero-assumption citation auditing) | Independent 2025 protocol converging on this ledger's unverified-until-confirmed design | METHODOLOGY | abstract-checked |
| arXiv:2606.11217 (preregistration for AI-agent experiments) | Required fields: exact checkpoints, generation params, verbatim prompts, pilot disclosure; recommends OSF | METHODOLOGY, experiments run discipline | abstract-checked |
| Haroz 2022 (preregistration platform comparison, MetaArXiv) | Three criteria — independent timestamp, registry, persistence; bare GitHub fails, OSF/Zenodo pass | METHODOLOGY | unverified — PDF fetch failed; criteria corroborated via 2-3 secondary sources, phrasing is paraphrase |
| PRISMA 2020 + PRISMA-S | Search-reporting standard: verbatim strings per source, counts flow, eligibility criteria | METHODOLOGY | unverified — primary pages 403'd during review; snippet-sourced |
| COPE position on authorship and AI tools | AI cannot author; AI use disclosed; covers prose, not AI-executed search | METHODOLOGY | unverified — primary page 403'd; snippet-sourced |
| Nosek et al. 2018 (preregistration revolution, PNAS) | Confirmatory/exploratory distinction; inference criteria tied to hypotheses | METHODOLOGY | unverified — paywalled; corroborated via COS secondary sources |
| The Turing Way | Research-compendium structure prescription | METHODOLOGY | abstract-checked |
| IPCC calibrated uncertainty language | Confidence scale (very low–very high) from evidence + agreement | HYPOTHESES, METHODOLOGY | abstract-checked |
| Registered Reports (Center for Open Science) | Two-stage review, in-principle acceptance regardless of outcome | METHODOLOGY | abstract-checked |

Known systematic weaknesses of the review, inherited by this ledger: recency-weighted search (older relevant work may be under-represented); English-only; two flagged papers never assessed (rows above); one automated summary already caught wrong and corrected (2502.13329) — assume more exist until rows are verified.
