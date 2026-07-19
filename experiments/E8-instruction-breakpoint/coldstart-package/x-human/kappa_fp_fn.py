#!/usr/bin/env python3
"""
X-HUMAN kappa / FP-FN computation. Consumes FILLED annotation packets + the provenance channel,
produces the per-cell Cohen's kappa, raw-agreement + deflation, instrument-vs-human confusion
matrices, near-threshold band, and the R1-R5 adjudication (X-HUMAN-PROTOCOL.md §5-§7).

INPUT it reads:
  labels/<annotator>.json  — one file per human annotator: {packet_item_id: "YES"|"NO"|"UNSURE"}.
                              THESE ARE HUMAN-PRODUCED. This script never writes them and refuses
                              to run if the only labels it can find are machine-authored (a label
                              file must declare "annotator_kind":"human").
  packets/_provenance/item_provenance.json — the stratum + instrument flags, joined back AFTER
                              labels exist (kept out of packets so annotators never saw it).
  packets/*batch*.json     — for the scored-sentence/family metadata and to enumerate items.

It DELIBERATELY does not read any Sonnet pre-label channel; §1.5 auxiliary labels live elsewhere
and are excluded from every statistic here (arXiv:2605.16354 — auxiliary, never substitutive).

Cohen's kappa and the exact binomial are implemented locally (no scipy dependency required for the
core; scipy used only if present for the exact binomial, else a documented normal fallback with a
warning). Oracle self-test: python3 kappa_fp_fn.py --selftest
"""
import json, os, glob, argparse, math
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))
PACKETS = os.path.join(HERE, "packets")
PROV = os.path.join(PACKETS, "_provenance", "item_provenance.json")
LABELS_DIR = os.path.join(HERE, "labels")

# ----------------------------------------------------------------- core stats
def cohens_kappa(labels_a, labels_b):
    """Cohen's kappa over paired categorical labels (lists aligned by item). Returns (kappa, n, po)."""
    pairs = [(a, b) for a, b in zip(labels_a, labels_b) if a is not None and b is not None]
    n = len(pairs)
    if n == 0:
        return None, 0, None
    cats = sorted(set(a for a, _ in pairs) | set(b for _, b in pairs))
    po = sum(1 for a, b in pairs if a == b) / n
    # expected agreement
    ca = Counter(a for a, _ in pairs); cb = Counter(b for _, b in pairs)
    pe = sum((ca[c] / n) * (cb[c] / n) for c in cats)
    if pe == 1.0:
        # degenerate: both annotators used one category identically -> kappa undefined; report po
        return 1.0 if po == 1.0 else 0.0, n, po
    kappa = (po - pe) / (1 - pe)
    return kappa, n, po

def exact_binom_upper95(k, n):
    """One-sided 95% upper confidence bound on a proportion given k successes in n (Clopper-Pearson)."""
    if n == 0:
        return None
    try:
        from scipy.stats import beta
        return 1.0 if k == n else beta.ppf(0.95, k + 1, n - k)
    except Exception:
        # normal approx fallback (documented; core gates use counts not this bound)
        p = k / n
        return min(1.0, p + 1.645 * math.sqrt(max(p * (1 - p), 1e-9) / n))

# ----------------------------------------------------------------- IO
def load_labels():
    """Load human label files. Each: {"annotator_id":..,"annotator_kind":"human","labels":{item_id:val}}."""
    out = {}
    for f in sorted(glob.glob(os.path.join(LABELS_DIR, "*.json"))):
        d = json.load(open(f))
        if d.get("annotator_kind") != "human":
            raise SystemExit(f"REFUSING: {f} is not declared annotator_kind=human. "
                             "kappa_fp_fn computes only over human labels.")
        out[d["annotator_id"]] = {k: _norm(v) for k, v in d["labels"].items()}
    return out

def _norm(v):
    v = (v or "").strip().upper()
    return v if v in ("YES", "NO", "UNSURE") else None

def load_items():
    items = {}
    for f in glob.glob(os.path.join(PACKETS, "*batch*.json")):
        for it in json.load(open(f))["items"]:
            items[it["packet_item_id"]] = it
    return items

def consensus(item_id, ann):
    """>=2-annotator consensus. Returns ('YES'/'NO', n_labels, adjudicated_bool) or (None,..) if <2 or tie."""
    votes = [ann[a][item_id] for a in ann if item_id in ann[a] and ann[a][item_id] is not None]
    votes = [v for v in votes if v in ("YES", "NO")]  # UNSURE excluded from consensus; forces adjudication
    if len(votes) < 2:
        return None, len(votes), False
    c = Counter(votes)
    if len(c) == 1:
        return votes[0], len(votes), False
    # disagreement -> needs adjudicator (a 3rd label). If a majority exists, use it and mark adjudicated.
    top, n_top = c.most_common(1)[0]
    if n_top > len(votes) / 2:
        return top, len(votes), True
    return None, len(votes), True  # tie, unresolved -> reported, not counted

