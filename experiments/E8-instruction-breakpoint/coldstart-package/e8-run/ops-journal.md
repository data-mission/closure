# E8 run — mission ops journal

Revised at every wake event (~3-5 min cadence). Improvements surfaced to the director only when weighted (impact × cost) AND verified (mechanism traced). Format: GOOD / WRONG / IMPROVEMENT CANDIDATES with status.

## GOOD (keep doing — proven this mission)
- Pre-staged verdict apparatus caught 2 verdict-corrupting bugs before any verdict code existed (`_oracle_result.json` glob poisoning; must_persist wrongly pruned) — both verified against source by lead.
- Equivalence-gated parallelization: no derived tool touched real data before byte-level output equivalence (84/84 booleans, verified independently by lead AND author — double-verified twice after a log-only change).
- Adversarial re-verification caught the lead's own false-greens twice (truncated patch hunk; failed kill with lying counter). Verify-by-result is load-bearing, including against the manager.
- Convergent independent analysis (lead + builder reached serialization conclusion separately within minutes) — redundant analysts on resource decisions pay off.
- Role-by-competence: dashboard owner replaced on failure, demoted agent retained in the lane it performs well. Precision beats blanket punishment.
- Event-driven orchestration: tripwires that exit-on-state-change; zero polling from the lead's loop.

## WRONG (each cost real time — guards adopted)
- 3h silent scoring phase launched without pre-flight script/data assessment (guard: 8-step pre-flight, now in /mission-ops skill).
- Micro-benchmark transferred across contexts was ~4x optimistic → false "82-100% done" + a deadline armed on a wrong model (guard: empirical-rate re-derivation; assumption-tagged ETAs).
- Parallel-everything on a memory-bandwidth-bound box → thrash, ~0.5 fam/min total (guard: serialize axes; measure system throughput, not process counts).
- `pkill -f` pattern killed the lead's own tripwire (guard: kill by exact PID — in skill traps table).
- zsh unsplit-PID kill silently failed while its verification check false-greened (guard: verify with independent method, ps not pgrep-count).
- Intervention broadcast gaps ×3 → agents burned cycles investigating the lead's own kills (guard: broadcast to ALL watchers + INTERVENTIONS.log on the machine, see below).
- Dashboard split-ownership + publish-step skipping → director stared at stale numbers twice (guard: single owner, publish-first charter, adversarial auditor, replacement executed).
- Agent resident loops die on turn boundaries (architecture) — repeated idle-drift (guard: bounded windows, foreground sleeps, piggyback pokes on events).

## IMPROVEMENT CANDIDATES (weighted: impact/cost; status)
1. **INTERVENTIONS.log on the target machine** — HIGH/trivial; VERIFIED mechanism (watchers check it before alarming → phantom-anomaly class dies). STATUS: implemented this mission (2026-07-18 04:50Z).
2. **Filter-stage calibration phase** (like Stage-2's 10-min measured calibration, absent from filter_stage.py) — HIGH/low for future registrations; the entire 3h-black-box pain was this gap. STATUS: propose for next experiment's apparatus; cannot retrofit this run (frozen).
3. **GPU/MPS scoring path** — potentially 5-20x on this class of workload; BLOCKED for this run (device=cpu is inside the frozen config hash; changing it voids registration) and numerics would need revalidation. STATUS: candidate for next experiment's pre-registration only; needs a registered CPU-vs-MPS equivalence study first.
4. **Per-family progress files in parallel scorer** (parent rollup lag fix) — MED/low; built and smoke-tested by builder, promotes after equivalence smoke. STATUS: in flight.
5. **Instrumented oracle** — MED/low; built, statically verified; runtime-equivalence in quiet window. STATUS: in flight.
6. **Agent-runtime pattern for residency** — MED/zero marginal (codified): bounded windows + event piggyback, foreground sleeps. STATUS: adopted + in skill.

## Non-improvements (rejected with reason — so they don't get re-proposed)
- Raising torch threads per worker: rejected — changes fp reduction order, can flip borderline NLI scores at the 0.7 threshold; frozen numerics win over speed.
- Killing A3 serial to free 2 cores: rejected — registered-script provenance + most-complete computation + Gate B serial side; cheapest insurance in the run.

## Update 05:02Z
- MEASURED (passive, builder): τ_assert ≈ 18.1s/call at full box occupancy; 0.66 fam/min 4-wide. KEY INSIGHT: no uncontended regime exists during scoring — the box is always at full occupancy, so optimistic per-call figures (3.9s) never apply. Serialized filter-scoring wall ≈ 9.9h total (A3 2.5 / A2 2.9 / A1 4.5).
- Caught before propagation: builder misread my A2 kill as "clean completion" — intervention-log mandate extended to ALL agents (was only watchers; my gap).
- Dashboard owner's 9-10h paracheck extrapolation corrected (forgot 4-way sharding division) before publication.
- DEFERRED DECISION with criteria: kill-or-keep A3 serial at the Stage-2-scoring boundary (≥85% of 17.7 CPU-h → keep; else kill, Gate B downgraded-and-disclosed).
