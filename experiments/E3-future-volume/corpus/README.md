# E3 candidate corpus

`candidates.jsonl` — 200 hand-authored candidate prompts across 5 task families (`arithmetic`, `factual`,
`deduction`, `enumeration`, `creative`), serving the leave-one-family-out OOD rotation of `e3-0001`, the N=10
volume target of `e3-0002`, and the answerable-subset AUROC of `e3-0003`. Design record: `../CORPUS.md`.

**STATUS: PROPOSED — binds nothing until a human approves it** (`e3-0004` freeze boundary; E0 `PLAN.md` step 6).

Fields (one JSON object per line): `id`, `family`, `prompt`, `gold` (canonical answer, or `null` for the
open families `enumeration`/`creative`), `difficulty` (1–3, anchored per family), `expected_diversity`
(low/mid/high — a design annotation, NOT a measurement), `provenance` (hand-authored + dataset format styled
after), `answerable` (bool; 126 of 200 are true — the AUROC subset).

**No spike overlap.** No prompt equals or near-duplicates any of the 20 throwaway prompts in
`../spike/run_spike.py`. Checked at assembly: zero exact matches; max token-set Jaccard vs any spike prompt =
0.50, and that maximum is the generic `What is the <X> of <Y>?` frame with no shared content words. Assembly also
asserts no duplicate prompts and recomputes every `arithmetic` gold from scratch.
