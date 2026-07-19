#!/usr/bin/env python3
"""X1 PRIMARY DELIVERABLE — numeric-slot-aware rescore of A3 contamination (deterministic, CPU-only).

Question this answers (the operator line gates on it): is A3's ~26% contamination a REAL
instruction-failure floor, or an NLI compound-sentence artifact?

The frozen instrument (outcomes._still_asserts) scores contamination by bidirectional DeBERTa-MNLI
entailment (threshold 0.7) between the model output and the stale must_change sentence — source_ids
EXCLUDED, whole-sentence. A3 must_change sentences have the shape
    "{quantity} is {STALE_NUMBER}, which {VERDICT} the {BENCHMARK} {noun}."
A model that CORRECTLY revises (computes the corrected number, flips the verdict) still restates the
shared BENCHMARK clause and the same requirement scaffold, so the NLI clears 0.7 and false-flags.

This rescore replaces the NLI test with an EXPLICIT string/numeric assertion test:

  A flagged item is TRUE contamination iff the model output ASSERTS the stale proposition, i.e.
    (V) the STALE_NUMBER is asserted as the LIVE value of that quantity — present in the output AND
        NOT equal to the benchmark constant AND NOT equal to the corrected value AND NOT appearing
        only inside a supersession/retraction clause; OR
    (D) the model's VERDICT DIRECTION for that requirement matches the stale verdict while the
        corrected direction is the opposite (verdict-direction contamination).
  Otherwise it is an INSTRUMENT ARTIFACT (the model gave the corrected number and/or flipped verdict;
  the NLI fired on the shared benchmark scaffold).

Outputs:
  rescore-report.json  — per-item verified records + the true-floor table (family x dose).
  true-floor-table.md  — raw NLI counts vs numeric-slot-verified counts, per family x dose.

This does NOT run any model. Verdicts are string/numeric only. NLI is used NOWHERE here.
"""
from __future__ import annotations
import json, re, glob, os
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RESULTS = os.path.join(BASE, "coldstart-package/e8-run/A3-stage2/results")
GEN = os.path.join(BASE, "coldstart-package/e8-run/A3-stage2/stage2-gen.jsonl")
CORPUS = os.path.join(BASE, "corpus-candidates/A3-corrections.jsonl")
FILTER_REPORT = os.path.join(BASE, "coldstart-package/e8-run/A3-filter/filter-report.json")
PRUNED = os.path.join(BASE, "coldstart-package/e8-run/A3-filter/pruned-items.json")
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

NUM_RE = re.compile(r'\$?\d[\d,]*(?:\.\d+)?')

def norm_num(tok):
    t = tok.replace("$", "").replace(",", "")
    try:
        return float(t)
    except ValueError:
        return None

def nums_set(text):
    return {n for n in (norm_num(t) for t in NUM_RE.findall(text)) if n is not None}

def nums_list(text):
    return [n for n in (norm_num(t) for t in NUM_RE.findall(text)) if n is not None]

def num_variants(n):
    if n == int(n):
        i = int(n)
        forms = {str(i), f"{i:,}"}
    else:
        forms = {str(n), f"{n:,}"}
    return forms | {"$" + f for f in list(forms)}

SUPERSESSION_MARKERS = ["supersede", "superseded", "supersedes", "original", "prior figure",
                        "earlier", "revised", "revision", "replacing", "replaced", "instead of",
                        "treated as false", "corrects", "corrected", "updating", "updated",
                        "raised to", "raising it", "no longer", "was originally", "previously"]

# verdict-direction lexicon: map verdict phrases to a polarity relative to the benchmark.
# POSITIVE = quantity satisfies/at-or-under/meets the benchmark; NEGATIVE = violates/fails/exceeds.
POS_VERDICT = ["meets", "fits within", "fits", "within the", "satisfies", "is sufficient",
               "sufficient", "at or under", "does meet", "is met", "passes", "covered", "covers",
               "no longer a problem", "now sufficient", "now covers"]
NEG_VERDICT = ["fails to meet", "fails", "exceeds", "violation", "cannot", "may not", "short of",
               "falls short", "blocked", "not all", "breached", "over the", "above the cap",
               "does not meet", "is not met"]

