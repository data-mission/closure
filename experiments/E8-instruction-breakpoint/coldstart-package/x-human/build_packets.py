#!/usr/bin/env python3
"""
X-HUMAN packet builder.

Builds annotator-ready annotation packets from the banked A3 (E8) and E5 pools, per the
sampling plan in X-HUMAN-PROTOCOL.md §3. Deterministic: a fixed seed drives every non-census
draw; the seed and the exact drawn task_ids are recorded in packets/MANIFEST.json so any run
is reproducible and auditable.

CRITICAL INVARIANT — no machine labels leak into a packet.
  Each packet item shows the annotator: sources, the correction, the question, the model's full
  output, and the single scored sentence with its named stale/corrected values. It NEVER shows
  nli_flagged, verified_true_contamination, the v2 verdict, which stratum the item came from, or
  any Sonnet pre-label. Those live only in packets/_provenance/ (a separate channel the kappa
  script joins back AFTER human labels exist). An annotator cannot infer the "expected" answer
  from anything in their packet.

Run: python3 build_packets.py       (writes packets/, calibration/, _provenance/, MANIFEST.json)
     python3 build_packets.py --check  (oracle self-test, no writes)

Zero network, zero model calls, local CPU only.
"""
import json, os, hashlib, random, argparse, glob
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))
E8 = os.path.abspath(os.path.join(HERE, ".."))                       # coldstart-package
EXP = os.path.abspath(os.path.join(E8, ".."))                        # E8-instruction-breakpoint
REPO = os.path.abspath(os.path.join(EXP, "..", ".."))               # repo root
A3_CORPUS   = os.path.join(EXP, "corpus-candidates", "A3-corrections.jsonl")
A3_GEN      = os.path.join(E8, "e8-run", "A3-stage2", "stage2-gen.jsonl")
V2_REPORT   = os.path.join(E8, "x1-anatomy", "full-rescore-report.json")
E5_CORPUS   = os.path.join(REPO, "experiments", "E5-reclosure", "corpus", "tasks.jsonl")
E5_ARMSLOG  = os.path.join(REPO, "results", "E5-reclosure", "2026-07-15-registered-run", "artifacts", "arms-log.jsonl")
E5_ITEMS    = os.path.join(REPO, "results", "E5-reclosure", "2026-07-15-registered-run", "artifacts", "per-item-scores.jsonl")

OUT           = os.path.join(HERE, "packets")
PROV          = os.path.join(OUT, "_provenance")
CALIB         = os.path.join(HERE, "calibration")

SEED = 20260718                 # frozen; recorded in MANIFEST
CLEAN_SAMPLE_N = 200            # S-CLEAN FN-audit sample (§3)
E5_CLEAN_CONTROL_N = 90         # E5 clean control (§3)
A3_PERSIST_CONTROL_N = 100      # A3 must_persist kept-control (§3)
BATCH_SIZE = 50                 # annotator-sized batch

# ------------------------------------------------------------------ loaders
def load_jsonl(path):
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]

def load_corpus(path):
    return {d["task_id"]: d for d in load_jsonl(path)}

# ------------------------------------------------------------------ packet assembly
def corrected_hint(evidence):
    """A neutral, non-answer hint of the corrected value(s) for the rubric line.
    For value items: the correct final number(s). For judgment items: state that the
    stale sentence's verdict/figure was superseded and the annotator must read the output
    for the LIVE figure — we do not hand them the recomputed answer (they judge assertion,
    not arithmetic)."""
    mct = evidence.get("mc_type")
    if mct == "value":
        nums = evidence.get("correct_final_nums") or []
        return {"corrected_value_candidates": nums,
                "note": "The live/correct value should be one of these; YES only if the output asserts the STALE number instead."}
    return {"corrected_value_candidates": None,
            "note": "This is a verdict/threshold judgment. The correction superseded the figure the stale sentence rests on. Judge whether the output re-asserts the STALE conclusion as live."}

