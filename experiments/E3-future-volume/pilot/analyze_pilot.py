"""
E3 pilot analysis — reads results/prompt_XX.json, emits distributions and writes
results/summary.json.

Everything here is DESCRIPTIVE plumbing-level observation, not a hypothesis test. The two
correlations (volume vs entropy, volume vs verbalized confidence) are Spearman over 30 disposable
points and are labelled as such; they exist to sanity-check that the wired-up statistics move
together in roughly the expected directions, NOT to support any claim.

Outputs:
  - printed report (distributions overall + per prompt-kind, entropy, VC histogram + parse
    failures, per-continuation length stats, total wall time, the two Spearman correlations)
  - results/summary.json (the same numbers, machine-readable)
"""

import json
from pathlib import Path

import numpy as np
from scipy import stats

RESULTS_DIR = Path(__file__).resolve().parent / "results"

KIND_ORDER = ["factual", "math", "instruction", "ambiguous", "creative"]


def load_results():
    rows = []
    for p in sorted(RESULTS_DIR.glob("prompt_*.json")):
        rows.append(json.loads(p.read_text()))
    return rows


def dist(xs):
    a = np.asarray(xs, dtype=float)
    if a.size == 0:
        return None
    return {
        "n": int(a.size),
        "min": float(a.min()),
        "q1": float(np.percentile(a, 25)),
        "median": float(np.median(a)),
        "q3": float(np.percentile(a, 75)),
        "max": float(a.max()),
        "mean": float(a.mean()),
        "std": float(a.std(ddof=0)),
    }


def fmt_dist(d):
    if d is None:
        return "(none)"
    return (f"n={d['n']:2d} min={d['min']:+8.3f} q1={d['q1']:+8.3f} "
            f"med={d['median']:+8.3f} q3={d['q3']:+8.3f} max={d['max']:+8.3f} "
            f"mean={d['mean']:+8.3f}")


