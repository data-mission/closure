# Analysis code (as run)

- `run_arms.py` — the lean driver: generations (arms A/B), contraction (arm C), scoring, statistics. Phase 4 crashed on a numpy-bool JSON serialization; all 180 score rows were already banked (see VERDICT §4 deviation 4).
- `regen_summary.py` — regenerated `results-summary.json` from the banked score rows via the frozen stats functions after that crash.
- `run_exploratory_v2.py` — post-verdict analyses: per-item rescore (exhaustive cross-check vs banked scores), Arm-C regeneration check, threshold sensitivity sweep. Memoized directional NLI pair-cache under the unmodified frozen harness; exactness gates precede any write.

Scripts are as-run and contain absolute paths from the run machine; re-running requires the harness package (`harness/`, uv project) and adjusting the two path constants at the top of each script.