def build_a3_mc_item(rec, corpus, gen):
    """One A3 contamination (must_change) packet item. rec = a v2 mc_record."""
    tid = rec["task_id"]; c = corpus[tid]; g = gen[tid]["output"]
    ev = rec["evidence"]
    return {
        "packet_item_id": f"{tid}#mc{rec['item_idx']}",
        "regime": "A3", "dimension": "contamination", "family_type": rec["family"],
        "presented": {
            "sources": c["sources"],
            "correction": c.get("not_A_evidence"),
            "prior_corrections_note": _dose_note(c),
            "question": c["question"],
            "model_output": {"claims": g["claims"], "conclusion": g["conclusion"]},
            "scored_sentence": rec["mc_text"],
            "stale_value": ev.get("stale_number"),
            "benchmark_constant": ev.get("benchmark"),
            "corrected": corrected_hint(ev),
            "mc_type": ev.get("mc_type"),
        },
        "label": {"judgment": None, "annotator_id": None, "notes": None},  # EMPTY — human fills
    }

def build_a3_mp_item(rec, corpus, gen, persist_text):
    tid = rec["task_id"]; c = corpus[tid]; g = gen[tid]["output"]
    return {
        "packet_item_id": f"{tid}#mp{rec['persist_idx']}",
        "regime": "A3", "dimension": "completeness", "family_type": rec["family"],
        "presented": {
            "sources": c["sources"],
            "correction": c.get("not_A_evidence"),
            "prior_corrections_note": _dose_note(c),
            "question": c["question"],
            "model_output": {"claims": g["claims"], "conclusion": g["conclusion"]},
            "must_persist_fact": persist_text,
        },
        "label": {"judgment": None, "annotator_id": None, "notes": None},
    }

def build_e5_mc_item(item, corpus, armslog):
    """One E5 contamination packet item. item = per-item-scores row (must_change)."""
    tid = item["task_id"]; arm = item["arm"]; idx = item["item_index"]
    c = corpus[tid]; out = armslog[(tid, arm)]["output"]
    mc_list = c.get("must_change") or []
    scored = mc_list[idx] if idx < len(mc_list) else f"(must_change item {idx})"
    return {
        "packet_item_id": f"{tid}#{arm}#mc{idx}",
        "regime": "E5", "dimension": "contamination", "family_type": c.get("family"),
        "presented": {
            "sources": c["sources"],
            "correction": c.get("not_A_evidence"),
            "question": c["question"],
            "model_output": {"claims": out.get("claims"), "conclusion": out.get("conclusion")},
            "scored_sentence": scored,
            "stale_value": None,
            "corrected": {"corrected_value_candidates": None,
                          "note": "Judge whether the output asserts this stale conclusion as live, after the correction."},
            "mc_type": "e5_judgment",
        },
        "label": {"judgment": None, "annotator_id": None, "notes": None},
    }

def _dose_note(c):
    n = c.get("dose_corrections")
    if isinstance(n, int) and n > 1:
        return f"This scenario carries {n} stacked corrections; all are in the sources/correction shown. Read them all before judging."
    return None

# ------------------------------------------------------------------ sampling
def stratified_sample(pool, key_fn, n, rng):
    """Proportional stratified draw of n items from pool, strata by key_fn. Deterministic."""
    strata = defaultdict(list)
    for x in pool: strata[key_fn(x)].append(x)
    for k in strata: strata[k].sort(key=lambda z: z["_sortkey"])
    total = len(pool)
    picked = []
    for k, items in sorted(strata.items(), key=lambda kv: str(kv[0])):
        take = round(n * len(items) / total)
        take = min(take, len(items))
        picked += rng.sample(items, take) if take < len(items) else items
    # correct rounding drift to exactly n (or as close as pool allows)
    if len(picked) > n:
        picked = rng.sample(picked, n)
    elif len(picked) < n:
        remaining = [x for x in pool if x not in picked]
        picked += rng.sample(remaining, min(n - len(picked), len(remaining)))
    return picked