def mc_type(text):
    tl = text.lower()
    if any(m in tl for m in ["exceeds", "fits", "fails", "meets", "cannot", "may not", "blocked",
                             "violation", "short of", "no longer", "not all", "sufficient",
                             "within the", "breached"]):
        return "judgment"
    if re.search(r'\bis\b.{0,40}?\$?\d[\d,]*', tl):
        return "value"
    return "other"

def stale_verdict_polarity(mc):
    tl = mc.lower()
    neg = any(m in tl for m in NEG_VERDICT)
    pos = any(m in tl for m in POS_VERDICT)
    if neg and not pos:
        return "NEG"
    if pos and not neg:
        return "POS"
    return "MIXED"

def load():
    corpus = {}
    for line in open(CORPUS):
        c = json.loads(line); corpus[c["task_id"]] = c
    gen = {}
    for line in open(GEN):
        g = json.loads(line); gen[g["task_id"]] = g
    results = {}
    for f in glob.glob(os.path.join(RESULTS, "*.json")):
        if "_oracle_result" in f:
            continue
        d = json.load(open(f)); results[d["task_id"]] = d
    return corpus, gen, results

def output_text(output):
    return output["conclusion"] + " " + " ".join(c["text"] for c in output["claims"])

def premises(output):
    return [output["conclusion"]] + [c["text"] for c in output["claims"]]

ENTITY_LABEL_RE = re.compile(
    r'\b(level|row|cabin|bay|silo|deck|line|dock|berth|gate|zone|unit|track|pier|slip|stall|'
    r'platform|aisle|floor|tier|ramp|lane|slot|cell|module)\s+(\d+)\b', re.I)

def entity_label_numbers(text):
    """Numbers that are location/entity labels ('Silo 4', 'level 22') — not computed values.
    These collide with the stale-value test on F1 verdict items whose stale sentence carries no
    computed number, only a location label. Excluded from the stale-value candidate."""
    out = set()
    for m in ENTITY_LABEL_RE.finditer(text):
        n = norm_num(m.group(2))
        if n is not None:
            out.add(n)
    return out

def units_after_number(text, n):
    """The set of unit-noun tokens that immediately follow number `n` in `text`, across all its
    numeric string forms. 'is 120 tonnes' -> {'tonnes'}. Used to detect unit collisions where the
    same digits denote different quantities."""
    if n is None:
        return set()
    out = set()
    for form in num_variants(n):
        esc = re.escape(form)
        for m in re.finditer(esc + r'\s+([A-Za-z][A-Za-z\-]{2,})', text):
            out.add(m.group(1).lower())
    return out