# ----------------------------------------------------------------- report
def compute(strict=True):
    ann = load_labels()
    items = load_items()
    prov = json.load(open(PROV))
    if not ann:
        return {"status": "NO_HUMAN_LABELS", "note": "labels/ empty; results are a skeleton until humans annotate."}

    # per (dimension, regime, family_type) cell: inter-annotator kappa + instrument-vs-human
    cells = defaultdict(lambda: {"human_a": [], "human_b": [], "ids": []})
    # instrument-vs-human accumulation
    inst = defaultdict(lambda: {"nli": Counter(), "v2": Counter()})  # keyed by cell -> confusion cells
    fn_clean = []      # S-CLEAN human-found contamination (R3)
    e5_counts = defaultdict(Counter)  # arm -> human YES/NO on E5 census

    ann_ids = list(ann)
    for iid, it in items.items():
        p = prov.get(iid, {})
        dim = it["dimension"]; reg = it["regime"]; fam = it.get("family_type")
        cell = (dim, reg, fam)
        # first two annotators who labelled this item (pairwise kappa base)
        labs = [(a, ann[a][iid]) for a in ann_ids if iid in ann[a] and ann[a][iid] in ("YES", "NO")]
        if len(labs) >= 2:
            cells[cell]["human_a"].append(labs[0][1])
            cells[cell]["human_b"].append(labs[1][1])
            cells[cell]["ids"].append(iid)
        cons, nlab, adj = consensus(iid, ann)
        if cons is None:
            continue
        human_pos = (cons == "YES")  # YES = contaminated / kept depending on dim
        # instrument flags from provenance
        if dim == "contamination":
            nli_pos = bool(p.get("nli_flagged")) or (p.get("stratum") in ("S-DISPUTED",)) or bool(p.get("nli_asserted"))
            # for E5, nli flag = it was in the contaminated census (nli_asserted True)
            if reg == "E5":
                nli_pos = bool(p.get("nli_asserted"))
            _tally(inst[cell]["nli"], nli_pos, human_pos)
            # v2: for A3, v2 said clean on all disputed (verified_true=False); v2 flagged = v2_verified_true
            v2_pos = bool(p.get("v2_verified_true"))
            _tally(inst[cell]["v2"], v2_pos, human_pos)
            if p.get("stratum") == "S-CLEAN" and human_pos:
                fn_clean.append(iid)  # neither instrument flagged, human says contaminated -> R3 FN
            if reg == "E5" and p.get("stratum") == "E5-CONTAM-CENSUS":
                e5_counts[p.get("arm")]["YES" if human_pos else "NO"] += 1

    # assemble per-cell report
    cell_report = {}
    for cell, d in sorted(cells.items(), key=lambda kv: str(kv[0])):
        k, n, po = cohens_kappa(d["human_a"], d["human_b"])
        cell_report[str(cell)] = {
            "n_paired": n, "cohens_kappa": _r(k), "raw_agreement": _r(po),
            "deflation_raw_minus_kappa": _r((po - k) if (po is not None and k is not None) else None),
            "kappa_gate": ("STRONG" if (k or 0) > 0.8 else "ACCEPTABLE" if (k or 0) > 0.6 else "FAIL"),
            "small_sample": n < 30,
        }
    inst_report = {}
    for cell, d in inst.items():
        inst_report[str(cell)] = {"nli": _confusion(d["nli"]), "v2": _confusion(d["v2"])}

    # R1-R5 adjudication (only for cells with data)
    verdicts = adjudicate(cell_report, inst_report, fn_clean, e5_counts, items, prov, ann)
    return {"status": "COMPUTED", "annotators": ann_ids,
            "per_cell_interannotator": cell_report,
            "instrument_vs_human": inst_report,
            "R3_false_negatives_in_S_CLEAN": fn_clean,
            "E5_census_human_counts_by_arm": {k: dict(v) for k, v in e5_counts.items()},
            "verdicts": verdicts}

def _tally(conf, inst_pos, human_pos):
    if inst_pos and human_pos: conf["TP"] += 1
    elif inst_pos and not human_pos: conf["FP"] += 1
    elif not inst_pos and human_pos: conf["FN"] += 1
    else: conf["TN"] += 1

def _confusion(c):
    tot_flag = c["TP"] + c["FP"]; tot_humanpos = c["TP"] + c["FN"]
    return {"TP": c["TP"], "FP": c["FP"], "FN": c["FN"], "TN": c["TN"],
            "fp_rate_of_flagged": _r(c["FP"] / tot_flag) if tot_flag else None,
            "fn_rate_of_human_pos": _r(c["FN"] / tot_humanpos) if tot_humanpos else None}

