#!/usr/bin/env python3
"""X1 FULL RESCORE (task #18) — numeric-slot-aware rescore of ALL 1,428 A3 items.

The prior rescore.py covered only the 200 NLI-flagged must_change items. This covers the FULL
item pool the frozen instrument scored across the 336 stage-2 records:

  756 must_change items  (asserted=True => contamination; 200 flagged, 556 never-flagged)
  672 must_persist items (asserted=False => dropped/completeness-failure; 168 dropped, 504 kept)
  ------------------------------------------------------------------------------------------------
  1,428 items total.

Two audits, deterministic string/numeric only, NLI used nowhere:

  (A) must_change TRUE-CONTAMINATION rescore (reuses rescore.verify_item). Applied to ALL 756:
      - the 200 NLI-flagged: confirm the artifact reclassification (expect ~0 true).
      - the 556 NLI-NEVER-flagged: FALSE-NEGATIVE AUDIT — did the NLI MISS a real stale echo?
        For each, run the SAME assertion test; any that verify TRUE are stale echoes the instrument
        missed (a headline if found).

  (B) must_persist COMPLETENESS check for all 672. Contamination is N/A (persist facts have no stale
      variant), so these are contamination-clean by construction. Reported separately: does the model
      output actually contain the persist fact (numeric/lexical presence)? The 168 the NLI marked
      dropped are re-examined to distinguish genuine drops from NLI presence-miss artifacts.

Outputs:
  full-rescore-report.json  — per-item records (all 1,428) + aggregates + false-negative audit.
  true-floor-table.md       — UPDATED: full family x dose table, raw-vs-verified, ALL items.
"""
from __future__ import annotations
import sys, os, json, glob, re
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rescore import (verify_item, mc_type, nums_set, nums_list, num_variants,
                     SUPERSESSION_MARKERS, BASE, RESULTS, GEN, CORPUS, load, output_text, premises)

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------- must_persist completeness check ----------
def persist_present(task, output, persist_text):
    """Deterministic: is the persist fact asserted in the output?
    Signal 1 (numeric): the persist fact's distinguishing number appears in the output.
    Signal 2 (lexical): a content-noun overlap heuristic (>=2 shared content tokens of len>=4).
    This is a PRESENCE proxy, NOT the NLI; used to distinguish genuine drops from NLI presence-miss.
    """
    pnums = nums_set(persist_text)
    out_all = output_text(output)
    out_nums = nums_set(out_all)
    numeric_hit = bool(pnums & out_nums)
    # lexical overlap on content tokens
    def content_tokens(s):
        return {w for w in re.findall(r"[A-Za-z][A-Za-z\-]{3,}", s.lower())
                if w not in STOP}
    pt = content_tokens(persist_text)
    ot = content_tokens(out_all)
    shared = pt & ot
    lexical_hit = len(shared) >= 2
    return {
        "numeric_hit": numeric_hit,
        "lexical_shared_tokens": sorted(shared)[:8],
        "lexical_hit": lexical_hit,
        "present_proxy": numeric_hit or lexical_hit,
    }

STOP = {"the", "and", "that", "this", "with", "from", "into", "under", "over", "than",
        "which", "asked", "wants", "want", "cost", "price", "alone", "fixed", "total",
        "monthly", "daily", "weekly", "operates", "reports", "single", "these", "their"}