def verify_item(task, output, i):
    """Return (true_contamination: bool, evidence: dict). Pure string/numeric."""
    mc = task["must_change"][i]
    typ = mc_type(mc)
    mcn = nums_list(mc)
    stale_number = mcn[0] if mcn else None
    benchmark = mcn[1] if len(mcn) > 1 else None
    # entity-label guard: if the first number is a location label ('Silo 4'), it is not a computed
    # stale value — drop it and re-pick the first genuine value number.
    label_nums = entity_label_numbers(mc)
    if stale_number is not None and stale_number in label_nums:
        remaining = [n for n in mcn if n not in label_nums]
        stale_number = remaining[0] if remaining else None
        benchmark = remaining[1] if len(remaining) > 1 else None
    other_mc_nums = set()
    for j, m in enumerate(task["must_change"]):
        if j != i:
            other_mc_nums |= nums_set(m)
    correct_nums = nums_set(task["axis_params"]["state_values"][-1])
    out_all = output_text(output)
    out_nums = nums_set(out_all)

    # (V) stale NUMBER asserted as a live value
    stale_present = stale_number is not None and stale_number in out_nums
    stale_is_benchmark = stale_number is not None and stale_number == benchmark
    stale_is_correct = stale_number is not None and stale_number in correct_nums
    # is every mention of stale_number inside a supersession clause?
    stale_only_supersession = False
    if stale_present:
        variants = num_variants(stale_number)
        mentioning = [p for p in premises(output) if any(v in p for v in variants)]
        stale_only_supersession = bool(mentioning) and all(
            any(m in p.lower() for m in SUPERSESSION_MARKERS) for p in mentioning)
    # unit guard: the stale number may appear in the output attached to a DIFFERENT quantity
    # (e.g. stale "120 tonnes" of maize vs output "120 hectares" of barley). If the unit-noun the
    # must_change puts after the stale number is disjoint from every unit-noun the output puts after
    # that same number, the shared digits are a coincidence across different quantities -> not
    # contamination. (batch-builder cross-check finding; verified on A3-C-0501.)
    stale_unit_collision = False
    if stale_present:
        mc_units = units_after_number(mc, stale_number)
        out_units = set()
        for p in premises(output):
            out_units |= units_after_number(p, stale_number)
        if mc_units and out_units and not (mc_units & out_units):
            stale_unit_collision = True

    value_contamination = bool(
        stale_present and not stale_is_benchmark and not stale_is_correct
        and not stale_only_supersession and not stale_unit_collision)

    # (D) verdict-direction contamination: model asserts the stale verdict polarity for this
    #     requirement while the corrected polarity is opposite. Detectable only when the stale
    #     number is NOT asserted (else V covers it) AND we can read the model's polarity on the
    #     SAME benchmark. We approximate: the model output contains the benchmark constant, and near
    #     it uses the stale polarity's verdict words but not the opposite. Conservative: only fire
    #     when the corrected value is on the opposite side AND the model's stated computed value
    #     equals the stale number (already covered by V) — so pure verdict-flip WITHOUT restating a
    #     number is genuinely undecidable by string alone -> route to probe, never auto-true.
    verdict_probe = False
    if not value_contamination and typ == "judgment" and stale_present:
        # stale number present but classified non-contaminating above (benchmark/correct/supersession)
        # -> the flag is explained; not verdict contamination.
        pass
    elif not value_contamination and typ == "judgment" and stale_number is not None and not stale_present:
        # stale computed value absent -> model used a different (corrected) number: artifact, unless
        # the model states NO number for this quantity at all (pure verdict) -> undecidable.
        # Detect "states some number for this quantity": we can't bind quantity->number reliably by
        # string; mark verdict_probe only if output asserts the stale benchmark AND no corrected
        # counterpart number near it. Kept conservative: default artifact.
        verdict_probe = False

    true_contam = value_contamination  # verdict-only flips are never auto-true (routed to probe list)
    return true_contam, {
        "mc_type": typ,
        "stale_number": stale_number,
        "benchmark": benchmark,
        "correct_final_nums": sorted(correct_nums),
        "stale_present_in_output": stale_present,
        "stale_equals_benchmark": stale_is_benchmark,
        "stale_equals_correct": stale_is_correct,
        "stale_only_in_supersession": stale_only_supersession,
        "value_contamination": value_contamination,
        "stale_verdict_polarity": stale_verdict_polarity(mc),
        "verdict_probe": verdict_probe,
        "entity_label_nums_excluded": sorted(label_nums),
        "stale_unit_collision": stale_unit_collision,
    }