def adjudicate(cell_report, inst_report, fn_clean, e5_counts, items, prov, ann):
    v = {}
    # R3 first (overrides R1)
    v["R3_false_negative_leak"] = ("FIRES — >=1 human-found contamination in S-CLEAN; both instruments leak; overrides R1"
                                   if len(fn_clean) >= 1 else "clear (0 human-found echoes in S-CLEAN sampled)")
    # R1/R2 on A3 contamination disputed census
    a3_true = _count_human_contam_in_disputed(items, prov, ann)
    if a3_true is not None:
        ub = exact_binom_upper95(a3_true, 200)
        if a3_true <= 3:
            v["R1_v2_validated"] = f"candidate FIRES — {a3_true}/200 flagged human-confirmed contaminated (upper95≈{_r(ub)}); pending kappa>0.8 on flagged cells"
            v["R2_v2_refuted"] = f"does not fire ({a3_true} < 12)"
        elif a3_true >= 12:
            v["R2_v2_refuted"] = f"FIRES — {a3_true}/200 (>=6%) human-confirmed contaminated; operator line REOPENS; X1 §7 withdrawn"
            v["R1_v2_validated"] = "does not fire"
        else:
            v["R1_v2_validated"] = f"ambiguous — {a3_true}/200 between thresholds (3<x<12); report and escalate"
            v["R2_v2_refuted"] = f"ambiguous ({a3_true})"
    # R5 E5 integrity
    if e5_counts:
        c = e5_counts.get("C", Counter()); b = e5_counts.get("B", Counter())
        c_yes = c.get("YES", 0); b_yes = b.get("YES", 0)
        v["R5_e5_integrity"] = (f"C human-confirmed contaminated={c_yes}/11, B={b_yes}/1; "
                                + ("C>B ordering preserved — H-RELEASE refutation stands on human labels"
                                   if c_yes > b_yes else
                                   "C>B ordering COLLAPSED — E5 'release lost' verdict is instrument-contaminated; re-adjudicate under v2"))
    return v

def _count_human_contam_in_disputed(items, prov, ann):
    n = 0; seen = 0
    for iid, it in items.items():
        if it["dimension"] != "contamination" or it["regime"] != "A3": continue
        if prov.get(iid, {}).get("stratum") != "S-DISPUTED": continue
        cons, _, _ = consensus(iid, ann)
        if cons is None: continue
        seen += 1
        if cons == "YES": n += 1
    return n if seen else None

def _r(x, nd=4):
    return round(x, nd) if isinstance(x, (int, float)) else x

# ----------------------------------------------------------------- oracle self-test
def selftest():
    fails = []
    # kappa: perfect agreement
    k, n, po = cohens_kappa(["YES", "NO", "YES"], ["YES", "NO", "YES"])
    if not (abs(k - 1.0) < 1e-9 and po == 1.0): fails.append(f"perfect-agreement kappa={k}")
    # kappa: chance-level (both 50/50 independent). Known: po=0.5, pe=0.5 -> kappa 0
    a = ["YES", "YES", "NO", "NO"]; b = ["YES", "NO", "YES", "NO"]
    k2, _, _ = cohens_kappa(a, b)
    if abs(k2 - 0.0) > 1e-9: fails.append(f"chance kappa={k2} (expected 0)")
    # deflation: high raw, modest kappa (skewed prevalence) — 18/20 agree but mostly on NO
    a = ["NO"] * 18 + ["YES", "YES"]; b = ["NO"] * 17 + ["YES", "NO", "YES"]
    k3, _, po3 = cohens_kappa(a, b)
    if not (po3 >= 0.85 and k3 < po3): fails.append(f"deflation not exhibited po={po3} k={k3}")
    # exact binom upper95 of 0/200 ~= 0.0149
    ub = exact_binom_upper95(0, 200)
    if ub is None or abs(ub - 0.0149) > 0.003: fails.append(f"binom 0/200 upper95={ub}")
    # _tally confusion correctness
    c = Counter(); _tally(c, True, False)  # instrument flagged, human clean -> FP
    if c["FP"] != 1: fails.append("tally FP wrong")
    # consensus: 2 agree -> that label; UNSURE excluded
    class _A(dict): pass
    ann = {"x": {"i1": "NO"}, "y": {"i1": "NO"}, "z": {"i1": "UNSURE"}}
    cons, nlab, adj = consensus("i1", ann)
    if cons != "NO": fails.append(f"consensus={cons}")
    if fails:
        print("KAPPA SELFTEST FAIL:"); [print("  -", f) for f in fails]; return 1
    print("KAPPA SELFTEST PASS — kappa, deflation, exact-binom, tally, consensus all correct.")
    return 0

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        raise SystemExit(selftest())
    r = compute()
    print(json.dumps(r, indent=2))
    if r.get("status") == "NO_HUMAN_LABELS":
        print("\n(labels/ is empty — this is expected until Vlad/recruited annotators fill packets.)")