def main():
    corpus, gen, results = load()

    mc_records = []
    mp_records = []
    # false-negative audit accumulators
    fn_flagged = []   # never-flagged-by-NLI but verify TRUE (missed echoes) -> HEADLINE if nonempty
    # true-floor table over must_change: (family, dose) -> counts
    table = defaultdict(lambda: {"mc_items": 0, "raw_nli_flag": 0, "verified_true": 0,
                                 "never_flag_verified_true": 0})

    for tid, d in results.items():
        c = corpus[tid]; g = gen[tid]
        output = g["output"]
        fam = c["covariates"]["family"]; dose = d["routing"]["dose_level"]
        key = (fam, dose)

        # ---- must_change: score ALL items ----
        mc_flags = d["arms"]["B"]["must_change_asserted_by_index"]
        for idx_s, nli_flag in mc_flags.items():
            i = int(idx_s)
            tc, ev = verify_item(c, output, i)
            table[key]["mc_items"] += 1
            if nli_flag:
                table[key]["raw_nli_flag"] += 1
            if tc:
                table[key]["verified_true"] += 1
                if not nli_flag:
                    table[key]["never_flag_verified_true"] += 1
                    fn_flagged.append({"task_id": tid, "item_idx": i, "family": fam, "dose": dose,
                                       "mc_text": c["must_change"][i], "evidence": ev})
            mc_records.append({
                "task_id": tid, "item_idx": i, "family": fam, "dose": dose,
                "mc_text": c["must_change"][i], "nli_flagged": bool(nli_flag),
                "verified_true_contamination": tc, "evidence": ev,
            })

        # ---- must_persist: completeness (contamination N/A) ----
        mp_flags = d["arms"]["B"].get("must_persist_asserted", [])
        persist = c.get("must_persist", [])
        for j, nli_kept in enumerate(mp_flags):
            ptext = persist[j] if j < len(persist) else None
            pres = persist_present(c, output, ptext) if ptext else None
            mp_records.append({
                "task_id": tid, "persist_idx": j, "family": fam, "dose": dose,
                "persist_text": ptext,
                "nli_asserted_kept": bool(nli_kept),
                "presence_proxy": pres,
                # NLI says dropped but our proxy finds it present => NLI presence-miss artifact candidate
                "nli_drop_but_present": (not nli_kept) and bool(pres and pres["present_proxy"]),
            })

    # ---- aggregates ----
    raw_total = sum(t["raw_nli_flag"] for t in table.values())
    verified_true_total = sum(t["verified_true"] for t in table.values())
    never_flag_true_total = sum(t["never_flag_verified_true"] for t in table.values())
    mc_total = sum(t["mc_items"] for t in table.values())

    by_family = defaultdict(lambda: {"raw_nli": 0, "verified_true": 0})
    by_dose = defaultdict(lambda: {"raw_nli": 0, "verified_true": 0})
    for (fam, dose), t in table.items():
        by_family[fam]["raw_nli"] += t["raw_nli_flag"]
        by_family[fam]["verified_true"] += t["verified_true"]
        by_dose[dose]["raw_nli"] += t["raw_nli_flag"]
        by_dose[dose]["verified_true"] += t["verified_true"]

    # must_persist aggregates
    mp_total = len(mp_records)
    mp_kept = sum(1 for r in mp_records if r["nli_asserted_kept"])
    mp_dropped = mp_total - mp_kept
    mp_drop_but_present = sum(1 for r in mp_records if r["nli_drop_but_present"])

    report = {
        "headline": {
            "total_items": mc_total + mp_total,
            "must_change_items": mc_total,
            "must_persist_items": mp_total,
            "mc_raw_nli_contaminated": raw_total,
            "mc_verified_true_contamination": verified_true_total,
            "mc_artifact_reclassified": raw_total - verified_true_total,
            "mc_never_flagged_items": mc_total - raw_total,
            "mc_never_flagged_verified_true": never_flag_true_total,
            "false_negative_audit": "PASS (0 missed echoes)" if never_flag_true_total == 0
                                    else f"HEADLINE: {never_flag_true_total} missed echoes",
            "mp_kept": mp_kept,
            "mp_nli_dropped": mp_dropped,
            "mp_nli_drop_but_present_proxy": mp_drop_but_present,
        },
        "true_floor_table_mc": {f"{fam}|dose{dose}": table[(fam, dose)]
                                for (fam, dose) in sorted(table)},
        "mc_by_family": {fam: dict(by_family[fam]) for fam in sorted(by_family)},
        "mc_by_dose": {dose: dict(by_dose[dose]) for dose in sorted(by_dose)},
        "false_negative_missed_echoes": fn_flagged,
        "mc_records": mc_records,
        "mp_records": mp_records,
    }
    with open(os.path.join(OUT_DIR, "full-rescore-report.json"), "w") as f:
        json.dump(report, f, indent=2)
    write_full_table_md(report)
    print(json.dumps(report["headline"], indent=2))
    return report

def write_full_table_md(report):
    h = report["headline"]
    lines = ["# A3 True-Floor Table — FULL rescore (all 1,428 items)\n"]
    lines.append(f"**Total items:** {h['total_items']} = {h['must_change_items']} must_change "
                 f"+ {h['must_persist_items']} must_persist\n")
    lines.append(f"\n**must_change:** raw NLI contaminated {h['mc_raw_nli_contaminated']} → "
                 f"numeric-slot verified TRUE {h['mc_verified_true_contamination']} "
                 f"(artifact {h['mc_artifact_reclassified']}). "
                 f"Never-flagged items {h['mc_never_flagged_items']}, of which verified-true "
                 f"{h['mc_never_flagged_verified_true']}. "
                 f"**False-negative audit: {h['false_negative_audit']}.**\n")
    lines.append(f"\n**must_persist (completeness, contamination N/A):** kept {h['mp_kept']}, "
                 f"NLI-dropped {h['mp_nli_dropped']}, of which present-by-proxy "
                 f"{h['mp_nli_drop_but_present_proxy']} (NLI presence-miss candidates).\n")
    lines.append("\n## must_change: family × dose (raw NLI vs verified TRUE)\n")
    lines.append("| family | dose | mc items | raw NLI | verified TRUE | (of which never-flagged) |")
    lines.append("|---|---|---|---|---|---|")
    for key, t in report["true_floor_table_mc"].items():
        fam, dose = key.split("|")
        lines.append(f"| {fam} | {dose} | {t['mc_items']} | {t['raw_nli_flag']} | "
                     f"{t['verified_true']} | {t['never_flag_verified_true']} |")
    lines.append("\n## must_change by family (all doses)\n")
    lines.append("| family | raw NLI | verified TRUE |")
    lines.append("|---|---|---|")
    for fam, v in report["mc_by_family"].items():
        lines.append(f"| {fam} | {v['raw_nli']} | {v['verified_true']} |")
    lines.append("\n## must_change by dose (all families)\n")
    lines.append("| dose | raw NLI | verified TRUE |")
    lines.append("|---|---|---|")
    for dose, v in report["mc_by_dose"].items():
        lines.append(f"| {dose} | {v['raw_nli']} | {v['verified_true']} |")
    with open(os.path.join(OUT_DIR, "true-floor-table.md"), "w") as f:
        f.write("\n".join(lines) + "\n")

if __name__ == "__main__":
    main()