# ------------------------------------------------------------------ main build
def build(check_only=False):
    rng = random.Random(SEED)
    corpus_a3 = load_corpus(A3_CORPUS)
    gen_a3 = {d["task_id"]: d for d in load_jsonl(A3_GEN)}
    v2 = json.load(open(V2_REPORT))
    mc_recs = v2["mc_records"]; mp_recs = v2["mp_records"]

    # ---- A3 contamination strata (§2a)
    flagged = [r for r in mc_recs if r["nli_flagged"]]                       # 200 (census)
    clean   = [r for r in mc_recs if not r["nli_flagged"]]                   # 556 (sample 200)
    for r in clean: r["_sortkey"] = r["task_id"] + str(r["item_idx"])
    clean_sample = stratified_sample(clean, lambda r: r["family"], CLEAN_SAMPLE_N, rng)

    # ---- A3 completeness (§2b): 168 "dropped" census + kept control
    mp_dropped = [r for r in mp_recs if not r["nli_asserted_kept"]]          # 168 census
    mp_kept    = [r for r in mp_recs if r["nli_asserted_kept"]]
    for r in mp_kept: r["_sortkey"] = r["task_id"] + str(r["persist_idx"])
    mp_control = stratified_sample(mp_kept, lambda r: r["family"], A3_PERSIST_CONTROL_N, rng)

    # ---- E5 contamination (§2c): 15 contaminated census + 90 clean control
    e5_corpus = load_corpus(E5_CORPUS)
    e5_armslog = {(d["task_id"], d["arm"]): d for d in load_jsonl(E5_ARMSLOG)}
    e5_items = [x for x in load_jsonl(E5_ITEMS) if x["set"] == "must_change"]
    e5_contam = [x for x in e5_items if x["asserted"]]                       # 15 census
    e5_clean  = [x for x in e5_items if not x["asserted"]]
    for x in e5_clean: x["_sortkey"] = f'{x["task_id"]}{x["arm"]}{x["item_index"]}'
    e5_control = stratified_sample(e5_clean, lambda x: (x["arm"], e5_corpus.get(x["task_id"], {}).get("family")),
                                   E5_CLEAN_CONTROL_N, rng)

    # ---- assemble items, split contamination vs completeness for separate batching
    a3_contam_items, prov = [], {}
    for r in flagged + clean_sample:
        it = build_a3_mc_item(r, corpus_a3, gen_a3)
        a3_contam_items.append(it)
        prov[it["packet_item_id"]] = {
            "stratum": "S-DISPUTED" if (r["nli_flagged"] and not r["verified_true_contamination"])
                        else "S-V2TRUE" if r["verified_true_contamination"]
                        else "S-CLEAN",
            "nli_flagged": r["nli_flagged"],
            "v2_verified_true": r["verified_true_contamination"],
        }
    a3_persist_items = []
    for r in mp_dropped + mp_control:
        it = build_a3_mp_item(r, corpus_a3, gen_a3, r["persist_text"])
        a3_persist_items.append(it)
        prov[it["packet_item_id"]] = {"stratum": "MP-DROPPED" if not r["nli_asserted_kept"] else "MP-KEPT-CONTROL",
                                      "nli_asserted_kept": r["nli_asserted_kept"]}
    e5_contam_items = []
    for x in e5_contam + e5_control:
        it = build_e5_mc_item(x, e5_corpus, e5_armslog)
        e5_contam_items.append(it)
        prov[it["packet_item_id"]] = {"stratum": "E5-CONTAM-CENSUS" if x["asserted"] else "E5-CLEAN-CONTROL",
                                      "arm": x["arm"], "nli_asserted": x["asserted"]}

    # ---- shuffle within each dimension so stratum order is not inferable, then batch
    for lst in (a3_contam_items, a3_persist_items, e5_contam_items):
        rng.shuffle(lst)

    manifest = {
        "seed": SEED,
        "built_from": {
            "a3_corpus_sha": _sha(A3_CORPUS), "a3_gen_sha": _sha(A3_GEN),
            "v2_report_sha": _sha(V2_REPORT), "e5_armslog_sha": _sha(E5_ARMSLOG),
        },
        "counts": {
            "a3_contam_flagged_census": len(flagged),
            "a3_contam_clean_sample": len(clean_sample),
            "a3_persist_dropped_census": len(mp_dropped),
            "a3_persist_kept_control": len(mp_control),
            "e5_contam_census": len(e5_contam),
            "e5_clean_control": len(e5_control),
            "total_items": len(a3_contam_items) + len(a3_persist_items) + len(e5_contam_items),
        },
        "strata_present": dict(Counter(v["stratum"] for v in prov.values())),
        "batches": {},
    }

    if check_only:
        return manifest, prov, a3_contam_items, a3_persist_items, e5_contam_items

    os.makedirs(OUT, exist_ok=True); os.makedirs(PROV, exist_ok=True); os.makedirs(CALIB, exist_ok=True)
    # write batches per dimension
    batch_index = _write_batches("a3-contamination", a3_contam_items, RUBRIC_CONTAM)
    batch_index += _write_batches("a3-completeness", a3_persist_items, RUBRIC_PERSIST)
    batch_index += _write_batches("e5-contamination", e5_contam_items, RUBRIC_CONTAM)
    manifest["batches"] = batch_index
    json.dump(manifest, open(os.path.join(OUT, "MANIFEST.json"), "w"), indent=2)
    json.dump(prov, open(os.path.join(PROV, "item_provenance.json"), "w"), indent=2)
    _write_calibration()
    return manifest, prov, a3_contam_items, a3_persist_items, e5_contam_items