def main():
    rows = load_results()
    if not rows:
        print("no results found in", RESULTS_DIR)
        return

    n = len(rows)
    volumes = [r["semantic_volume"] for r in rows]
    entropies = [r["next_token_entropy_nats"] for r in rows]
    kinds = [r["kind"] for r in rows]

    # per-continuation realized lengths (flattened across all prompts)
    all_lengths = [ln for r in rows for ln in r["realized_lengths"]]
    eos_hits = [r["eos_hit_count"] for r in rows]

    # VC
    vc_values = [r["vc"]["value"] for r in rows]
    vc_present = [v for v in vc_values if v is not None]
    vc_missing = sum(1 for v in vc_values if v is None)
    vc_retried = sum(1 for r in rows if r["vc"].get("retried"))
    vc_parse_failed_first = sum(1 for r in rows if r["vc"].get("parse_failed_first"))

    # wall time
    total_wall = sum(r["prompt_total_wall_s"] for r in rows)
    gen_wall = sum(r["gen_total_wall_s"] for r in rows)
    embed_wall = sum(r.get("embed_wall_s", 0.0) for r in rows)
    vc_wall = sum(r["vc"].get("wall_s", 0.0) for r in rows)

    summary = {
        "n_prompts": n,
        "volume_overall": dist(volumes),
        "volume_by_kind": {},
        "entropy_overall": dist(entropies),
        "entropy_by_kind": {},
        "continuation_length_overall": dist(all_lengths),
        "continuation_length_by_kind": {},
        "eos_hit_count_per_prompt": {"values": eos_hits, "total_over_all": int(sum(eos_hits))},
        "vc": {
            "values": vc_values,
            "present_count": len(vc_present),
            "missing_count": vc_missing,
            "retried_count": vc_retried,
            "parse_failed_first_count": vc_parse_failed_first,
            "present_dist": dist(vc_present),
            "histogram_bins_of_10": _hist_0_100(vc_present),
        },
        "wall_time_s": {
            "total_prompt_wall_sum": total_wall,
            "generation_wall_sum": gen_wall,
            "embed_wall_sum": embed_wall,
            "vc_wall_sum": vc_wall,
        },
        "correlations_descriptive_not_a_test": {},
    }

    for k in KIND_ORDER:
        vk = [r["semantic_volume"] for r in rows if r["kind"] == k]
        ek = [r["next_token_entropy_nats"] for r in rows if r["kind"] == k]
        lk = [ln for r in rows if r["kind"] == k for ln in r["realized_lengths"]]
        summary["volume_by_kind"][k] = dist(vk)
        summary["entropy_by_kind"][k] = dist(ek)
        summary["continuation_length_by_kind"][k] = dist(lk)

    # Spearman correlations — DESCRIPTIVE, plumbing-level observation, NOT a hypothesis test.
    if n >= 3:
        rho_ve, p_ve = stats.spearmanr(volumes, entropies)
        summary["correlations_descriptive_not_a_test"]["volume_vs_entropy_spearman"] = {
            "rho": float(rho_ve), "p_value_descriptive_only": float(p_ve), "n": n,
        }
        # volume vs VC over the subset with a parsed VC value
        pair = [(r["semantic_volume"], r["vc"]["value"]) for r in rows
                if r["vc"]["value"] is not None]
        if len(pair) >= 3:
            vv = [a for a, _ in pair]
            cc = [b for _, b in pair]
            rho_vc, p_vc = stats.spearmanr(vv, cc)
            summary["correlations_descriptive_not_a_test"]["volume_vs_vc_spearman"] = {
                "rho": float(rho_vc), "p_value_descriptive_only": float(p_vc), "n": len(pair),
            }
        else:
            summary["correlations_descriptive_not_a_test"]["volume_vs_vc_spearman"] = {
                "rho": None, "note": "fewer than 3 parsed VC values", "n": len(pair),
            }

    (RESULTS_DIR / "summary.json").write_text(json.dumps(summary, indent=2))

    # ---- printed report ----
    print("=" * 78)
    print(f"E3 PILOT ANALYSIS — {n} throwaway prompts (DESCRIPTIVE plumbing observation only)")
    print("=" * 78)
    print("\nSEMANTIC VOLUME  log det(G + 1e-6 I)   [e3-0002, via e3_validation.semantic_volume]")
    print(f"  overall   {fmt_dist(summary['volume_overall'])}")
    print("  by kind (dynamic range across kinds — the key plumbing question):")
    for k in KIND_ORDER:
        print(f"    {k:12s} {fmt_dist(summary['volume_by_kind'][k])}")

    print("\nNEXT-TOKEN PREDICTIVE ENTROPY (nats)   [e3-0003 B3]")
    print(f"  overall   {fmt_dist(summary['entropy_overall'])}")
    for k in KIND_ORDER:
        print(f"    {k:12s} {fmt_dist(summary['entropy_by_kind'][k])}")

    print("\nCONTINUATION REALIZED LENGTH (tokens, across all draws)")
    print(f"  overall   {fmt_dist(summary['continuation_length_overall'])}")
    for k in KIND_ORDER:
        print(f"    {k:12s} {fmt_dist(summary['continuation_length_by_kind'][k])}")
    print(f"  EOS-hit continuations total: {summary['eos_hit_count_per_prompt']['total_over_all']}"
          f" / {n * len(rows[0]['realized_lengths'])}")

    print("\nVERBALIZED CONFIDENCE  [e3-0003 B1]")
    print(f"  present={len(vc_present)}  missing={vc_missing}  "
          f"retried={vc_retried}  parse_failed_first_turn={vc_parse_failed_first}")
    if vc_present:
        print(f"  value dist {fmt_dist(summary['vc']['present_dist'])}")
        print("  histogram (bins of 10):")
        for lo, cnt in summary["vc"]["histogram_bins_of_10"]:
            bar = "#" * cnt
            print(f"    [{lo:3d}-{lo+9 if lo < 90 else 100:3d}] {cnt:2d} {bar}")

    print("\nWALL TIME")
    w = summary["wall_time_s"]
    print(f"  total prompt wall  {w['total_prompt_wall_sum']:.1f}s "
          f"({w['total_prompt_wall_sum']/60:.1f} min)")
    print(f"    generation       {w['generation_wall_sum']:.1f}s")
    print(f"    embedding        {w['embed_wall_sum']:.1f}s")
    print(f"    verbalized-conf  {w['vc_wall_sum']:.1f}s")

    print("\nCORRELATIONS (Spearman, DESCRIPTIVE plumbing observation — NOT a hypothesis test)")
    c = summary["correlations_descriptive_not_a_test"]
    ve = c.get("volume_vs_entropy_spearman")
    if ve:
        print(f"  volume vs entropy: rho={ve['rho']:+.3f} (n={ve['n']})")
    vc = c.get("volume_vs_vc_spearman")
    if vc and vc.get("rho") is not None:
        print(f"  volume vs VC:      rho={vc['rho']:+.3f} (n={vc['n']})")
    elif vc:
        print(f"  volume vs VC:      {vc.get('note')}")

    print("\nwrote", RESULTS_DIR / "summary.json")


def _hist_0_100(values):
    """Bins of 10 over [0,100]; last bin includes 100."""
    bins = [(lo, 0) for lo in range(0, 100, 10)]
    counts = [0] * 10
    for v in values:
        b = min(int(v) // 10, 9)
        counts[b] += 1
    return [[lo, counts[i]] for i, (lo, _) in enumerate(bins)]


if __name__ == "__main__":
    main()
