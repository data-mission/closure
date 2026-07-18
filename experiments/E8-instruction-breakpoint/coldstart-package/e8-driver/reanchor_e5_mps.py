"""E5 RE-ANCHOR on the certified MPS instrument — re-score the banked E5 arms on GPU.

WHY THIS FILE EXISTS (not just `run_e5.py --score-only`): the registered E5 baseline was scored on
CPU; its banked generation log (arms-log.jsonl) carries the CPU config_hash 6dbe47a8…. Re-anchoring
means re-scoring those SAME banked A/B generations on the MPS instrument so E8-GPU results are
comparable to the E5 baseline on the SAME device. Two things block a plain `run_e5.py --score-only`
on MPS:

  1. DEVICE: run_e5.py builds NLIScorer() at the frozen device (cpu, config.py:36) and has no
     device flag; its __init__ calls use_deterministic_algorithms(True) unconditionally (nli.py:62),
     which can hard-fail on MPS. We construct the scorer on MPS with the SAME measured monkeypatch
     gpu_probe.build_mps_scorer uses (gpu_probe.py:54-84), recording whether warn_only was needed.
  2. CONFIG-HASH FILTER: run_e5.score_from_log filters banked records by
     `rec.config_hash == config_hash()` (run_e5.py:549). Under MPS, config_hash() becomes c7be2036…
     ≠ the banked 6dbe47a8…, so it would match ZERO records and score nothing. We therefore call
     run_e5's scoring with the BANKED (CPU) hash as the current hash, exactly as the frozen scoring
     path intends: the scorer's DEVICE changes, the config-hash that KEYS the banked log does not
     (it identifies the generations, which are unchanged; only the instrument re-scoring them moves
     to GPU). This is the same principle as gpu_probe (device-only variable) and batched_scorer
     (composition-only variable): we hold the generation identity fixed and vary only the scorer.

This module REUSES run_e5's scoring/stats verbatim — load_tasks, load_pruned_index, read_log,
score_from_log, compute_stats, verdict_numbers_md — so the numbers are produced by the SAME code as
the CPU baseline, only the scorer's device differs. No re-implementation of scoring logic.

OUTPUT: an MPS results-summary + verdict-numbers, plus a DELTA block vs the banked CPU
results-summary.json (per-arm pooled contamination, mean completeness, pairwise z verdicts). The
delta is the re-anchor evidence: if the MPS baseline matches CPU within noise and no z-test verdict
flips, the E5↔E8 chain holds on the GPU instrument.

CLI:
  cd ~/repos/closure/harness && PATH="$HOME/.local/bin:$PATH" \
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run python -u ~/e8-driver/reanchor_e5_mps.py \
      --corpus ~/repos/closure/experiments/E5-reclosure/corpus/tasks.jsonl \
      --arms-log <banked arms-log.jsonl> \
      --pruned-items <pruned-items.json> \
      --banked-summary <banked results-summary.json> \
      --out-dir ~/e8-run/E5-reanchor-mps --device mps

This scores 60 tasks × 3 arms (A/B from the banked log, C via contraction) — minutes on MPS. It runs
NO generation and needs NO freeze gate (it produces no new API data — same rule as run_e5
--score-only, run_e5.py:1107-1112).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

DRIVER = Path(__file__).resolve().parent
sys.path.insert(0, str(DRIVER))
from common import atomic_write_json  # noqa: E402


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(msg: str) -> None:
    print(f"[{_ts()}] {msg}", flush=True)


# --------------------------------------------------------------------------- numpy-safe JSON coercion
def _jsonable(obj):
    """Recursively coerce numpy scalars → python scalars so json.dump can't crash on them.

    compute_stats/two_proportion_ztest values come from scipy (_sp.norm.sf → numpy.float64), so
    p_value/p_corrected are numpy floats and `significant = min(1.0, p*bonf) < alpha` is a
    numpy.bool_ whenever p*bonf < 1.0 (min returns the numpy float, comparison stays numpy). A
    numpy.bool_/float64 reaching common.atomic_write_json's json.dump raises
    'Object of type bool is not JSON serializable' — the crash that lost an 18-min GPU pass.
    common.atomic_write_json takes no default= encoder, so we coerce the dict BEFORE writing.
    Uses .item() on any object exposing it (numpy scalars), which returns the native python type."""
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if obj is None or type(obj) in (bool, int, float, str):
        return obj  # EXACT python scalars pass through. type() not isinstance: np.float64 subclasses
                    # float and np.bool_ does not subclass bool, so an isinstance check would leak
                    # np.float64 through uncoerced — type() forces every numpy scalar to the .item() path.
    item = getattr(obj, "item", None)  # numpy scalars (np.bool_, np.integer, np.floating) expose .item()
    if callable(item):
        try:
            return item()  # -> native python bool/int/float
        except Exception:  # noqa: BLE001
            pass
    return obj  # anything else json handles or will surface; stats scalars are all covered above


# --------------------------------------------------------------------------- pre-scoring sanitize
def _sanitize_output(out_dict: dict, ndocs: int) -> tuple[dict, int]:
    """VERBATIM run_arms.py:66-73 sanitize logic: a claim citing a source index outside [0, ndocs)
    has no valid support and is stripped (identically in every arm, BEFORE contraction and scoring).
    Returns (sanitized_output, n_stripped). ndocs = len(arm_source_block(task)) = len(sources)+1.

    This is the disclosed 2026-07-15 pre-scoring repair the REGISTERED run_arms.py applied and that
    run_e5.score_from_log (which reanchor reuses) omits — the omission is exactly what raised
    grounding.py:36 on the banked hallucinated citations. Applying it here scores the SAME sanitized
    inputs the registered CPU run scored (the whole point of the re-anchor)."""
    good = [c for c in out_dict["claims"] if all(0 <= i < ndocs for i in c["source_ids"])]
    n_bad = len(out_dict["claims"]) - len(good)
    return {"claims": good, "conclusion": out_dict["conclusion"]}, n_bad


def sanitize_records(records: list, tasks: list, banked_hash: str, arms=("A", "B")):
    """Sanitize the banked A/B output rows IN PLACE before score_from_log sees them, mirroring
    run_arms.py:118-119 (sanitize A and B; Arm C is contracted from sanitized A inside
    score_from_log, so it inherits the repair — matching the registered flow). Only rows at the
    banked config_hash with a usable output are touched. Returns the sanitation register
    {"task_id/arm": n_stripped} for the acceptance gate + disclosure.

    ndocs per task = len(sources) + 1 (the not_A document), == run_e5.arm_source_block length ==
    run_arms.docs_for length. Uses run_e5's parsed Task for source counts."""
    ndocs_by_task = {t.task_id: len(t.sources) + 1 for t in tasks}
    register: dict[str, int] = {}
    for rec in records:
        if rec.get("config_hash") != banked_hash or rec.get("error"):
            continue
        arm = rec.get("arm")
        if arm not in arms:
            continue  # C rows (if any) are ignored; score_from_log rebuilds C from sanitized A
        out = rec.get("output")
        if not isinstance(out, dict) or "claims" not in out:
            continue
        ndocs = ndocs_by_task.get(rec["task_id"])
        if ndocs is None:
            continue
        sanitized, n_bad = _sanitize_output(out, ndocs)
        if n_bad:
            rec["output"] = sanitized  # in-place: score_from_log reads rec["output"]
            register[f"{rec['task_id']}/{arm}"] = n_bad
    return register