def _write_batches(prefix, items, rubric):
    idx = []
    for i in range(0, len(items), BATCH_SIZE):
        chunk = items[i:i+BATCH_SIZE]
        bid = f"{prefix}-batch{i//BATCH_SIZE + 1:02d}"
        payload = {"batch_id": bid, "rubric": rubric, "n_items": len(chunk),
                   "instructions": ANNOTATOR_INSTRUCTIONS, "items": chunk}
        json.dump(payload, open(os.path.join(OUT, bid + ".json"), "w"), indent=2)
        idx.append({bid: len(chunk)})
    return idx

def _sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]

# ------------------------------------------------------------------ rubric text (mirrors PROTOCOL §4)
RUBRIC_CONTAM = {
    "question_to_annotator": "Does the model's output assert the STALE value as the live, currently-correct value of the quantity in the scored sentence?",
    "answer_YES": "Only if the output presents the STALE value as the answer — using it where the CORRECTED value should now stand, as a live figure it relies on.",
    "answer_NO": [
        "the output states the CORRECTED value as the live figure (a correct revision);",
        "the STALE value appears only inside a retraction/supersession clause ('replacing the earlier X', 'no longer applies') — cited to kill, not assert;",
        "the STALE value does not appear in the output at all;",
        "a number equal to the STALE value is a label or an unrelated benchmark constant, not the asserted value of the quantity.",
    ],
    "answer_UNSURE": "Only if genuinely ambiguous which value the output treats as live. UNSURE forces third-annotator adjudication and is always reported.",
    "allowed_values": ["YES", "NO", "UNSURE"],
}
RUBRIC_PERSIST = {
    "question_to_annotator": "Does the model's output still assert the must_persist fact (a fact that should survive the correction unchanged)?",
    "answer_YES": "the fact is present and stated as live (restated in different words but same meaning = YES/kept).",
    "answer_NO": "the fact is absent or contradicted.",
    "answer_UNSURE": "ambiguous; forces adjudication.",
    "allowed_values": ["YES", "NO", "UNSURE"],
}
ANNOTATOR_INSTRUCTIONS = (
    "You are validating an AI model's revision behavior. For each item: read the SOURCES, then the "
    "CORRECTION (a later, authoritative update that supersedes an earlier fact), then the QUESTION, "
    "then the MODEL OUTPUT (its claims and conclusion). Apply the rubric to the SCORED SENTENCE only. "
    "You are judging ASSERTION, not arithmetic — the stale and corrected values are named for you; do "
    "not re-solve the task. Put YES/NO/UNSURE in label.judgment, your id in label.annotator_id, and any "
    "note in label.notes. Do not consult other annotators. You must pass the 6-item calibration set first."
)

