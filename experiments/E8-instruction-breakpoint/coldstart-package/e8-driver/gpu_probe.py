"""E8 GPU/MPS EQUIVALENCE PROBE — certification data, NOT part of the registered run.

Question: does scoring the A3 filter outputs on Apple MPS (GPU) produce the SAME per-item
booleans as the registered CPU path? If yes (zero flips), the director may consider a disclosed
amendment to score A2/A1 filters on GPU (~5-20× faster). If any flip, the registered CPU path
stands and E9 designs on real data.

METHOD (controlled variable = device ONLY):
- Reuse the FROZEN NLIScorer verbatim, constructed with dataclasses.replace(CONFIG.nli,
  device="mps"). Same checkpoint, revision, batch_size(16), max_length(512), entail/contradict
  index resolution, the (entail-contradict+1)/2 scalar, bidirectional max-over-sources — every
  numeric choice identical to CPU. The ONLY difference is torch.device. This is exactly what a
  GPU-scored run would do, so equivalence here == equivalence there.
- The frozen NLIScorer.__init__ calls torch.use_deterministic_algorithms(True) unconditionally.
  MPS lacks deterministic kernels for some ops and will RAISE. We monkeypatch that call to
  warn_only=True FOR THIS PROBE PROCESS ONLY (never touches the frozen file), and RECORD whether
  the warn_only path was actually exercised — the probe MEASURES nondeterminism, it does not
  assume it away. We also score every item TWICE on MPS to test self-consistency (a run-to-run
  flip on the SAME device is a harder failure than a CPU/MPS delta).

COMPARISON: per (draw, must_change item) we compute the raw scalar float + the boolean
(float >= assert_threshold) on MPS, twice, and diff booleans against the CPU ground truth
(_smoke/serial_gt.json for the 4 smoke families; extendable to paracheck shards / serial report).
Report: flip count, flip rate, score-delta distribution (esp. |Δ| for items near the 0.7
threshold), and MPS self-consistency (run1 vs run2 booleans + max |Δ|).

CONSTRAINTS honored by the caller (launch with `nice -n 19`, ONE process, throttle if the live
run's fam/min drops >10%). This file does NOT touch the live run, frozen files, or any key.
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
import filter_stage  # noqa: E402  (reuse top_level_per_family + gen indexing shape)
from common import load_jsonl, atomic_write_json  # noqa: E402


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(msg: str) -> None:
    print(f"[{_ts()}] {msg}", flush=True)


def build_mps_scorer():
    """Construct the FROZEN NLIScorer on MPS. Returns (scorer, deterministic_warn_only_used:bool).

    Monkeypatches torch.use_deterministic_algorithms so the frozen constructor's unconditional
    True call cannot hard-fail on MPS; records whether warn_only was actually needed."""
    import torch
    from closure_harness.config import CONFIG

    orig = torch.use_deterministic_algorithms
    state = {"warn_only_used": False, "raised_without_warn": False}

    def patched(mode, *a, **kw):
        # First try the strict call the frozen code intends; if MPS rejects it, retry warn_only
        # and record that we had to. This MEASURES whether MPS can be deterministic here.
        try:
            return orig(mode, *a, **kw)
        except Exception as e:  # noqa: BLE001 — we are probing exactly this failure
            state["raised_without_warn"] = True
            state["warn_only_used"] = True
            _log(f"[probe] use_deterministic_algorithms strict rejected on MPS ({type(e).__name__}: "
                 f"{e}); retrying warn_only=True")
            return orig(mode, warn_only=True)

    torch.use_deterministic_algorithms = patched
    try:
        from closure_harness.nli import NLIScorer
        mps_cfg = replace(CONFIG.nli, device="mps")
        scorer = NLIScorer(config=mps_cfg)
    finally:
        torch.use_deterministic_algorithms = orig  # restore, keep the probe hermetic
    return scorer, state


def build_cpu_scorer():
    from closure_harness.config import CONFIG
    from closure_harness.nli import NLIScorer
    return NLIScorer(config=CONFIG.nli)  # device pinned "cpu" in frozen config


def index_gens(gen_log: Path, config_hash: str) -> dict:
    """(task_id, filter_state, draw_index) -> output — same selection as filter_stage.score_draws."""
    gens = {}
    for r in load_jsonl(gen_log):
        if r.get("config_hash") == config_hash and not r.get("error") and "filter_state" in r:
            gens[(r["task_id"], r["filter_state"], r["draw_index"])] = r["output"]
    return gens


def score_all(scorer, top, gens, threshold, n_draws, tag):
    """Return {(fam, state, draw, item_idx): (raw_float, bool)} using the FROZEN per-item path.

    Mirrors filter_stage.score_draws exactly but ALSO captures the raw scalar float (score_draws
    keeps only the bool) so we can measure deltas near the threshold. parse_output + _asserted_text
    are the frozen functions; scalar(premises, concl) is the frozen __call__."""
    from closure_harness.schema import parse_output
    from closure_harness.outcomes import _asserted_text

    result = {}
    fams = sorted(top.keys())
    total = len(fams)
    for fi, fam in enumerate(fams, 1):
        task = top[fam]
        mc = task["must_change"]
        for state in ("assumption", "correction"):
            for d in range(n_draws):
                g = gens.get((task["task_id"], state, d))
                if g is None:
                    continue
                o = parse_output(g)
                premises = _asserted_text(o)
                for i, concl in enumerate(mc):
                    raw = float(scorer(premises, concl))          # FROZEN scalar, raw float
                    result[(fam, state, d, i)] = (raw, raw >= threshold)
        _log(f"[probe {tag}] {fi}/{total} families scored")
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description="E8 GPU/MPS equivalence probe (NOT the registered run)")
    ap.add_argument("--tasks", required=True, type=Path)
    ap.add_argument("--gen-log", required=True, type=Path)
    ap.add_argument("--cpu-gt", type=Path, default=None,
                    help="optional CPU ground-truth serial_gt.json (booleans) to diff against")
    ap.add_argument("--families", type=str, default=None,
                    help="comma-separated family ids to restrict to (e.g. the 4 smoke families)")
    ap.add_argument("--out", required=True, type=Path, help="probe result JSON")
    ap.add_argument("--n-draws", type=int, default=3)
    ap.add_argument("--threads", type=int, default=2, help="CPU threads for tokenization")
    args = ap.parse_args()

    from common import set_cpu_threads
    set_cpu_threads(args.threads)  # tokenization is CPU; keep it modest (nice -n 19 caller too)
    from closure_harness.config import CONFIG, config_hash
    CH = config_hash()
    threshold = CONFIG.outcome.assert_threshold

    tasks = [json.loads(l) for l in args.tasks.read_text().splitlines() if l.strip()]
    top = filter_stage.top_level_per_family(tasks)
    if args.families:
        keep = set(args.families.split(","))
        top = {f: t for f, t in top.items() if f in keep}
    gens = index_gens(args.gen_log, CH)
    _log(f"[probe] {len(top)} families, threshold={threshold}, config_hash={CH[:12]}")

    # Build MPS scorer (records whether warn_only was needed).
    t0 = time.time()
    mps_scorer, det_state = build_mps_scorer()
    _log(f"[probe] MPS scorer built; deterministic warn_only needed: {det_state['warn_only_used']}")

    # MPS run 1 + run 2 (self-consistency).
    mps1 = score_all(mps_scorer, top, gens, threshold, args.n_draws, "mps1")
    mps2 = score_all(mps_scorer, top, gens, threshold, args.n_draws, "mps2")

    # MPS self-consistency: same device, run-to-run.
    keys = sorted(mps1.keys() & mps2.keys())
    self_bool_flips = sum(1 for k in keys if mps1[k][1] != mps2[k][1])
    self_max_delta = max((abs(mps1[k][0] - mps2[k][0]) for k in keys), default=0.0)

    # CPU ground truth: build it fresh on CPU for the SAME items (authoritative), and also
    # optionally cross-check against a provided serial_gt.json (which stores per-family a/c bools).
    _log("[probe] building CPU ground truth (device=cpu) for the same items ...")
    cpu_scorer = build_cpu_scorer()
    cpu = score_all(cpu_scorer, top, gens, threshold, args.n_draws, "cpu")

    ckeys = sorted(cpu.keys() & mps1.keys())
    flips = [k for k in ckeys if cpu[k][1] != mps1[k][1]]
    deltas = [abs(cpu[k][0] - mps1[k][0]) for k in ckeys]
    # near-threshold: items whose CPU raw is within 0.05 of 0.7 (the borderline zone)
    near = [k for k in ckeys if abs(cpu[k][0] - threshold) <= 0.05]
    near_flips = [k for k in near if cpu[k][1] != mps1[k][1]]

    def dist(xs):
        if not xs:
            return {}
        s = sorted(xs)
        n = len(s)
        return {"n": n, "max": max(s), "mean": sum(s) / n,
                "p50": s[n // 2], "p95": s[min(n - 1, int(n * 0.95))],
                "gt_1e-6": sum(1 for x in s if x > 1e-6),
                "gt_1e-4": sum(1 for x in s if x > 1e-4),
                "gt_1e-2": sum(1 for x in s if x > 1e-2)}

    report = {
        "probe": "GPU/MPS equivalence — device-only variable vs frozen CPU path",
        "config_hash": CH, "assert_threshold": threshold,
        "n_families": len(top), "n_items_compared": len(ckeys),
        "device_note": "MPS via dataclasses.replace(CONFIG.nli, device='mps'); frozen file untouched",
        "deterministic": {
            "warn_only_needed_on_mps": det_state["warn_only_used"],
            "strict_raised": det_state["raised_without_warn"],
            "note": "frozen __init__ calls use_deterministic_algorithms(True); MPS may lack "
                    "deterministic kernels — probe records if warn_only was required",
        },
        "mps_self_consistency": {
            "n": len(keys), "boolean_flips_run1_vs_run2": self_bool_flips,
            "max_abs_delta_run1_vs_run2": self_max_delta,
            "verdict": "STABLE" if self_bool_flips == 0 else "NONDETERMINISTIC",
        },
        "cpu_vs_mps": {
            "n_items": len(ckeys),
            "boolean_flips": len(flips),
            "flip_rate": (len(flips) / len(ckeys)) if ckeys else 0.0,
            "score_delta_distribution": dist(deltas),
            "near_threshold_pm0.05": {"n": len(near), "flips": len(near_flips)},
            "flip_examples": [
                {"key": list(k), "cpu": {"raw": cpu[k][0], "bool": cpu[k][1]},
                 "mps": {"raw": mps1[k][0], "bool": mps1[k][1]}}
                for k in flips[:20]
            ],
        },
        "outcome": ("A_ZERO_FLIPS" if not flips and self_bool_flips == 0
                    else "B_FLIPS_OR_NONDETERMINISM"),
        "elapsed_s": round(time.time() - t0, 1),
    }

    # optional cross-check vs a provided serial_gt.json (per-family {item:{a:[..],c:[..]}})
    if args.cpu_gt and args.cpu_gt.exists():
        gt = json.loads(args.cpu_gt.read_text())
        mismatch = 0
        checked = 0
        state_key = {"assumption": "a", "correction": "c"}
        for fam, items in gt.items():
            if fam not in top:
                continue
            for i_s, ac in items.items():
                i = int(i_s)
                for st, kk in state_key.items():
                    for d, gt_bool in enumerate(ac[kk]):
                        k = (fam, st, d, i)
                        if k in mps1:
                            checked += 1
                            if bool(gt_bool) != mps1[k][1]:
                                mismatch += 1
        report["cross_check_vs_serial_gt"] = {"checked": checked, "mismatches_vs_mps": mismatch}

    atomic_write_json(args.out, report)
    _log("[probe] RESULT " + json.dumps({
        "outcome": report["outcome"],
        "cpu_vs_mps_flips": report["cpu_vs_mps"]["boolean_flips"],
        "flip_rate": round(report["cpu_vs_mps"]["flip_rate"], 6),
        "mps_self_flips": report["mps_self_consistency"]["boolean_flips_run1_vs_run2"],
        "warn_only_needed": report["deterministic"]["warn_only_needed_on_mps"],
        "max_delta": report["cpu_vs_mps"]["score_delta_distribution"].get("max"),
    }))
    _log(f"[probe] wrote {args.out}")


if __name__ == "__main__":
    main()
