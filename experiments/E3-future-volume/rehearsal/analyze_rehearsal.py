"""
E3 rehearsal analysis — the ENTIRE downstream analysis path, run exactly as the real 200-prompt
run would run it, on the ~40 LABELED throwaway prompts. Every number is DESCRIPTIVE at n=40 (an
n-of-40 R^2/AUROC is not a result); the point is to see which numbers would embarrass the program
at n=200 and to calibrate difficulty.

The stats path CALLS the instrument (e3_validation.*) at every step - it never reimplements it:
  - splits.in_distribution_split / splits.leave_one_family_out
  - probe.ridge_probe / probe.logistic_median_split_probe / probe.class_mean_predictor_r2
  - compare.auroc / compare.paired_bootstrap_auroc_diff
  - verdict.decide / VerdictInputs / VerdictThresholds

Thresholds are the THRESHOLDS-PROPOSAL.md proposed values (evaluated, not decided). The ridge
alpha grid and inner folds are also the proposed values.

DERIVED SEEDS (off base_seed = 20260714):
  split_seed            = base_seed + 1
  paired_bootstrap seed = base_seed + 2
  single_arm CI seed    = base_seed + 3
  synthetic_mixture seed= base_seed + 4

Writes results/analysis.json and prints every table.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr, spearmanr

from e3_validation import compare, probe, splits, verdict

RESULTS_DIR = Path(__file__).resolve().parent / "results"
BASE_SEED = 20260714

# THRESHOLDS-PROPOSAL.md proposed values (evaluated here, decided at registration).
ALPHA_GRID = tuple(np.logspace(-2.0, 6.0, 9))
INNER_FOLDS = 5
THRESHOLDS = verdict.VerdictThresholds(
    r2_fidelity_min=0.10,
    r2_margin_over_classmean_min=0.05,
    r2_ood_min=0.05,
    auc_binary_min=0.70,
    vc_ci_floor=0.0,
)
TEST_FRACTION = 0.30
N_BOOT = 10_000
CI_LEVEL = 0.95


# ---------------------------------------------------------------------------
# load
# ---------------------------------------------------------------------------
def load_rows():
    rows = []
    for p in sorted(RESULTS_DIR.glob("prompt_*.json")):
        r = json.loads(p.read_text())
        npz = np.load(RESULTS_DIR / r["npz"])
        r["_hidden"] = np.asarray(npz["hidden_state"], dtype=np.float64)
        r["_emb"] = np.asarray(npz["continuation_embeddings"], dtype=np.float64)
        rows.append(r)
    return rows


def _safe_spearman(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.std() == 0 or b.std() == 0 or a.size < 3:
        return float("nan")
    return float(spearmanr(a, b)[0])


def _safe_pearson(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.std() == 0 or b.std() == 0 or a.size < 3:
        return float("nan")
    return float(pearsonr(a, b)[0])


def _safe_auroc(scores, labels):
    """compare.auroc but returns (value_or_None, note) rather than raising on a single class."""
    labels = np.asarray(labels)
    if len(np.unique(labels)) < 2:
        return None, "undefined (single-class labels)"
    return compare.auroc(scores, labels), "ok"


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    rows = load_rows()
    n = len(rows)
    if n == 0:
        print("no results yet")
        return

    X = np.vstack([r["_hidden"] for r in rows])                       # (n, 3584)
    y = np.array([r["semantic_volume"] for r in rows], dtype=float)   # log-volume target (e3-0002)
    family = np.array([r["family"] for r in rows])
    difficulty = np.array([r["difficulty"] for r in rows], dtype=int)
    correct = np.array([1 if r["correct"] else 0 for r in rows], dtype=int)
    vc = np.array([r["vc"]["value"] if r["vc"]["value"] is not None else np.nan for r in rows], float)
    entropy = np.array([r["next_token_entropy_nats"] for r in rows], dtype=float)
    mean_len = np.array([np.mean(r["realized_lengths"]) for r in rows], dtype=float)
    std_len = np.array([np.std(r["realized_lengths"]) for r in rows], dtype=float)

    n_negatives = int((correct == 0).sum())
    n_positives = int((correct == 1).sum())
    has_both = 0 < n_negatives < n

    out = {
        "n": n,
        "n_correct": n_positives,
        "n_negatives": n_negatives,
        "families": {f: int((family == f).sum()) for f in sorted(set(family))},
        "thresholds_evaluated_at": THRESHOLDS.__dict__,
        "alpha_grid": [float(a) for a in ALPHA_GRID],
    }

    # ===== (3a) in-distribution split + ridge probe =====
    tr, te = splits.in_distribution_split(n, TEST_FRACTION, seed=BASE_SEED + 1)
    ridge = probe.ridge_probe(X[tr], y[tr], X[te], y[te], alpha_grid=ALPHA_GRID, inner_folds=INNER_FOLDS)
    r2_indist = ridge.r2
    spearman_indist = ridge.spearman
    r2_classmean = probe.class_mean_predictor_r2(y[tr], y[te], family[tr], family[te])

    out["indistribution"] = {
        "n_train": int(tr.size), "n_test": int(te.size),
        "ridge_alpha_selected": ridge.alpha,
        "r2": r2_indist, "spearman": spearman_indist,
        "classmean_r2": r2_classmean,
        "r2_minus_classmean": r2_indist - r2_classmean,
        "label": "DESCRIPTIVE at n=%d — not a result" % n,
    }

    # ===== (3a') SEP-style median-split logistic AUROC (volume class, always computable) =====
    try:
        logit = probe.logistic_median_split_probe(X[tr], y[tr], X[te], y[te])
        auc_binary = logit.auroc
        auc_binary_note = "ok"
    except Exception as e:  # single-class median split on a tiny test split
        auc_binary = None
        auc_binary_note = f"undefined ({e})"
    out["sep_median_split"] = {"auroc_volume_class": auc_binary, "note": auc_binary_note}

    # ===== (3b) leave-one-family-out — pooled OOD predicted volume for every prompt =====
    ood_pred = np.full(n, np.nan)
    ood_binscore = np.full(n, np.nan)
    per_family_r2 = {}
    for fam, ftr, fte in splits.leave_one_family_out(family):
        rp = probe.ridge_probe(X[ftr], y[ftr], X[fte], y[fte], alpha_grid=ALPHA_GRID, inner_folds=INNER_FOLDS)
        ood_pred[fte] = rp.predictions
        per_family_r2[str(fam)] = rp.r2
        # binarized probe held-out decision score (volume median-split), same rotation
        try:
            from sklearn.linear_model import LogisticRegression
            mu = X[ftr].mean(0); sd = X[ftr].std(0); sd = np.where(sd == 0, 1.0, sd)
            thr = float(np.median(y[ftr]))
            ybin = (y[ftr] > thr).astype(int)
            if len(np.unique(ybin)) == 2:
                clf = LogisticRegression(C=1.0, max_iter=1000).fit((X[ftr] - mu) / sd, ybin)
                ood_binscore[fte] = clf.decision_function((X[fte] - mu) / sd)
        except Exception:
            pass
    # pooled OOD R^2 over all prompts (every prompt predicted by a probe that never saw its family)
    from sklearn.metrics import r2_score
    r2_ood = float(r2_score(y, ood_pred))
    out["ood_leave_one_family_out"] = {
        "per_family_r2": per_family_r2,
        "pooled_r2": r2_ood,
        "pooled_spearman": _safe_spearman(y, ood_pred),
        "label": "DESCRIPTIVE at n=%d — load-bearing regime, uninterpretable at this n" % n,
    }

    # ===== (3c) correctness AUROCs (all arms) — direction fixed so higher score => more correct ==
    score_probe = -ood_pred            # higher predicted volume => less correct
    score_gtvol = -y                   # ground-truth volume ceiling (descriptive)
    score_binprobe = -ood_binscore     # higher volume-class => less correct
    score_vc = vc                      # higher verbalized confidence => more correct
    score_b3 = -entropy                # higher entropy => less correct

    aurocs = {}
    for name, s in [("probe_ood", score_probe), ("gt_volume_ceiling", score_gtvol),
                    ("binarized_probe_ood", score_binprobe), ("verbalized_confidence", score_vc),
                    ("predictive_entropy_b3", score_b3)]:
        mask = ~np.isnan(s)
        val, note = _safe_auroc(s[mask], correct[mask]) if mask.sum() >= 2 else (None, "insufficient")
        aurocs[name] = {"auroc": val, "note": note, "n_scored": int(mask.sum())}
    out["correctness_auroc"] = aurocs

    # ===== (3d) paired bootstrap probe vs verbalized confidence =====
    pb = None
    if has_both:
        mask = ~np.isnan(score_probe) & ~np.isnan(score_vc)
        if mask.sum() >= 2 and len(np.unique(correct[mask])) == 2:
            try:
                res = compare.paired_bootstrap_auroc_diff(
                    score_probe[mask], score_vc[mask], correct[mask],
                    n_boot=N_BOOT, ci_level=CI_LEVEL, seed=BASE_SEED + 2,
                )
                pb = {"diff": res.diff, "ci_low": res.ci_low, "ci_high": res.ci_high,
                      "excludes_zero": res.excludes_zero, "n_boot": res.n_boot,
                      "ci_level": res.ci_level, "n_scored": int(mask.sum())}
            except Exception as e:
                pb = {"error": str(e)}
    out["probe_vs_vc_paired_bootstrap"] = pb or {
        "note": "not computable — need both correctness classes present (negatives=%d)" % n_negatives
    }

    # ===== (3e) verdict.decide at the proposed thresholds =====
    probe_vs_vc_ci_low = pb["ci_low"] if (pb and "ci_low" in pb) else None
    verdict_block = {}
    if auc_binary is not None and probe_vs_vc_ci_low is not None:
        vin = verdict.VerdictInputs(
            r2_indist=r2_indist, r2_classmean_indist=r2_classmean,
            r2_ood=r2_ood, auc_binary=auc_binary, probe_vs_vc_ci_low=probe_vs_vc_ci_low,
        )
        branch = verdict.decide(vin, THRESHOLDS)
        verdict_block = {"inputs": vin.__dict__, "branch": branch.value, "computable": True}
    else:
        # report the branch that CAN be determined from the fidelity clause alone
        fidelity_present = (r2_indist >= THRESHOLDS.r2_fidelity_min and
                            (r2_indist - r2_classmean) >= THRESHOLDS.r2_margin_over_classmean_min)
        verdict_block = {
            "computable": False,
            "reason": ("verbalized-margin clause needs correctness AUROC, which needs both "
                       "correctness classes (negatives=%d); auc_binary=%s" % (n_negatives, auc_binary)),
            "continuous_fidelity_present": bool(fidelity_present),
            "would_route": ("not confirmed — fails fidelity clause, would land in refuted/no-signal "
                            "or refuted/binary-only depending on auc_binary" if not fidelity_present
                            else "fidelity clause passes; downstream clauses indeterminate"),
        }
    out["verdict"] = verdict_block

    # ===== (4) CALIBRATION =====
    acc_by_diff = {}
    for d in [1, 2, 3, 4]:
        m = difficulty == d
        acc_by_diff[d] = {
            "n": int(m.sum()),
            "n_correct": int(correct[m].sum()),
            "accuracy": float(correct[m].mean()) if m.sum() else None,
        }
    acc_by_family = {}
    for f in sorted(set(family)):
        m = family == f
        acc_by_family[f] = {"n": int(m.sum()), "n_correct": int(correct[m].sum()),
                            "accuracy": float(correct[m].mean())}
    acc_by_family_diff = {}
    for f in sorted(set(family)):
        for d in [1, 2, 3, 4]:
            m = (family == f) & (difficulty == d)
            if m.sum():
                acc_by_family_diff[f"{f}-d{d}"] = {"n": int(m.sum()),
                                                   "n_correct": int(correct[m].sum())}
    # greedy-truncation diagnostic: a greedy answer that never hit EOS was cut by the 256 cap,
    # and its correctness label is suspect (the final answer may never have been emitted).
    trunc = np.array([not r["greedy_answer_eos_hit"] for r in rows])
    out["greedy_truncation"] = {
        "n_truncated": int(trunc.sum()),
        "truncated_idx": [int(r["idx"]) for r, t in zip(rows, trunc) if t],
        "truncated_and_labeled_incorrect": int((trunc & (correct == 0)).sum()),
        "note": ("a truncated greedy answer's correctness label is a cap artifact risk: the model "
                 "may have been mid-derivation when MAX_TOKENS=256 cut it"),
    }

    out["calibration"] = {
        "accuracy_by_difficulty": acc_by_diff,
        "accuracy_by_family": acc_by_family,
        "n_by_family_difficulty": acc_by_family_diff,
        "n_negatives_overall": n_negatives,
        "overall_accuracy": float(correct.mean()),
    }

    # (4b) AUROC CI width at n=40 (observed negative rate) — single-arm percentile bootstrap
    def single_arm_ci(scores, labels, seed, n_boot=10_000):
        mask = ~np.isnan(scores)
        s, l = scores[mask], labels[mask]
        if len(np.unique(l)) < 2:
            return None
        rng = np.random.default_rng(seed)
        m = s.shape[0]
        vals = []
        from sklearn.metrics import roc_auc_score
        tries = 0
        while len(vals) < n_boot and tries < n_boot * 20:
            tries += 1
            idx = rng.integers(0, m, m)
            if len(np.unique(l[idx])) < 2:
                continue
            vals.append(roc_auc_score(l[idx], s[idx]))
        vals = np.array(vals)
        lo, hi = np.quantile(vals, [0.025, 0.975])
        return {"auroc_point": float(roc_auc_score(l, s)), "ci_low": float(lo),
                "ci_high": float(hi), "ci_width": float(hi - lo), "n_boot_effective": int(len(vals))}

    ci_at_40 = {
        "probe_ood": single_arm_ci(score_probe, correct, BASE_SEED + 3),
        "gt_volume_ceiling": single_arm_ci(score_gtvol, correct, BASE_SEED + 3),
    }
    out["calibration"]["auroc_ci_width_at_n%d" % n] = {
        "observed_negative_rate": (n_negatives / n),
        "arms": ci_at_40,
        "method": "single-arm percentile bootstrap, 10k resamples, 95% two-sided",
    }

    # (4c) extrapolated CI width at n=126 with 10/25/40% negative rates — synthetic-mixture bootstrap
    def synth_mixture_ci(scores, labels, target_n, neg_rate, seed, reps=2000):
        mask = ~np.isnan(scores)
        s, l = scores[mask], labels[mask]
        pos_pool = s[l == 1]; neg_pool = s[l == 0]
        if pos_pool.size == 0 or neg_pool.size == 0:
            return None
        rng = np.random.default_rng(seed)
        n_neg = int(round(target_n * neg_rate))
        n_pos = target_n - n_neg
        from sklearn.metrics import roc_auc_score
        vals = []
        for _ in range(reps):
            ps = rng.choice(pos_pool, n_pos, replace=True)
            ns = rng.choice(neg_pool, n_neg, replace=True)
            ss = np.concatenate([ps, ns])
            ll = np.concatenate([np.ones(n_pos), np.zeros(n_neg)])
            vals.append(roc_auc_score(ll, ss))
        vals = np.array(vals)
        lo, hi = np.quantile(vals, [0.025, 0.975])
        return {"ci_low": float(lo), "ci_high": float(hi), "ci_width": float(hi - lo),
                "median_auroc": float(np.median(vals)),
                "pos_pool_size": int(pos_pool.size), "neg_pool_size": int(neg_pool.size)}

    extrap = {}
    for arm_name, s in [("probe_ood", score_probe), ("gt_volume_ceiling", score_gtvol)]:
        extrap[arm_name] = {}
        for rate in [0.10, 0.25, 0.40]:
            extrap[arm_name][f"neg_rate_{int(rate*100)}pct"] = synth_mixture_ci(
                s, correct, target_n=126, neg_rate=rate, seed=BASE_SEED + 4)
    out["calibration"]["extrapolated_auroc_ci_width_at_n126"] = {
        "method": ("synthetic-mixture bootstrap: resample correct/incorrect conditional score "
                   "distributions (rehearsal-observed) to target n and negative rate, 2000 reps, "
                   "95% two-sided. Only as trustworthy as the (small) incorrect-score pool."),
        "arms": extrap,
    }

    # ===== (5) CONFOUNDS (descriptive) =====
    # within-family vs between-family volume variance decomposition
    grand = y.mean()
    ss_total = float(((y - grand) ** 2).sum())
    ss_between = 0.0
    within = {}
    for f in sorted(set(family)):
        yf = y[family == f]
        ss_between += yf.size * (yf.mean() - grand) ** 2
        within[f] = {"n": int(yf.size), "mean": float(yf.mean()), "var": float(yf.var(ddof=0))}
    ss_within = ss_total - ss_between
    out["confounds"] = {
        "volume_vs_mean_len": {"pearson": _safe_pearson(y, mean_len), "spearman": _safe_spearman(y, mean_len)},
        "volume_vs_std_len": {"pearson": _safe_pearson(y, std_len), "spearman": _safe_spearman(y, std_len)},
        "volume_vs_entropy": {"pearson": _safe_pearson(y, entropy), "spearman": _safe_spearman(y, entropy)},
        "volume_variance_decomposition": {
            "ss_total": ss_total, "ss_between_family": float(ss_between), "ss_within_family": float(ss_within),
            "eta_squared_between": float(ss_between / ss_total) if ss_total > 0 else None,
            "per_family": within,
            "note": "eta^2 = fraction of log-volume variance BETWEEN families; 1-eta^2 is within-family",
        },
    }

    # ===== (5b) TARGET RELIABILITY: split-half volume (draws 0-4 vs draws 5-9) =====
    # No target-reliability ceiling exists anywhere in the records: the probe's attainable R^2 is
    # bounded by how reproducible the volume itself is across independent draw sets. Split-half at
    # N=5 per half is NOISIER than the full N=10 statistic (log det on 5 points has fewer
    # well-conditioned directions), so this is a LOWER-BOUND-flavored reliability read, labeled so.
    from e3_validation.volume import semantic_volume as _sv
    v_a = np.array([_sv(r["_emb"][:5]) for r in rows])
    v_b = np.array([_sv(r["_emb"][5:]) for r in rows])
    # Spearman-Brown steps up a half-test correlation to full-length reliability
    r_half = _safe_pearson(v_a, v_b)
    sb = (2 * r_half / (1 + r_half)) if (r_half == r_half and r_half > -1) else float("nan")
    out["volume_split_half_reliability"] = {
        "pearson_half_vs_half": r_half,
        "spearman_half_vs_half": _safe_spearman(v_a, v_b),
        "spearman_brown_full_length": float(sb),
        "n": n,
        "method": ("volume recomputed on draws 0-4 vs draws 5-9 per prompt via "
                   "e3_validation.semantic_volume; correlated across prompts. N=5 halves are "
                   "noisier than the N=10 statistic, so this understates N=10 reliability; "
                   "Spearman-Brown correction reported. DESCRIPTIVE."),
        "implied_r2_ceiling_note": ("probe R^2 against the N=10 target cannot exceed target "
                                    "reliability; compare r2_fidelity_min=0.10 to this number"),
    }

    (RESULTS_DIR / "analysis.json").write_text(json.dumps(out, indent=2, default=float))
    _print_report(out)


def _print_report(o):
    n = o["n"]
    print("=" * 84)
    print(f"E3 REHEARSAL ANALYSIS — {n} LABELED throwaway prompts (every number DESCRIPTIVE at n={n})")
    print("=" * 84)
    print(f"\nnegatives (incorrect greedy answers): {o['n_negatives']} / {n}   "
          f"overall accuracy {o['calibration']['overall_accuracy']:.3f}")
    print(f"families: {o['families']}")

    print("\n--- (3) FULL STATS PATH ---")
    ind = o["indistribution"]
    print(f"in-dist ridge probe (train {ind['n_train']} / test {ind['n_test']}, alpha={ind['ridge_alpha_selected']:.3g}):")
    print(f"   R^2 = {ind['r2']:+.3f}   Spearman = {ind['spearman']:+.3f}   "
          f"class-mean R^2 = {ind['classmean_r2']:+.3f}   R^2-classmean = {ind['r2_minus_classmean']:+.3f}")
    sm = o["sep_median_split"]
    print(f"SEP median-split logistic AUROC (volume class): {sm['auroc_volume_class']}  ({sm['note']})")
    ood = o["ood_leave_one_family_out"]
    print(f"leave-one-family-out: pooled R^2 = {ood['pooled_r2']:+.3f}  pooled Spearman = {ood['pooled_spearman']:+.3f}")
    print(f"   per-family held-out R^2: " + "  ".join(f"{k}={v:+.3f}" for k, v in ood["per_family_r2"].items()))

    print("\ncorrectness AUROC (higher score => more correct):")
    for k, v in o["correctness_auroc"].items():
        print(f"   {k:24s} AUROC = {v['auroc']}  ({v['note']}, n={v['n_scored']})")

    pb = o["probe_vs_vc_paired_bootstrap"]
    print("\nprobe vs verbalized-confidence paired bootstrap (10k, 95%):")
    if "diff" in pb:
        print(f"   diff = {pb['diff']:+.3f}   CI = [{pb['ci_low']:+.3f}, {pb['ci_high']:+.3f}]   "
              f"excludes_zero = {pb['excludes_zero']}")
    else:
        print(f"   {pb.get('note') or pb.get('error')}")

    v = o["verdict"]
    print("\nverdict.decide at PROPOSED thresholds:")
    if v.get("computable"):
        print(f"   BRANCH FIRED: {v['branch']}")
        print(f"   inputs: {v['inputs']}")
    else:
        print(f"   NOT FULLY COMPUTABLE: {v['reason']}")
        print(f"   continuous_fidelity_present = {v['continuous_fidelity_present']}")
        print(f"   would route: {v['would_route']}")

    gt = o["greedy_truncation"]
    print(f"\ngreedy answers truncated by 256 cap: {gt['n_truncated']} (idx {gt['truncated_idx']}); "
          f"of those labeled incorrect: {gt['truncated_and_labeled_incorrect']}")

    print("\n--- (4) CALIBRATION ---")
    print("accuracy by intended difficulty (the curve the corpus hardening is set from):")
    for d, s in o["calibration"]["accuracy_by_difficulty"].items():
        acc = s["accuracy"]
        bar = "#" * int(round((acc or 0) * 20))
        print(f"   d{d}: {s['n_correct']:2d}/{s['n']:2d} = {acc if acc is None else f'{acc:.3f}'}  {bar}")
    print("accuracy by family:")
    for f, s in o["calibration"]["accuracy_by_family"].items():
        print(f"   {f:11s}: {s['n_correct']:2d}/{s['n']:2d} = {s['accuracy']:.3f}")
    ci40key = [k for k in o["calibration"] if k.startswith("auroc_ci_width_at_n")][0]
    ci40 = o["calibration"][ci40key]
    print(f"\nAUROC CI width at n={n} (observed neg rate {ci40['observed_negative_rate']:.3f}):")
    for arm, r in ci40["arms"].items():
        if r:
            print(f"   {arm:20s} AUROC={r['auroc_point']:.3f} CI=[{r['ci_low']:.3f},{r['ci_high']:.3f}] width={r['ci_width']:.3f}")
        else:
            print(f"   {arm:20s} undefined (single-class)")
    print("\nextrapolated AUROC CI width at n=126 (synthetic-mixture bootstrap):")
    ex = o["calibration"]["extrapolated_auroc_ci_width_at_n126"]["arms"]
    for arm, rates in ex.items():
        print(f"   {arm}:")
        for rate, r in rates.items():
            if r:
                print(f"      {rate:14s} width={r['ci_width']:.3f}  median AUROC={r['median_auroc']:.3f}  "
                      f"(pos pool {r['pos_pool_size']}, neg pool {r['neg_pool_size']})")
            else:
                print(f"      {rate:14s} undefined (empty pool)")

    print("\n--- (5) CONFOUNDS (descriptive) ---")
    c = o["confounds"]
    print(f"volume vs mean continuation length: Pearson {c['volume_vs_mean_len']['pearson']:+.3f}  "
          f"Spearman {c['volume_vs_mean_len']['spearman']:+.3f}")
    print(f"volume vs std  continuation length: Pearson {c['volume_vs_std_len']['pearson']:+.3f}  "
          f"Spearman {c['volume_vs_std_len']['spearman']:+.3f}")
    print(f"volume vs predictive entropy:       Pearson {c['volume_vs_entropy']['pearson']:+.3f}  "
          f"Spearman {c['volume_vs_entropy']['spearman']:+.3f}")
    vd = c["volume_variance_decomposition"]
    print(f"volume variance: between-family eta^2 = {vd['eta_squared_between']:.3f}  "
          f"(within-family = {1 - vd['eta_squared_between']:.3f})")
    sh = o.get("volume_split_half_reliability")
    if sh:
        print(f"volume target split-half reliability (draws 0-4 vs 5-9): Pearson {sh['pearson_half_vs_half']:+.3f}  "
              f"Spearman {sh['spearman_half_vs_half']:+.3f}  Spearman-Brown full-length {sh['spearman_brown_full_length']:+.3f}")

    print("\nwrote", RESULTS_DIR / "analysis.json")


if __name__ == "__main__":
    main()