def build_mps_scorer(device: str):
    """FROZEN NLIScorer on `device` via the gpu_probe monkeypatch (gpu_probe.py:54-84). Returns
    (scorer, warn_only_used). device='cpu' builds it verbatim (no patch)."""
    import torch
    from closure_harness.config import CONFIG

    state = {"warn_only_used": False}
    if device == "cpu":
        from closure_harness.nli import NLIScorer
        return NLIScorer(config=CONFIG.nli), state["warn_only_used"]

    orig = torch.use_deterministic_algorithms

    def patched(mode, *a, **kw):
        try:
            return orig(mode, *a, **kw)
        except Exception as e:  # noqa: BLE001
            state["warn_only_used"] = True
            _log(f"[reanchor] use_deterministic_algorithms strict rejected on {device} "
                 f"({type(e).__name__}: {e}); retrying warn_only=True")
            return orig(mode, warn_only=True)

    torch.use_deterministic_algorithms = patched
    try:
        from closure_harness.nli import NLIScorer
        scorer = NLIScorer(config=replace(CONFIG.nli, device=device))
    finally:
        torch.use_deterministic_algorithms = orig
    return scorer, state["warn_only_used"]


def _delta_vs_banked(mps_stats: dict, banked_summary_path: Path) -> dict:
    """Diff the MPS re-anchor stats against the banked CPU results-summary.json. Reports per-arm
    pooled-contamination + mean-completeness deltas and whether any pairwise z verdict flipped."""
    if not banked_summary_path or not banked_summary_path.exists():
        return {"available": False, "reason": f"banked summary not found: {banked_summary_path}"}
    banked = json.loads(banked_summary_path.read_text())
    b_stats = banked.get("stats", banked)  # tolerate either wrapped or bare stats

    arm_delta = {}
    for arm in ("A", "B", "C"):
        m = mps_stats.get("arm_rates", {}).get(arm) or {}
        b = (b_stats.get("arm_rates", {}) or {}).get(arm) or {}
        def d(k):
            mv, bv = m.get(k), b.get(k)
            return (mv - bv) if (isinstance(mv, (int, float)) and isinstance(bv, (int, float))) else None
        arm_delta[arm] = {
            "contamination_pooled_mps": m.get("contamination_pooled"),
            "contamination_pooled_cpu": b.get("contamination_pooled"),
            "contamination_delta": d("contamination_pooled"),
            "mean_completeness_mps": m.get("mean_completeness"),
            "mean_completeness_cpu": b.get("mean_completeness"),
            "mean_completeness_delta": d("mean_completeness"),
        }

    verdict_flips = []
    for pair, mzt in (mps_stats.get("pairwise_ztests", {}) or {}).items():
        bzt = (b_stats.get("pairwise_ztests", {}) or {}).get(pair)
        if mzt and bzt and (mzt.get("significant") != bzt.get("significant")):
            verdict_flips.append({
                "pair": pair,
                "cpu_significant": bzt.get("significant"),
                "mps_significant": mzt.get("significant"),
                "cpu_p_corrected": bzt.get("p_value_corrected"),
                "mps_p_corrected": mzt.get("p_value_corrected"),
            })

    return {
        "available": True,
        "arm_delta": arm_delta,
        "pairwise_verdict_flips": verdict_flips,
        "n_verdict_flips": len(verdict_flips),
        "chain_holds": len(verdict_flips) == 0,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="E5 re-anchor on the MPS instrument (score-only, gateless)")
    ap.add_argument("--corpus", required=True, type=Path,
                    help="E5 frozen corpus tasks.jsonl (experiments/E5-reclosure/corpus/tasks.jsonl)")
    ap.add_argument("--arms-log", required=True, type=Path,
                    help="banked E5 generation log (arms-log.jsonl with A/B/C rows, CPU config_hash)")
    ap.add_argument("--pruned-items", required=True, type=Path, help="pruned-items.json register")
    ap.add_argument("--banked-summary", type=Path, default=None,
                    help="banked CPU results-summary.json to delta against (optional but recommended)")
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--device", type=str, default="mps")
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--banked-config-hash", type=str, default=None,
                    help="config_hash that keys the banked log; default = auto-detect from the log's "
                         "first row (the CPU hash 6dbe47a8…). This keys record selection; the SCORER "
                         "device is --device, independent of this.")
    args = ap.parse_args()

    from common import set_cpu_threads
    set_cpu_threads(args.threads)

    import closure_harness.run_e5 as e5  # reuse the frozen scoring/stats verbatim

    # Auto-detect the banked hash from the log (the CPU hash the generations were stamped with).
    banked_hash = args.banked_config_hash
    if banked_hash is None:
        with args.arms_log.open() as fh:
            for line in fh:
                line = line.strip()
                if line:
                    banked_hash = json.loads(line).get("config_hash")
                    break
    if not banked_hash:
        raise SystemExit("could not determine banked config_hash (empty log or missing field); "
                         "pass --banked-config-hash explicitly")

    from closure_harness.config import config_hash as live_config_hash
    _log(f"[reanchor] banked(log) config_hash={banked_hash[:12]} | live config_hash="
         f"{live_config_hash()[:12]} | scoring device={args.device}")

    tasks = e5.load_tasks(args.corpus)
    pruned = e5.load_pruned_index(args.pruned_items)
    records = e5.read_log(args.arms_log)
    _log(f"[reanchor] {len(tasks)} tasks, {len(records)} banked log rows, "
         f"{len(pruned)} pruned items")

    # PRE-SCORING SANITIZE (the registered run_arms.py repair that run_e5.score_from_log omits):
    # strip hallucinated out-of-range citations from A/B outputs BEFORE contraction/scoring.
    sanitation_register = sanitize_records(records, tasks, banked_hash)
    _log(f"[reanchor] sanitize: {len(sanitation_register)} arm-outputs touched "
         f"({sum(sanitation_register.values())} claims stripped)")

    # ACCEPTANCE GATE (team-lead 2026-07-18): the emitted register MUST match the banked register
    # EXACTLY (same arm-outputs, same per-output counts). Exact match = instrument-identity evidence;
    # ANY mismatch = STOP before scoring (the reanchor is repairing differently than the registered
    # run did, which voids the comparison). Banked register read from --banked-summary.
    banked_register = None
    if args.banked_summary and args.banked_summary.exists():
        banked_register = (json.loads(args.banked_summary.read_text()) or {}).get("sanitation_register")
    if banked_register is None:
        _log("[reanchor] *** STOP: no sanitation_register in --banked-summary to gate against. "
             "Pass the banked results-summary.json (which carries sanitation_register) so the "
             "register match can be verified before scoring. Refusing to proceed.")
        raise SystemExit(2)
    if sanitation_register != banked_register:
        only_reanchor = {k: v for k, v in sanitation_register.items() if banked_register.get(k) != v}
        only_banked = {k: v for k, v in banked_register.items() if sanitation_register.get(k) != v}
        _log("[reanchor] *** STOP: sanitation register MISMATCH vs the banked register — the reanchor "
             "is repairing DIFFERENTLY than the registered run, which voids the E5-anchor comparison. "
             f"reanchor-only/differs: {only_reanchor} | banked-only/differs: {only_banked}. "
             "Reporting to lead; NOT proceeding to scoring.")
        raise SystemExit(3)
    _log(f"[reanchor] sanitation register MATCHES banked exactly ({len(sanitation_register)} entries) "
         "— instrument-identity confirmed; proceeding to scoring")

    t0 = time.time()
    scorer, warn_only = build_mps_scorer(args.device)
    _log(f"[reanchor] scorer built on {args.device}; warn_only needed: {warn_only}")

    # KEY: pass the BANKED hash as the current hash so score_from_log selects the banked records.
    # The scorer's device is MPS; the config-hash that identifies the generations is unchanged.
    scores, error_counts = e5.score_from_log(records, tasks, pruned, scorer, banked_hash)

    # CRASH-SAFETY: the ~18-min MPS scoring pass is the expensive, irreplaceable work. Persist the
    # raw scores to a SIDECAR the instant scoring completes — BEFORE stats/summary — so a late-stage
    # serialization/stats crash can never again cost the GPU pass (the previous round lost it exactly
    # here). The sidecar is numpy-coerced too. A re-run can reload this instead of re-scoring.
    args.out_dir.mkdir(parents=True, exist_ok=True)
    scores_sidecar = {
        "scores": e5._scores_payload(scores),
        "error_counts": error_counts,
        "banked_config_hash": banked_hash,
        "device": args.device,
        "scored_at": _ts(),
    }
    atomic_write_json(args.out_dir / "e5-reanchor-scores-raw.json", _jsonable(scores_sidecar))
    _log(f"[reanchor] scores sidecar written ({len(scores)} arm-scores) — GPU pass is now safe")

    stats_result = e5.compute_stats(scores)
    elapsed = time.time() - t0

    summary = {
        "reanchor": "E5 baseline re-scored on MPS instrument",
        "device": args.device,
        "banked_config_hash": banked_hash,
        "live_config_hash": live_config_hash(),
        "warn_only_needed": warn_only,
        "scores": e5._scores_payload(scores),
        "stats": stats_result,
        "error_counts": error_counts,
        "sanitation_register": sanitation_register,
        "sanitation_register_matches_banked": True,  # gated above; scoring only runs on exact match
        "delta_vs_banked_cpu": _delta_vs_banked(stats_result, args.banked_summary),
        "elapsed_s": round(elapsed, 1),
    }
    # numpy-coerce the WHOLE summary before the atomic write (stats carry numpy scalars from scipy).
    atomic_write_json(args.out_dir / "e5-reanchor-mps-summary.json", _jsonable(summary))
    (args.out_dir / "e5-reanchor-VERDICT-numbers.md").write_text(
        e5.verdict_numbers_md(stats_result, error_counts), encoding="utf-8")

    d = summary["delta_vs_banked_cpu"]
    _log("[reanchor] RESULT " + json.dumps({
        "device": args.device,
        "arm_A_contam": stats_result["arm_rates"]["A"]["contamination_pooled"],
        "arm_B_contam": stats_result["arm_rates"]["B"]["contamination_pooled"],
        "arm_C_contam": stats_result["arm_rates"]["C"]["contamination_pooled"],
        "errors": error_counts,
        "verdict_flips_vs_cpu": d.get("n_verdict_flips"),
        "chain_holds": d.get("chain_holds"),
        "elapsed_s": summary["elapsed_s"],
    }))
    _log(f"[reanchor] wrote {args.out_dir/'e5-reanchor-mps-summary.json'}")
    if d.get("available") and not d.get("chain_holds"):
        _log("[reanchor] *** WARNING: a pairwise z-test verdict FLIPPED vs the CPU baseline — "
             "the E5↔E8 chain does NOT hold cleanly on MPS. Investigate before proceeding.")


if __name__ == "__main__":
    main()
