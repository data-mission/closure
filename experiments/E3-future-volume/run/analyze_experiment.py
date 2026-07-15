"""
E3 CONFIRMATORY ANALYSIS + VERDICT — wires the 200-prompt confirmatory results into the frozen
E3 instrument (e3_validation.*) and lets the instrument decide. This driver reimplements NO
statistic: every gate quantity is produced by calling the frozen modules (preconditions, fidelity,
splits, ood, correctness, compare, probe, verdict, volume). The driver only assembles data and wires
the modules exactly as the instrument's own integration test wires them
(validation/tests/test_probe_signal.py::test_verdict_is_confirmed_shaped and the fidelity/correctness
test modules); the frozen instrument computes the verdict.

ALL thresholds, seeds, the alpha grid, fold counts, bootstrap parameters, epsilon and N are READ from
results/run_manifest.json (the committed frozen config). Nothing result-moving is hardcoded here. The
per-parameter SWEEP SETS are the pre-registered sweep points from THRESHOLDS-PROPOSAL.md (they are a
separate registered artifact, not part of the manifest); each sweep set is asserted to contain the
manifest primary so the two registered artifacts are cross-checked at run time.

Two evaluation arms, each on the subset the protocol defines:
  * VOLUME / FIDELITY / OOD arm — every non-excluded prompt (all five families). Target: log-volume
    (e3_validation.volume, called; recorded per prompt as semantic_volume). A prompt is excluded from
    this arm only under the refusal rule (fewer than N valid continuations); its volume is still
    recorded for the audit trail.
  * CORRECTNESS arm — the answerable subset (answerable, non-excluded, greedy answer not truncated by
    the answer cap). Arms: probe = -predicted_volume (OOF k-fold), B3 = -entropy, B4 = P(correct)
    (OOF k-fold), verbalized = the two frozen B1 variants collapsed by max-over-variants.

Outputs:
  * results/analysis.json — every number (gate inputs, verdict, sweep, determinism hashes,
    exploratory block, provenance).
  * VERDICT.md — the verdict branch first; registered-vs-observed gate table; sweep stability;
    a clearly-marked exploratory section with zero verdict weight; a provenance block; an
    honest-limitations paragraph. Written only on the full 200-prompt run (never under --dry-run).

Determinism: the analysis is a pure function of the frozen inputs and the manifest seed formulas
(closed-form ridge, seeded k-fold, seeded bootstrap). The compute path is run twice and the gate
block is hashed; the two hashes must be identical.

Usage:
  ./.venv/bin/python analyze_experiment.py                # full run, requires 200 results
  ./.venv/bin/python analyze_experiment.py --dry-run      # wiring proof on partial data, no VERDICT.md
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import time
import warnings
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr, spearmanr
from sklearn.metrics import r2_score

from e3_validation import compare, correctness, fidelity, ood, preconditions, probe, splits, verdict
from e3_validation.volume import EPSILON as VOL_EPSILON

RESULTS_DIR = Path(__file__).resolve().parent / "results"
MANIFEST_PATH = RESULTS_DIR / "run_manifest.json"
ANALYSIS_PATH = RESULTS_DIR / "analysis.json"
VERDICT_PATH = Path(__file__).resolve().parent / "VERDICT.md"

# Pre-registered per-parameter sweep sets (THRESHOLDS-PROPOSAL.md § "Proposed values"). NOT in the
# manifest — a separate registered artifact. Every set is asserted to contain the manifest primary
# below (cross-check of the two registered artifacts). Threshold-only params re-decide on fixed
# inputs; correctness_cv_folds is data-affecting (re-derives the correctness arm at the new k).
REGISTERED_SWEEP = {
    "min_negatives": [15, 20],
    "r2_fidelity_min": [0.05, 0.10, 0.20],
    "spearman_fidelity_min": [0.2, 0.3, 0.4],
    "within_family_spearman_min": [0.2, 0.3, 0.4],
    "family_oracle_margin_min": [0.05, 0.10],
    "ood_pooled_spearman_min": [0.2, 0.3],
    "ood_per_family_floor": [0.0, 0.1],
    "b3_ci_floor": [0.0],
    "b4_margin_ceiling": [0.0],
    "correctness_cv_folds": [5, 10],
}


# ---------------------------------------------------------------------------
# manifest / config
# ---------------------------------------------------------------------------
def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text())


def build_config(manifest: dict) -> dict:
    fc = manifest["frozen_config"]
    th = fc["thresholds"]
    seeds = fc["seeds"]
    base_seed = int(seeds["base_seed"])
    cfg = {
        "base_seed": base_seed,
        "split_seed": base_seed + 1,
        "paired_bootstrap_seed": base_seed + 2,
        "single_arm_ci_seed": base_seed + 3,
        "synthetic_mixture_seed": base_seed + 4,
        "correctness_cv_seed": base_seed + 5,
        "alpha_grid": tuple(float(a) for a in fc["alpha_grid"]),
        "inner_cv_folds": int(fc["inner_cv_folds"]),
        "correctness_cv_folds": int(fc["correctness_cv_folds"]),
        "bootstrap_n": int(fc["bootstrap_n"]),
        "bootstrap_ci_level": float(fc["bootstrap_ci_level"]),
        "test_fraction": float(fc["test_fraction"]),
        "epsilon": float(fc["epsilon"]),
        "n_continuations": int(fc["n_continuations"]),
        "thresholds_raw": th,
        "frozen_config_sha256": manifest["frozen_config_sha256"],
        "registration": manifest["registration"],
        "n_prompts": int(manifest["n_prompts"]),
        "n_answerable_manifest": int(manifest["n_answerable"]),
    }
    cfg["thresholds"] = verdict.VerdictThresholds(
        min_negatives=int(th["min_negatives"]),
        r2_fidelity_min=float(th["r2_fidelity_min"]),
        spearman_fidelity_min=float(th["spearman_fidelity_min"]),
        within_family_spearman_min=float(th["within_family_spearman_min"]),
        family_oracle_margin_min=float(th["family_oracle_margin_min"]),
        r2_margin_over_classmean_min=float(th["r2_margin_over_classmean_min"]),
        ood_pooled_spearman_min=float(th["ood_pooled_spearman_min"]),
        ood_per_family_floor=float(th["ood_per_family_floor"]),
        auc_binary_min=float(th["auc_binary_min"]),
        vc_ci_floor=float(th["vc_ci_floor"]),
        b3_ci_floor=float(th["b3_ci_floor"]),
        b4_margin_ceiling=float(th["b4_margin_ceiling"]),
        require_length_robust=bool(th["require_length_robust"]),
    )
    if cfg["epsilon"] != VOL_EPSILON:
        raise ValueError(
            f"manifest epsilon {cfg['epsilon']} != instrument volume EPSILON {VOL_EPSILON}"
        )
    # Cross-check the two registered artifacts: every sweep set must contain the manifest primary.
    for name, sweep in REGISTERED_SWEEP.items():
        primary = getattr(cfg["thresholds"], name, None)
        if name == "correctness_cv_folds":
            primary = cfg["correctness_cv_folds"]
        if primary is not None and not any(abs(float(primary) - float(s)) < 1e-12 for s in sweep):
            raise ValueError(
                f"manifest primary {name}={primary} not in registered sweep set {sweep} "
                "(THRESHOLDS-PROPOSAL.md and the manifest disagree)"
            )
    return cfg


# ---------------------------------------------------------------------------
# load
# ---------------------------------------------------------------------------
def load_rows(cap: int | None = None):
    """Load every results/prompt_*.json plus its npz. Returns (rows, unreadable)."""
    paths = sorted(RESULTS_DIR.glob("prompt_*.json"))
    rows, unreadable = [], []
    for p in paths:
        try:
            r = json.loads(p.read_text())
            npz = np.load(RESULTS_DIR / r["npz"])
            r["_hidden"] = np.asarray(npz["hidden_state"], dtype=np.float64)
            r["_emb"] = np.asarray(npz["continuation_embeddings"], dtype=np.float64)
            if r["_hidden"].shape != (3584,):
                raise ValueError(f"hidden_state shape {r['_hidden'].shape} != (3584,)")
            if r["_emb"].shape != (10, 768):
                raise ValueError(f"continuation_embeddings shape {r['_emb'].shape} != (10,768)")
            rows.append(r)
        except Exception as e:  # noqa: BLE001 — record and surface, never silently drop
            unreadable.append({"file": p.name, "error": repr(e)})
    if cap is not None:
        rows = rows[:cap]
    return rows, unreadable


# ---------------------------------------------------------------------------
# assembly
# ---------------------------------------------------------------------------
def assemble(rows: list[dict]) -> dict:
    n = len(rows)
    idx = np.array([r["idx"] for r in rows], dtype=int)
    family = np.array([r["family"] for r in rows], dtype=object)
    difficulty = np.array([r["difficulty"] for r in rows], dtype=int)
    kind = np.array([r["kind"] for r in rows], dtype=object)
    answerable = np.array([bool(r["answerable"]) for r in rows], dtype=bool)
    volume = np.array([float(r["semantic_volume"]) for r in rows], dtype=float)
    entropy = np.array([float(r["next_token_entropy_nats"]) for r in rows], dtype=float)
    n_valid = np.array([int(r["n_valid_continuations"]) for r in rows], dtype=int)
    greedy_eos = np.array([bool(r.get("greedy_answer_eos_hit", False)) for r in rows], dtype=bool)
    X = np.vstack([r["_hidden"] for r in rows])
    mean_len = np.array([float(np.mean(r["realized_lengths"])) for r in rows], dtype=float)
    std_len = np.array([float(np.std(r["realized_lengths"], ddof=0)) for r in rows], dtype=float)
    lengths = np.column_stack([mean_len, std_len])

    # correctness label — defined only for answerable items (None otherwise -> -1 sentinel, masked out)
    correct = np.array(
        [int(bool(r["correct"])) if (r["answerable"] and r.get("correct") is not None) else -1
         for r in rows],
        dtype=int,
    )

    def vc_value(r, key):
        v = r.get(key)
        if v is None:
            return np.nan
        val = v.get("value")
        if val is None or v.get("missing", False):
            return np.nan
        return float(val)

    vc_zero = np.array([vc_value(r, "vc_zero_shot") for r in rows], dtype=float)
    vc_cot = np.array([vc_value(r, "vc_cot") for r in rows], dtype=float)

    # Refusal-rule exclusion from the VOLUME arm: fewer than N valid continuations, or the run flagged
    # the prompt excluded. (The volume is still recorded on the row for the audit trail.)
    excluded_volume = (n_valid < 10) | np.array([bool(r.get("excluded", False)) for r in rows])

    return {
        "n": n, "idx": idx, "family": family, "difficulty": difficulty, "kind": kind,
        "answerable": answerable, "volume": volume, "entropy": entropy, "n_valid": n_valid,
        "greedy_eos": greedy_eos, "X": X, "mean_len": mean_len, "std_len": std_len,
        "lengths": lengths, "correct": correct, "vc_zero": vc_zero, "vc_cot": vc_cot,
        "excluded_volume": excluded_volume,
    }


# ---------------------------------------------------------------------------
# fidelity + OOD arm (volume target, all non-excluded prompts, all families)
# ---------------------------------------------------------------------------
def compute_volume_arm(data: dict, cfg: dict) -> dict:
    vmask = ~data["excluded_volume"]
    X = data["X"][vmask]
    y = data["volume"][vmask]
    fam = data["family"][vmask]
    lengths = data["lengths"][vmask]
    n = int(vmask.sum())
    ncont = cfg["n_continuations"]
    eps = cfg["epsilon"]
    ag = cfg["alpha_grid"]
    inner = cfg["inner_cv_folds"]

    tr, te = splits.in_distribution_split(n, cfg["test_fraction"], seed=cfg["split_seed"])
    res = probe.ridge_probe(X[tr], y[tr], X[te], y[te], alpha_grid=ag, inner_folds=inner)
    r2_indist = res.r2
    spearman_indist = res.spearman

    # two-part fidelity: split the degenerate floor out of the TEST split, score continuous fidelity
    # on the non-degenerate subset only (fidelity.continuous_fidelity).
    deg_te = fidelity.degenerate_mask(y[te], n_continuations=ncont, epsilon=eps)
    nondeg_te = ~deg_te
    r2_nd, sp_nd, n_nd = fidelity.continuous_fidelity(res.predictions, y[te], nondeg_te)
    n_deg = int(deg_te.sum())

    # degeneracy classifier AUROC (reported, never gated). Single-class train/eval -> not evaluable.
    deg_tr = fidelity.degenerate_mask(y[tr], n_continuations=ncont, epsilon=eps)
    try:
        deg_auroc = fidelity.degeneracy_auroc(X[tr], deg_tr, X[te], deg_te)
        deg_auroc_note = "ok"
    except Exception as e:  # noqa: BLE001
        deg_auroc = None
        deg_auroc_note = f"not-evaluable ({e})"

    # within-family fidelity (family-band confound guard) — FULL test split, per the instrument's own
    # integration wiring (test_probe_signal.py): no non-degenerate mask is passed here.
    wf_r2, wf_sp = fidelity.within_family_metrics(res.predictions, y[te], y[tr], fam[te], fam[tr])
    family_oracle_r2 = fidelity.family_mean_oracle_r2(y[tr], y[te], fam[tr], fam[te])
    family_oracle_margin = r2_indist - family_oracle_r2  # probe (full-test R2) minus family-mean oracle

    # length gate quantity — within-family Spearman after residualizing volume on (mean,std) length.
    len_resid_sp = fidelity.length_residualized_within_family_spearman(
        res.predictions, y[te], y[tr], fam[te], fam[tr], lengths[tr], lengths[te]
    )

    # B2 reporting: the 2-bin (train-median split) class-mean oracle R^2.
    thr = float(np.median(y[tr]))
    cls_tr = (y[tr] > thr).astype(int)
    cls_te = (y[te] > thr).astype(int)
    try:
        r2_classmean = probe.class_mean_predictor_r2(y[tr], y[te], cls_tr, cls_te)
        classmean_note = "ok"
    except Exception as e:  # noqa: BLE001
        r2_classmean = float("nan")
        classmean_note = f"not-evaluable ({e})"

    # B2: SEP-style median-split logistic AUROC.
    try:
        auc_binary = probe.logistic_median_split_probe(X[tr], y[tr], X[te], y[te]).auroc
        auc_binary_note = "ok"
    except Exception as e:  # noqa: BLE001
        auc_binary = None
        auc_binary_note = f"not-evaluable ({e})"

    # OOD — leave-one-family-out, within-held-out-family Spearman (ood.leave_one_family_out_spearman).
    oodres = ood.leave_one_family_out_spearman(X, y, fam)
    per_rotation = [
        {
            "family": str(rr.held_out_family), "spearman": rr.spearman, "n_held": rr.n_held,
            "held_range": list(rr.held_range), "train_range": list(rr.train_range),
            "range_uncovered": rr.range_uncovered,
        }
        for rr in oodres.per_rotation
    ]

    return {
        "n_volume_arm": n, "n_train": int(tr.size), "n_test": int(te.size),
        "ridge_alpha_selected": res.alpha,
        "r2_indist": r2_indist, "spearman_indist": spearman_indist,
        "r2_nondegenerate": r2_nd, "spearman_nondegenerate": sp_nd,
        "n_nondegenerate": n_nd, "n_degenerate": n_deg,
        "degeneracy_auroc": deg_auroc, "degeneracy_auroc_note": deg_auroc_note,
        "within_family_r2": wf_r2, "within_family_spearman": wf_sp,
        "family_oracle_r2": family_oracle_r2, "family_oracle_margin": family_oracle_margin,
        "within_family_spearman_length_resid": len_resid_sp,
        "r2_classmean_indist": r2_classmean, "classmean_note": classmean_note,
        "auc_binary": auc_binary, "auc_binary_note": auc_binary_note,
        "ood_pooled_spearman": oodres.pooled_spearman,
        "ood_min_rotation_spearman": oodres.min_rotation_spearman,
        "ood_range_uncovered": bool(oodres.any_range_uncovered),
        "ood_per_rotation": per_rotation,
    }


# ---------------------------------------------------------------------------
# correctness arm (answerable subset)
# ---------------------------------------------------------------------------
def correctness_mask(data: dict) -> np.ndarray:
    # answerable, non-excluded (>=10 valid), greedy answer not truncated by the answer cap.
    return data["answerable"] & (~data["excluded_volume"]) & data["greedy_eos"] & (data["correct"] >= 0)


def compute_correctness_arm(data: dict, cfg: dict, k: int, full_report: bool = True) -> dict:
    m = correctness_mask(data)
    Xc = data["X"][m]
    volc = data["volume"][m]
    corr = data["correct"][m].astype(int)
    ent = data["entropy"][m]
    vc_zero = data["vc_zero"][m]
    vc_cot = data["vc_cot"][m]
    n = int(m.sum())
    n_neg = int((corr == 0).sum())
    n_pos = int((corr == 1).sum())

    ag = cfg["alpha_grid"]
    inner = cfg["inner_cv_folds"]
    cv_seed = cfg["correctness_cv_seed"]
    boot_seed = cfg["paired_bootstrap_seed"]
    n_boot = cfg["bootstrap_n"]
    ci_level = cfg["bootstrap_ci_level"]

    # arm scores (frozen orientation; probe & B4 strictly out-of-fold via seeded k-fold).
    probe_oof = correctness.probe_scores_oof(Xc, volc, k=k, seed=cv_seed, alpha_grid=ag, inner_folds=inner)
    b3 = correctness.b3_scores(ent)
    try:
        b4_oof = correctness.b4_scores_oof(Xc, corr, k=k, seed=cv_seed)
        b4_note = "ok"
    except Exception as e:  # noqa: BLE001
        b4_oof = None
        b4_note = f"not-evaluable ({e})"

    # verbalized arm: max over the two frozen B1 variants (manifest b1_variants.added_value_gate).
    vc_max = np.nanmax(np.vstack([vc_zero, vc_cot]), axis=0)
    present = correctness.vc_present_mask(vc_max)

    def arm(scores):
        try:
            a = correctness.arm_aurocs(scores, corr, present)
            return {"full": a.full, "vc_present": a.vc_present}
        except Exception as e:  # noqa: BLE001
            return {"error": repr(e)}

    aurocs = {"probe": arm(probe_oof), "b3": arm(b3)}
    if b4_oof is not None:
        aurocs["b4"] = arm(b4_oof)
    aurocs["vc_max"] = arm(vc_max)
    aurocs["vc_zero_shot"] = arm(vc_zero)
    aurocs["vc_cot"] = arm(vc_cot)

    def pb(a, b, mask=None, seed=boot_seed):
        aa, bb, yy = (a, b, corr) if mask is None else (a[mask], b[mask], corr[mask])
        try:
            r = compare.paired_bootstrap_auroc_diff(aa, bb, yy, n_boot=n_boot, ci_level=ci_level, seed=seed)
            return {"diff": r.diff, "ci_low": r.ci_low, "ci_high": r.ci_high,
                    "excludes_zero": r.excludes_zero, "n": int(len(yy))}
        except Exception as e:  # noqa: BLE001
            return {"error": repr(e)}

    # gated comparisons (probe vs strongest verbalized on the VC-present subset; probe vs B3; B4 vs probe).
    probe_vs_vcmax = pb(probe_oof, vc_max, mask=present)
    probe_vs_b3 = pb(probe_oof, b3)
    b4_vs_probe = pb(b4_oof, probe_oof) if b4_oof is not None else {"error": "b4 not evaluable"}

    # reporting-only per-variant comparisons (skipped for sweep recomputes to save bootstraps).
    if full_report:
        probe_vs_vczero = pb(probe_oof, vc_zero, mask=correctness.vc_present_mask(vc_zero))
        probe_vs_vccot = pb(probe_oof, vc_cot, mask=correctness.vc_present_mask(vc_cot))
    else:
        probe_vs_vczero = {"skipped": "reporting-only, omitted on sweep recompute"}
        probe_vs_vccot = {"skipped": "reporting-only, omitted on sweep recompute"}

    return {
        "n_answerable_scored": n, "n_negatives": n_neg, "n_positives": n_pos, "k_folds": k,
        "aurocs": aurocs,
        "probe_vs_vc_max": probe_vs_vcmax,
        "probe_vs_b3": probe_vs_b3,
        "b4_vs_probe": b4_vs_probe,
        "probe_vs_vc_zero_shot": probe_vs_vczero,
        "probe_vs_vc_cot": probe_vs_vccot,
        "b4_note": b4_note,
        "n_vc_present": int(present.sum()),
    }


# ---------------------------------------------------------------------------
# verdict inputs assembly + decide
# ---------------------------------------------------------------------------
def build_verdict_inputs(vol: dict, corr: dict) -> verdict.VerdictInputs:
    def ci_low(block):
        v = block.get("ci_low")
        return float(v) if v is not None else float("nan")

    return verdict.VerdictInputs(
        n_negatives=int(corr["n_negatives"]),
        r2_nondegenerate=float(vol["r2_nondegenerate"]),
        spearman_nondegenerate=float(vol["spearman_nondegenerate"]),
        n_nondegenerate=int(vol["n_nondegenerate"]),
        n_degenerate=int(vol["n_degenerate"]),
        degeneracy_auroc=float(vol["degeneracy_auroc"]) if vol["degeneracy_auroc"] is not None else float("nan"),
        within_family_spearman=float(vol["within_family_spearman"]),
        within_family_r2=float(vol["within_family_r2"]),
        family_oracle_r2=float(vol["family_oracle_r2"]),
        family_oracle_margin=float(vol["family_oracle_margin"]),
        within_family_spearman_length_resid=float(vol["within_family_spearman_length_resid"]),
        r2_indist=float(vol["r2_indist"]),
        r2_classmean_indist=float(vol["r2_classmean_indist"]),
        auc_binary=float(vol["auc_binary"]) if vol["auc_binary"] is not None else float("nan"),
        ood_pooled_spearman=float(vol["ood_pooled_spearman"]),
        ood_min_rotation_spearman=float(vol["ood_min_rotation_spearman"]),
        ood_range_uncovered=bool(vol["ood_range_uncovered"]),
        probe_vs_vc_ci_low=ci_low(corr["probe_vs_vc_max"]),
        probe_vs_b3_ci_low=ci_low(corr["probe_vs_b3"]),
        b4_vs_probe_ci_low=ci_low(corr["b4_vs_probe"]),
    )


# ---------------------------------------------------------------------------
# sweep
# ---------------------------------------------------------------------------
def run_sweep(data: dict, cfg: dict, vol: dict, corr_by_k: dict, vin_primary, T, primary_branch) -> dict:
    sweep = {}
    fragile = False
    for name, values in REGISTERED_SWEEP.items():
        rows = []
        branches = set()
        for val in values:
            if name == "correctness_cv_folds":
                corr_k = corr_by_k[int(val)]  # precomputed (k=5 reuses the primary arm)
                vin_k = build_verdict_inputs(vol, corr_k)
                branch = verdict.decide(vin_k, T).value
            else:
                cast = int(val) if name == "min_negatives" else float(val)
                T2 = dataclasses.replace(T, **{name: cast})
                branch = verdict.decide(vin_primary, T2).value
            rows.append({"value": val, "branch": branch, "is_primary": _is_primary(cfg, T, name, val)})
            branches.add(branch)
        stable = len(branches) == 1
        if not stable:
            fragile = True
        sweep[name] = {"points": rows, "stable": stable, "branches_seen": sorted(branches)}
    return {"per_parameter": sweep, "any_fragile": fragile, "primary_branch": primary_branch}


def _is_primary(cfg: dict, T, name: str, val) -> bool:
    primary = cfg["correctness_cv_folds"] if name == "correctness_cv_folds" else getattr(T, name)
    return abs(float(primary) - float(val)) < 1e-12


# ---------------------------------------------------------------------------
# exploratory block (ZERO verdict weight — descriptive only)
# ---------------------------------------------------------------------------
def _safe_spearman(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.size < 3 or a.std() == 0 or b.std() == 0:
        return float("nan")
    return float(spearmanr(a, b)[0])


def _safe_pearson(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.size < 3 or a.std() == 0 or b.std() == 0:
        return float("nan")
    return float(pearsonr(a, b)[0])


def compute_exploratory(data: dict, cfg: dict) -> dict:
    fam = data["family"]
    y = data["volume"]
    ent = data["entropy"]
    diff = data["difficulty"]
    m = correctness_mask(data)
    corr = data["correct"]

    # per-family volume structure (variance decomposition)
    grand = float(y.mean())
    ss_total = float(((y - grand) ** 2).sum())
    ss_between = 0.0
    per_family = {}
    for f in sorted(set(fam.tolist())):
        yf = y[fam == f]
        ss_between += yf.size * (yf.mean() - grand) ** 2
        per_family[str(f)] = {"n": int(yf.size), "mean_volume": float(yf.mean()),
                              "std_volume": float(yf.std(ddof=0))}
    eta2 = float(ss_between / ss_total) if ss_total > 0 else None

    # accuracy by difficulty and by family (answerable only)
    acc_by_diff = {}
    for d in sorted(set(diff[m].tolist())):
        sel = m & (diff == d)
        cvals = corr[sel]
        acc_by_diff[str(int(d))] = {"n": int(sel.sum()), "n_correct": int((cvals == 1).sum()),
                                    "accuracy": float((cvals == 1).mean()) if sel.sum() else None}
    acc_by_family = {}
    for f in sorted(set(fam[m].tolist())):
        sel = m & (fam == f)
        cvals = corr[sel]
        acc_by_family[str(f)] = {"n": int(sel.sum()), "n_correct": int((cvals == 1).sum()),
                                 "accuracy": float((cvals == 1).mean()) if sel.sum() else None}
    acc_by_family_diff = {}
    for f in sorted(set(fam[m].tolist())):
        for d in sorted(set(diff[m].tolist())):
            sel = m & (fam == f) & (diff == d)
            if sel.sum():
                cvals = corr[sel]
                acc_by_family_diff[f"{f}-d{int(d)}"] = {
                    "n": int(sel.sum()), "n_correct": int((cvals == 1).sum()),
                    "accuracy": float((cvals == 1).mean()),
                }

    # confident-error analysis: answerable items labeled incorrect with high verbalized confidence.
    vc_zero = data["vc_zero"]
    vc_cot = data["vc_cot"]
    with warnings.catch_warnings():  # non-answerable rows are all-NaN by design; that is expected
        warnings.simplefilter("ignore", RuntimeWarning)
        vc_max = np.nanmax(np.vstack([vc_zero, vc_cot]), axis=0)
    wrong = m & (corr == 0)
    confident_errors = []
    for i in np.flatnonzero(wrong):
        confident_errors.append({
            "idx": int(data["idx"][i]), "family": str(fam[i]), "difficulty": int(diff[i]),
            "vc_zero": None if np.isnan(vc_zero[i]) else float(vc_zero[i]),
            "vc_cot": None if np.isnan(vc_cot[i]) else float(vc_cot[i]),
            "vc_max": None if np.isnan(vc_max[i]) else float(vc_max[i]),
            "entropy_nats": float(ent[i]), "volume": float(y[i]),
        })
    confident_errors.sort(key=lambda r: (-(r["vc_max"] or 0.0), r["idx"]))
    n_conf_err = int(np.sum(wrong & (vc_max >= 90)))

    # entropy vs volume decoupling (all prompts and answerable subset)
    ent_vol_all = {"pearson": _safe_pearson(y, ent), "spearman": _safe_spearman(y, ent)}
    ent_vol_ans = {"pearson": _safe_pearson(y[m], ent[m]), "spearman": _safe_spearman(y[m], ent[m])}

    # annotation-vs-measured diversity bands are attached by add_diversity_bands (needs the raw rows).
    return {
        "volume_variance_decomposition": {
            "eta_squared_between_family": eta2, "ss_total": ss_total,
            "ss_between_family": float(ss_between), "ss_within_family": float(ss_total - ss_between),
            "per_family": per_family,
            "note": "eta^2 = fraction of log-volume variance BETWEEN families; 1-eta^2 is within-family",
        },
        "volume_vs_length": {
            "pearson_mean_len": _safe_pearson(y, data["mean_len"]),
            "spearman_mean_len": _safe_spearman(y, data["mean_len"]),
            "pearson_std_len": _safe_pearson(y, data["std_len"]),
            "spearman_std_len": _safe_spearman(y, data["std_len"]),
        },
        "entropy_volume_decoupling": {"all_prompts": ent_vol_all, "answerable": ent_vol_ans},
        "calibration": {
            "overall_accuracy": float((corr[m] == 1).mean()) if m.sum() else None,
            "accuracy_by_difficulty": acc_by_diff,
            "accuracy_by_family": acc_by_family,
            "n_by_family_difficulty": acc_by_family_diff,
        },
        "confident_errors": {
            "n_incorrect": int(wrong.sum()),
            "n_confident_incorrect_vcmax_ge_90": n_conf_err,
            "items": confident_errors,
        },
        "_bands_placeholder": None,
    }


def add_diversity_bands(explor: dict, data: dict, rows: list[dict]) -> None:
    """annotation-vs-measured: expected_diversity label vs measured log-volume."""
    y = data["volume"]
    exp = np.array([str(r.get("expected_diversity", "n/a")) for r in rows], dtype=object)
    bands = {}
    for b in sorted(set(exp.tolist())):
        yb = y[exp == b]
        bands[b] = {"n": int(yb.size), "mean_volume": float(yb.mean()),
                    "min_volume": float(yb.min()), "max_volume": float(yb.max())}
    explor["annotation_vs_measured_diversity_bands"] = bands
    explor.pop("_bands_placeholder", None)


# ---------------------------------------------------------------------------
# one full compute pass (pure function of frozen inputs + seeds)
# ---------------------------------------------------------------------------
def compute_all(data: dict, cfg: dict) -> dict:
    vol = compute_volume_arm(data, cfg)
    k_primary = cfg["correctness_cv_folds"]
    corr = compute_correctness_arm(data, cfg, k=k_primary, full_report=True)
    # precompute every distinct k that appears in the correctness_cv_folds sweep (reuse the primary).
    corr_by_k = {k_primary: corr}
    for k_val in REGISTERED_SWEEP["correctness_cv_folds"]:
        if int(k_val) not in corr_by_k:
            corr_by_k[int(k_val)] = compute_correctness_arm(data, cfg, k=int(k_val), full_report=False)
    vin = build_verdict_inputs(vol, corr)
    T = cfg["thresholds"]
    branch = verdict.decide(vin, T).value
    report = verdict.branch_report(vin, T)
    sweep = run_sweep(data, cfg, vol, corr_by_k, vin, T, branch)
    return {
        "volume_arm": vol,
        "correctness_arm": corr,
        "verdict_inputs": dataclasses.asdict(vin),
        "verdict_branch": branch,
        "branch_report": {k: (v if not isinstance(v, float) else float(v)) for k, v in report.items()},
        "sweep": sweep,
    }


def gate_block(res: dict) -> dict:
    """The determinism-critical subset: verdict inputs, branch, and every sweep branch."""
    return {
        "verdict_inputs": res["verdict_inputs"],
        "verdict_branch": res["verdict_branch"],
        "sweep": res["sweep"],
    }


def canonical_hash(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), default=_json_default).encode("utf-8")
    ).hexdigest()


def _json_default(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return float(o)


# ---------------------------------------------------------------------------
# VERDICT.md
# ---------------------------------------------------------------------------
def gate_table_rows(cfg: dict, vin: dict) -> list[dict]:
    T = cfg["thresholds"]
    rows = [
        ("precondition: n_negatives", f">= {T.min_negatives}", vin["n_negatives"], "min_negatives"),
        ("continuous fidelity: R^2 (non-degenerate)", f">= {T.r2_fidelity_min}", vin["r2_nondegenerate"], "r2_fidelity_min"),
        ("continuous fidelity: Spearman (non-degenerate)", f">= {T.spearman_fidelity_min}", vin["spearman_nondegenerate"], "spearman_fidelity_min"),
        ("within-family Spearman", f">= {T.within_family_spearman_min}", vin["within_family_spearman"], "within_family_spearman_min"),
        ("family-mean-oracle margin", f">= {T.family_oracle_margin_min}", vin["family_oracle_margin"], "family_oracle_margin_min"),
        ("length gate: within-family Spearman (length-residualized)", f">= {T.within_family_spearman_min} (require_length_robust={T.require_length_robust})", vin["within_family_spearman_length_resid"], "within_family_spearman_min"),
        ("OOD range covered", "not uncovered", (not vin["ood_range_uncovered"]), "-"),
        ("OOD pooled within-family Spearman", f">= {T.ood_pooled_spearman_min}", vin["ood_pooled_spearman"], "ood_pooled_spearman_min"),
        ("OOD per-family floor (min rotation Spearman)", f">= {T.ood_per_family_floor}", vin["ood_min_rotation_spearman"], "ood_per_family_floor"),
        ("added value: probe vs verbalized (CI-low)", f"> {T.vc_ci_floor}", vin["probe_vs_vc_ci_low"], "vc_ci_floor"),
        ("added value: probe vs entropy B3 (CI-low)", f"> {T.b3_ci_floor}", vin["probe_vs_b3_ci_low"], "b3_ci_floor"),
        ("added value: B4 vs probe (CI-low, must NOT exceed)", f"<= {T.b4_margin_ceiling}", vin["b4_vs_probe_ci_low"], "b4_margin_ceiling"),
        ("B2 reporting: SEP median-split AUROC", f"(auc_binary_min={T.auc_binary_min}; branch-router only)", vin["auc_binary"], "auc_binary_min"),
        ("B2 reporting: class-mean margin (R2_indist - R2_classmean)", f"(reporting only; r2_margin_over_classmean_min={T.r2_margin_over_classmean_min})", vin["r2_indist"] - vin["r2_classmean_indist"], "-"),
        ("reporting: degeneracy classifier AUROC", "(reported, not gated)", vin["degeneracy_auroc"], "-"),
    ]
    return [{"quantity": q, "registered": reg, "observed": obs, "param": p} for q, reg, obs, p in rows]


def _fmt(v):
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        if v != v:
            return "n/a"
        return f"{v:+.4f}"
    return str(v)


def write_verdict_md(cfg: dict, manifest: dict, res: dict, explor: dict, provenance: dict,
                     det: dict) -> None:
    vin = res["verdict_inputs"]
    branch = res["verdict_branch"]
    T = cfg["thresholds"]
    lines: list[str] = []
    A = lines.append

    A("# E3 confirmatory verdict")
    A("")
    A(f"**VERDICT: `{branch}`**")
    A("")
    A("The branch name is the result. Everything below is the evidence the frozen instrument "
      "(`e3_validation.verdict.decide`) used to reach it, plus a clearly separated exploratory "
      "section carrying zero verdict weight.")
    A("")

    A("## Registered vs observed — every gate quantity")
    A("")
    A("| gate quantity | registered bar | observed |")
    A("|---|---|---|")
    for r in gate_table_rows(cfg, vin):
        A(f"| {r['quantity']} | {r['registered']} | {_fmt(r['observed'])} |")
    A("")
    br = res["branch_report"]
    A(f"Precedence outcome: correctness arm evaluable = {br['correctness_arm_evaluable']} "
      f"(n_negatives {br['n_negatives']} vs min_negatives {br['min_negatives']}); "
      f"continuous fidelity present = {br['has_continuous_fidelity']}; "
      f"degenerate/non-degenerate test split = {br['n_degenerate']}/{br['n_nondegenerate']}.")
    A("")

    A("## Sweep stability")
    A("")
    sweep = res["sweep"]
    A(f"Verdict at the registered primaries: `{branch}`. "
      f"Sweep fragility across all registered sweep points: "
      f"**{'FRAGILE — verdict flips inside a sweep band' if sweep['any_fragile'] else 'STABLE — verdict holds across every registered sweep point'}**.")
    A("")
    A("| swept parameter | registered points | verdict stable across band? | branches seen |")
    A("|---|---|---|---|")
    for name, blk in sweep["per_parameter"].items():
        pts = ", ".join(f"{p['value']}{'*' if p['is_primary'] else ''}" for p in blk["points"])
        A(f"| {name} | {pts} | {'yes' if blk['stable'] else 'NO'} | {', '.join(blk['branches_seen'])} |")
    A("")
    A("`*` marks the registered primary. A parameter whose band shows more than one branch is "
      "threshold-fragile (a pre-registered honesty label, not a re-decision).")
    A("")

    A("## Confirmatory vs exploratory separation")
    A("")
    A("**Confirmatory** — only the gate table and sweep above bear on the verdict; the branch is a "
      "deterministic function of exactly the `VerdictInputs` fields, decided by the frozen "
      "`verdict.decide` at the manifest thresholds.")
    A("")
    A("**Exploratory (ZERO verdict weight)** — the following are descriptive observations that did "
      "NOT and cannot move the verdict branch. They are recorded for interpretation only.")
    A("")
    vd = explor["volume_variance_decomposition"]
    A(f"- Between-family volume structure: eta^2 = {vd['eta_squared_between_family']:.3f} "
      f"(within-family fraction {1 - vd['eta_squared_between_family']:.3f}). Per-family mean volume: "
      + "; ".join(f"{k} {v['mean_volume']:+.1f}" for k, v in vd["per_family"].items()) + ".")
    vl = explor["volume_vs_length"]
    A(f"- Volume vs continuation length (verbosity confound): Spearman(mean_len) "
      f"{vl['spearman_mean_len']:+.3f}, Spearman(std_len) {vl['spearman_std_len']:+.3f}.")
    ev = explor["entropy_volume_decoupling"]
    A(f"- Entropy-volume decoupling: Spearman(volume, entropy) all-prompts "
      f"{ev['all_prompts']['spearman']:+.3f}, answerable {ev['answerable']['spearman']:+.3f}.")
    cal = explor["calibration"]
    A(f"- Overall greedy accuracy on the answerable subset: {cal['overall_accuracy']:.3f}. "
      "Accuracy by intended difficulty: "
      + "; ".join(f"d{k} {v['n_correct']}/{v['n']}"
                  + ("" if v["accuracy"] is None else f" ({v['accuracy']:.2f})")
                  for k, v in cal["accuracy_by_difficulty"].items()) + ".")
    A("- Accuracy by family: "
      + "; ".join(f"{k} {v['n_correct']}/{v['n']} ({v['accuracy']:.2f})"
                  for k, v in cal["accuracy_by_family"].items()) + ".")
    dd = cal["n_by_family_difficulty"].get("deduction-d4")
    if dd:
        A(f"- Calibration deviation flagged in the proposal: deduction-d4 = {dd['n_correct']}/{dd['n']} "
          f"correct (accuracy {dd['n_correct']/dd['n']:.2f}); the hardening target for d4 was 0.2-0.4. "
          "This is a corpus-calibration observation, not verdict evidence.")
    ce = explor["confident_errors"]
    A(f"- Confident errors: {ce['n_incorrect']} answerable items are labeled incorrect; "
      f"{ce['n_confident_incorrect_vcmax_ge_90']} of them carry verbalized confidence >= 90 "
      "(max over B1 variants) — the overconfidence pattern the verbalized baseline is expected to show.")
    ab = explor.get("annotation_vs_measured_diversity_bands", {})
    if ab:
        A("- Annotation vs measured diversity bands (expected_diversity label -> measured mean volume): "
          + "; ".join(f"{k} {v['mean_volume']:+.1f} (n={v['n']})" for k, v in ab.items()) + ".")
    A("")

    A("## Provenance")
    A("")
    A(f"- Frozen-config SHA-256: `{cfg['frozen_config_sha256']}`")
    A(f"- Registration status (verbatim from manifest): `{cfg['registration']}`")
    A(f"- Model: `{manifest['frozen_config']['model']['model_id']}` @ "
      f"`{manifest['frozen_config']['model']['model_revision']}` (4-bit).")
    A(f"- Prompts loaded: {provenance['n_loaded']} / {cfg['n_prompts']}; unreadable: "
      f"{provenance['n_unreadable']}.")
    A(f"- Volume-arm exclusions (refusal rule, < {cfg['n_continuations']} valid continuations): "
      f"{provenance['n_excluded_volume']} "
      + (f"(per family: {provenance['exclusion_per_family']})" if provenance['n_excluded_volume'] else "(none)")
      + ".")
    A(f"- Correctness arm: {res['correctness_arm']['n_answerable_scored']} answerable items scored "
      f"({res['correctness_arm']['n_negatives']} negatives, {res['correctness_arm']['n_positives']} "
      f"positives); greedy-truncation exclusions: {provenance['n_truncated']}.")
    A(f"- Determinism: two independent compute passes; gate-block SHA-256 run 1 = `{det['hash_1']}`, "
      f"run 2 = `{det['hash_2']}`; identical = {det['identical']}.")
    A(f"- Analysis wall time: {provenance['wall_s']:.1f} s. Seeds from the manifest formulas "
      f"(base_seed {cfg['base_seed']}).")
    A("")

    A("## Honest limitations")
    A("")
    A("This is one decoder-only model (Qwen2.5-7B-Instruct) at 4-bit quantization, read at a single "
      "layer via one forward pass, on a hand-authored 200-prompt battery across five task families. "
      "The run is UNREGISTERED (`registration: none` in the manifest; pre-registration was waived by "
      "the operator), so the thresholds, though fixed in the committed frozen config before analysis, "
      "carry the weaker evidential status of a frozen-but-unregistered instrument rather than a "
      "timestamped pre-registration. The volume target has no external R^2/Spearman anchor in the "
      "literature (the field reports binarized AUROC), the R^2 bars are modest by construction, and "
      "the correctness arm rests on a normalizer-scored greedy answer. The verdict generalizes no "
      "further than these conditions; the branch name states exactly what was and was not established.")
    A("")

    VERDICT_PATH.write_text("\n".join(lines))


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="wire and compute on partial data (<=190 prompts); do NOT write VERDICT.md")
    args = ap.parse_args()

    t0 = time.time()
    manifest = load_manifest()
    cfg = build_config(manifest)

    rows, unreadable = load_rows(cap=190 if args.dry_run else None)
    if unreadable:
        raise RuntimeError(f"unreadable result files: {unreadable}")
    n_loaded = len(rows)
    if not args.dry_run and n_loaded < cfg["n_prompts"]:
        raise RuntimeError(
            f"confirmatory run requires {cfg['n_prompts']} results; found {n_loaded}. "
            "Re-run with --dry-run to exercise the wiring on partial data."
        )

    data = assemble(rows)

    # exclusion report (per family) via the frozen precondition module.
    excl_report = preconditions.exclusion_report(
        [str(f) for f in data["family"]], data["excluded_volume"].tolist()
    )
    n_truncated = int((data["answerable"] & (~data["excluded_volume"]) & (~data["greedy_eos"])).sum())

    # two independent compute passes for the determinism assertion.
    res1 = compute_all(data, cfg)
    res2 = compute_all(data, cfg)
    h1 = canonical_hash(gate_block(res1))
    h2 = canonical_hash(gate_block(res2))
    identical = (h1 == h2) and (res1["verdict_branch"] == res2["verdict_branch"])
    det = {"hash_1": h1, "hash_2": h2, "identical": identical,
           "branch_1": res1["verdict_branch"], "branch_2": res2["verdict_branch"]}
    if not identical:
        raise RuntimeError(f"DETERMINISM FAILURE: gate hashes differ {h1} != {h2}")

    res = res1
    explor = compute_exploratory(data, cfg)
    add_diversity_bands(explor, data, rows)

    wall_s = time.time() - t0
    provenance = {
        "n_loaded": n_loaded, "n_unreadable": len(unreadable),
        "n_excluded_volume": int(data["excluded_volume"].sum()),
        "exclusion_per_family": dict(excl_report.per_family_excluded),
        "answerable_per_family": dict(excl_report.per_family_answerable),
        "n_truncated": n_truncated, "wall_s": wall_s,
        "dry_run": args.dry_run,
        "families": {str(f): int((data["family"] == f).sum()) for f in sorted(set(data["family"].tolist()))},
    }

    analysis = {
        "mode": "dry-run (partial data, VERDICT.md NOT written)" if args.dry_run else "confirmatory",
        "config": {
            "frozen_config_sha256": cfg["frozen_config_sha256"],
            "registration": cfg["registration"],
            "base_seed": cfg["base_seed"],
            "alpha_grid": list(cfg["alpha_grid"]),
            "inner_cv_folds": cfg["inner_cv_folds"],
            "correctness_cv_folds": cfg["correctness_cv_folds"],
            "bootstrap_n": cfg["bootstrap_n"], "bootstrap_ci_level": cfg["bootstrap_ci_level"],
            "test_fraction": cfg["test_fraction"], "epsilon": cfg["epsilon"],
            "n_continuations": cfg["n_continuations"],
            "thresholds": dataclasses.asdict(cfg["thresholds"]),
            "registered_sweep": REGISTERED_SWEEP,
        },
        "provenance": provenance,
        "determinism": det,
        "verdict_branch": res["verdict_branch"],
        "verdict_inputs": res["verdict_inputs"],
        "branch_report": res["branch_report"],
        "volume_arm": res["volume_arm"],
        "correctness_arm": res["correctness_arm"],
        "sweep": res["sweep"],
        "exploratory_zero_verdict_weight": explor,
    }
    ANALYSIS_PATH.write_text(json.dumps(analysis, indent=2, default=_json_default))

    if not args.dry_run:
        write_verdict_md(cfg, manifest, res, explor, provenance, det)

    _print_summary(analysis, det, args.dry_run)


def _print_summary(analysis: dict, det: dict, dry: bool) -> None:
    print("=" * 88)
    print(f"E3 {'DRY-RUN wiring proof' if dry else 'CONFIRMATORY analysis'} — "
          f"{analysis['provenance']['n_loaded']} prompts")
    print("=" * 88)
    print(f"VERDICT BRANCH: {analysis['verdict_branch']}")
    print(f"determinism: identical={det['identical']} h1={det['hash_1'][:16]} h2={det['hash_2'][:16]}")
    vin = analysis["verdict_inputs"]
    print("\ngate inputs:")
    for k in ["n_negatives", "r2_nondegenerate", "spearman_nondegenerate", "within_family_spearman",
              "family_oracle_margin", "within_family_spearman_length_resid", "ood_pooled_spearman",
              "ood_min_rotation_spearman", "ood_range_uncovered", "auc_binary",
              "probe_vs_vc_ci_low", "probe_vs_b3_ci_low", "b4_vs_probe_ci_low"]:
        print(f"   {k:38s} = {vin[k]}")
    print(f"\nsweep any_fragile = {analysis['sweep']['any_fragile']}")
    for name, blk in analysis["sweep"]["per_parameter"].items():
        print(f"   {name:28s} stable={blk['stable']} branches={blk['branches_seen']}")
    print(f"\nwrote {ANALYSIS_PATH}")
    if not dry:
        print(f"wrote {VERDICT_PATH}")


if __name__ == "__main__":
    main()