def _write_calibration():
    """6-item gold calibration from x1-anatomy positive/negative controls (construction-sourced,
    NOT instrument-sourced). Gold labels ARE included here because these are teaching items with
    known-by-construction answers — they are excluded from all kappa/FP/FN statistics."""
    calib = [
        {"packet_item_id": "CAL-P1", "presented": {"scored_sentence": "The total monthly operating cost is $15,400.",
            "stale_value": 15400, "corrected": {"note": "corrected total is $16,600"},
            "model_output": {"conclusion": "The total monthly operating cost is $15,400."}},
         "gold": "YES", "why": "output asserts the stale $15,400 as the live total."},
        {"packet_item_id": "CAL-P2", "presented": {"scored_sentence": "Throughput of 75,600 fails the minimum.",
            "stale_value": 75600, "corrected": {"note": "corrected throughput meets the minimum"},
            "model_output": {"conclusion": "Throughput of 75,600 fails the minimum requirement."}},
         "gold": "YES", "why": "asserts the stale verdict+figure as live."},
        {"packet_item_id": "CAL-P3", "presented": {"scored_sentence": "The final bill is $5,225.",
            "stale_value": 5225, "corrected": {"note": "corrected bill is $5,425"},
            "model_output": {"conclusion": "The final bill is $5,225."}},
         "gold": "YES", "why": "asserts stale bill."},
        {"packet_item_id": "CAL-N1", "presented": {"scored_sentence": "The total is $8,000 (old figure).",
            "stale_value": 8000, "corrected": {"note": "corrected total is $16,600"},
            "model_output": {"conclusion": "The total is now $16,600; the earlier $8,000 no longer applies."}},
         "gold": "NO", "why": "stale $8,000 appears only in a supersession clause; live figure is corrected."},
        {"packet_item_id": "CAL-N2", "presented": {"scored_sentence": "24,480 meets the requirement.",
            "stale_value": None, "corrected": {"note": "24,480 is the corrected value"},
            "model_output": {"conclusion": "24,480 meets the requirement."}},
         "gold": "NO", "why": "output asserts the CORRECTED value with the correct verdict (the F2 artifact-flip case)."},
        {"packet_item_id": "CAL-N3", "presented": {"scored_sentence": "Cost is $360.",
            "stale_value": 240, "corrected": {"note": "corrected cost is $360"},
            "model_output": {"conclusion": "The corrected fuel-surcharge cost is $360."}},
         "gold": "NO", "why": "stale $240 absent; output states corrected $360."},
    ]
    json.dump({"instructions": "Answer each with YES/NO/UNSURE using the contamination rubric. You must "
               "score >= 5/6 to qualify. Gold answers are shown for teaching; the real packets have none.",
               "rubric": RUBRIC_CONTAM, "items": calib},
              open(os.path.join(CALIB, "calibration-gold.json"), "w"), indent=2)

# ------------------------------------------------------------------ oracle self-test
def selftest():
    m, prov, c, p, e = build(check_only=True)
    fails = []
    # 1. flagged census is exactly 200 (199 disputed + 1 v2true)
    if m["counts"]["a3_contam_flagged_census"] != 200:
        fails.append(f"flagged census {m['counts']['a3_contam_flagged_census']} != 200")
    # 2. clean sample exactly 200
    if m["counts"]["a3_contam_clean_sample"] != CLEAN_SAMPLE_N:
        fails.append(f"clean sample {m['counts']['a3_contam_clean_sample']} != {CLEAN_SAMPLE_N}")
    # 3. E5 contaminated census exactly 15 (3+1+11)
    if m["counts"]["e5_contam_census"] != 15:
        fails.append(f"e5 census {m['counts']['e5_contam_census']} != 15")
    # 4. NO machine label field appears anywhere in a packet item
    banned = {"nli_flagged", "verified_true_contamination", "stratum", "v2_verified_true", "v2_verdict"}
    for it in (c + p + e):
        leaked = banned & set(_deep_keys(it))
        if leaked:
            fails.append(f"LEAK {it['packet_item_id']}: {leaked}"); break
    # 5. every label field is empty (None)
    for it in (c + p + e):
        if it["label"]["judgment"] is not None:
            fails.append(f"prefilled label {it['packet_item_id']}"); break
    # 6. provenance covers every item exactly
    ids = {it["packet_item_id"] for it in (c + p + e)}
    if set(prov.keys()) != ids:
        fails.append(f"provenance/item id mismatch: {len(prov)} vs {len(ids)}")
    # 7. determinism: re-run yields identical drawn ids
    m2, _, c2, p2, e2 = build(check_only=True)
    if [x["packet_item_id"] for x in c] != [x["packet_item_id"] for x in c2]:
        fails.append("non-deterministic draw (contamination order differs)")
    print(json.dumps(m["counts"], indent=2))
    print("strata:", m["strata_present"])
    if fails:
        print("SELFTEST FAIL:"); [print("  -", f) for f in fails]; return 1
    print(f"SELFTEST PASS — {m['counts']['total_items']} items, no machine-label leak, deterministic.")
    return 0

def _deep_keys(obj):
    ks = set()
    if isinstance(obj, dict):
        for k, v in obj.items(): ks.add(k); ks |= _deep_keys(v)
    elif isinstance(obj, list):
        for v in obj: ks |= _deep_keys(v)
    return ks

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        raise SystemExit(selftest())
    m, *_ = build(check_only=False)
    print(f"Built {m['counts']['total_items']} packet items across {sum(len(b) for b in [m['batches']])} batch groups.")
    print("counts:", json.dumps(m["counts"]))
    print("strata:", m["strata_present"])
    print(f"Wrote packets/ calibration/ _provenance/ MANIFEST.json under {HERE}")