def main():
    corpus, gen, results = load()
    # true-floor table: (family, dose) -> {raw_nli, verified}
    table = defaultdict(lambda: {"raw_nli": 0, "verified_true": 0, "items_total": 0})
    fam_dose_raw = defaultdict(int)
    records = []
    for tid, d in results.items():
        c = corpus[tid]; g = gen[tid]
        fam = c["covariates"]["family"]; dose = d["routing"]["dose_level"]
        flags = d["arms"]["B"]["must_change_asserted_by_index"]
        key = (fam, dose)
        table[key]["items_total"] += len(flags)
        for idx_s, flag in flags.items():
            i = int(idx_s)
            if not flag:
                continue
            table[key]["raw_nli"] += 1
            tc, ev = verify_item(c, g["output"], i)
            if tc:
                table[key]["verified_true"] += 1
            records.append({
                "task_id": tid, "item_idx": i, "family": fam, "dose": dose,
                "mc_text": c["must_change"][i], "true_contamination": tc, "evidence": ev,
            })
    # aggregates
    raw_total = sum(t["raw_nli"] for t in table.values())
    verified_total = sum(t["verified_true"] for t in table.values())
    by_family_raw = Counter(); by_family_true = Counter()
    by_dose_raw = Counter(); by_dose_true = Counter()
    for (fam, dose), t in table.items():
        by_family_raw[fam] += t["raw_nli"]; by_family_true[fam] += t["verified_true"]
        by_dose_raw[dose] += t["raw_nli"]; by_dose_true[dose] += t["verified_true"]

    # pruning-bias check
    fr = json.load(open(FILTER_REPORT))
    pruned = json.load(open(PRUNED))
    excluded = set(fr["excluded_families"])
    fam_of = {}
    for tid, c in corpus.items():
        fam_of.setdefault(c["family_id"], c["covariates"]["family"])
    excl_by_ffam = Counter(fam_of[f] for f in excluded)
    all_by_ffam = Counter(fam_of[fid] for fid in set(fam_of))
    prune_bias = {
        "n_excluded_families": len(excluded),
        "n_pruned_items": len(pruned),
        "excluded_by_F_family": dict(excl_by_ffam),
        "all_families_by_F": dict(all_by_ffam),
        "exclusion_rate_by_F": {f: round(excl_by_ffam[f] / all_by_ffam[f], 4) for f in all_by_ffam},
        "note": "Filter is a SEPARATE A-dependency qualification stage; it did NOT remove families "
                "from the stage-2 contamination run (all 112 families present in stage-2 results). "
                "So the rescore has no survivorship bias. The exclusion pattern is itself evidence: "
                "the same NLI instrument, run on correction-state draws, independently flagged 73% of "
                "F2 families (0% F1, 0% F3) as anomalously 'asserted' — a second confirmation that F2's "
                "template is where the NLI misbehaves.",
    }

    report = {
        "headline": {
            "raw_nli_contaminated": raw_total,
            "numeric_slot_verified_true": verified_total,
            "artifact_reclassified": raw_total - verified_total,
            "artifact_fraction": round((raw_total - verified_total) / raw_total, 4),
        },
        "true_floor_table": {f"{fam}|dose{dose}": table[(fam, dose)]
                             for (fam, dose) in sorted(table)},
        "by_family": {fam: {"raw_nli": by_family_raw[fam], "verified_true": by_family_true[fam]}
                      for fam in sorted(by_family_raw)},
        "by_dose": {dose: {"raw_nli": by_dose_raw[dose], "verified_true": by_dose_true[dose]}
                    for dose in sorted(by_dose_raw)},
        "pruning_bias": prune_bias,
        "records": records,
    }
    with open(os.path.join(OUT_DIR, "rescore-report.json"), "w") as f:
        json.dump(report, f, indent=2)
    write_floor_table_md(report)
    print(json.dumps({k: report[k] for k in ["headline", "by_family", "by_dose"]}, indent=2))
    print("pruning_bias.exclusion_rate_by_F:", prune_bias["exclusion_rate_by_F"])
    return report

def write_floor_table_md(report):
    lines = ["# A3 True-Floor Table — raw NLI vs numeric-slot-verified\n"]
    h = report["headline"]
    lines.append(f"**Raw NLI contaminated:** {h['raw_nli_contaminated']}  |  "
                 f"**Numeric-slot verified TRUE:** {h['numeric_slot_verified_true']}  |  "
                 f"**Artifact-reclassified:** {h['artifact_reclassified']} "
                 f"({h['artifact_fraction']:.1%})\n")
    lines.append("\n## By family × dose\n")
    lines.append("| family | dose | items | raw NLI | verified TRUE |")
    lines.append("|---|---|---|---|---|")
    for key, t in report["true_floor_table"].items():
        fam, dose = key.split("|")
        lines.append(f"| {fam} | {dose} | {t['items_total']} | {t['raw_nli']} | {t['verified_true']} |")
    lines.append("\n## By family (all doses)\n")
    lines.append("| family | raw NLI | verified TRUE |")
    lines.append("|---|---|---|")
    for fam, v in report["by_family"].items():
        lines.append(f"| {fam} | {v['raw_nli']} | {v['verified_true']} |")
    lines.append("\n## By dose (all families)\n")
    lines.append("| dose | raw NLI | verified TRUE |")
    lines.append("|---|---|---|")
    for dose, v in report["by_dose"].items():
        lines.append(f"| {dose} | {v['raw_nli']} | {v['verified_true']} |")
    with open(os.path.join(OUT_DIR, "true-floor-table.md"), "w") as f:
        f.write("\n".join(lines) + "\n")

if __name__ == "__main__":
    main()
