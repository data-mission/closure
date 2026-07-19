#!/usr/bin/env python3
"""
X-HUMAN — X6 FF-cell packet builder (refusal-confirmation dimension).

CONTEXT (from red-check + _dev_notes/x6-ff-diagnosis/FF-TAXONOMY.md, verified against the raw sample):
The X6 pilot acceptance gate fired WITHHOLD (SCOPED FF 73.7%). The diagnosed root cause is a
CORPUS-CONSTRUCTION defect, NOT scoring ambiguity and NOT model over-generalization: the X6 worksheet
gives the model the RULE ("2% of insured value") + the exception but NOT the per-case FACTS (insured
values, kWh, hours) the rule needs, so the model correctly REFUSES to compute rule-case values
(RULE/NEW answered 0/90; EXCEPTED answered 13/15). The pilot is therefore VOID for the behavioral
(SCOPE_LEAK) hypothesis until the corpus is fixed and re-run.

SO THE HUMAN TASK IS NARROW — NOT scope-leak adjudication. It is: on each raw model reply, confirm
whether it is a genuine MISSING-INPUT REFUSAL (the model declines to compute because the facts were
not provided) vs some OTHER behavior (it fabricated inputs, computed a wrong value, or actually
over-generalized the exception). This single spot-confirm is what certifies the "construction defect,
not model failure" ruling with human eyes before it is written into the record.

WHY A KEYWORD SCAN IS NOT ENOUGH (the finding that justifies the human pass): a refusal-keyword scan
matches only 17/30 replies, yet hand-reading shows all 30 are refusals — the other 13 use the
"I don't have X / please provide" idiom a keyword list misses. A human reading prose sees what the
parser cannot. That gap is exactly why this dimension needs human labels, not an automated rule.

INVARIANT: no machine label / no diagnosis verdict is shown to the annotator. The annotator sees the
worksheet prompt + the raw reply, and answers the rubric. The taxonomy's expected answer lives only in
_provenance/, joined back after labels exist.

Run:  python3 build_x6ff_packets.py           (writes packets/x6ff-*.json + provenance)
      python3 build_x6ff_packets.py --check    (oracle self-test, no writes)
"""
import json, os, hashlib, argparse
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "_x6ff_source.jsonl")
OUT = os.path.join(HERE, "packets")
PROV = os.path.join(OUT, "_provenance")
BATCH_SIZE = 15   # 30 items → 2 batches; keep each (arm) coherent-ish but shuffled

RUBRIC_X6FF = {
    "question_to_annotator": "Is this reply a genuine MISSING-INPUT REFUSAL — the model declining to "
        "compute the per-case values because the worksheet did not give it the facts (insured values, "
        "kWh, hours, dates) the rule needs?",
    "answer_REFUSAL": "the model says (in any words) it lacks the per-case inputs and asks for them / "
        "declines to compute — e.g. 'I cannot compute…no values were provided', 'I don't have the "
        "billing records…please provide', 'the rate alone isn't sufficient'. It may still answer a "
        "case that DID carry an explicit value (the excepted case) — that is still a REFUSAL reply "
        "overall if it refuses the fact-less cases.",
    "answer_FABRICATED": "the model INVENTED per-case inputs that were not in the worksheet and "
        "computed values from them (a real failure — flag it).",
    "answer_OVERGENERALIZED": "the model applied the EXCEPTION's value/rate to a case the exception "
        "did not name (the SCOPE_LEAK behavior the pilot meant to measure) — flag it, it would mean "
        "the defect hid a real signal.",
    "answer_OTHER": "none of the above (e.g. computed a plainly wrong value from provided facts, or "
        "incoherent) — describe in notes.",
    "allowed_values": ["REFUSAL", "FABRICATED", "OVERGENERALIZED", "OTHER"],
}

INSTRUCTIONS = (
    "You are checking WHY an AI worksheet task produced no scorable answers. For each item read the "
    "WORKSHEET PROMPT the model was given, then its RAW REPLY. Decide, per the rubric, what the reply "
    "actually is. The point is to confirm the model refused for lack of inputs (expected) vs did "
    "something else (a real finding). Put REFUSAL/FABRICATED/OVERGENERALIZED/OTHER in label.judgment, "
    "your id in label.annotator_id, notes in label.notes. Do not consult other annotators."
)


def load_rows():
    return [json.loads(l) for l in open(SRC) if l.strip()]


# Two heuristics, both recorded in provenance as AUXILIARY predictors the human label CHECKS.
# The narrow list is the "obvious refusal keyword" set; the broad list adds the "I don't have X /
# please provide" idiom. The gap between them (narrow 17/30 vs broad 30/30) is the concrete evidence
# that a keyword rule is fragile: which words you pick decides the count, and only a human reading the
# prose is invariant to phrasing. Neither heuristic distinguishes a refusal from a fabrication that is
# WORDED like a refusal — that discrimination is exactly what the human pass adds.
NARROW_KWS = ["cannot compute", "not provided", "no meter", "were not provided", "no values",
              "cannot calculate", "not specified", "declarations page", "unable to"]
BROAD_KWS = NARROW_KWS + ["missing", "not given", "need the", "were provided", "without the",
                          "don't have", "do not have", "please provide", "isn't sufficient",
                          "is not sufficient", "provide the", "provide those"]

def keyword_refusal(text, kws=BROAD_KWS):
    t = (text or "").lower()
    return any(k in t for k in kws)


def build(check_only=False):
    rows = load_rows()
    items, prov = [], {}
    for r in rows:
        sc = r.get("scored_cases", [])
        # count answered vs refused cases by class, from the diagnosis fields (provenance only)
        by_cls = Counter(c["cls"] for c in sc)
        answered = sum(1 for c in sc if c.get("emitted_parsed") is not None)
        it = {
            "packet_item_id": r["task_id"],
            "dimension": "x6_ff_refusal",
            "arm": r["arm"], "dose_level": r["dose_level"],
            "presented": {
                "worksheet_prompt": r["worksheet_prompt"],
                "raw_reply": r["raw_final_reply"],
                "n_cases_in_task": len(sc),
            },
            "label": {"judgment": None, "annotator_id": None, "notes": None},
        }
        items.append(it)
        prov[r["task_id"]] = {
            "stratum": f"X6FF-{r['arm']}-D{r['dose_level']}",
            "arm": r["arm"], "dose_level": r["dose_level"],
            "cases_by_class": dict(by_cls),
            "cases_answered_parsed": answered,
            "keyword_refusal_narrow": keyword_refusal(r["raw_final_reply"], NARROW_KWS),
            "keyword_refusal_broad": keyword_refusal(r["raw_final_reply"], BROAD_KWS),
            "diagnosis_expected": "REFUSAL",  # the taxonomy's expectation; NOT shown to annotator
        }

    manifest = {
        "dimension": "x6_ff_refusal",
        "built_from_sha": hashlib.sha256(open(SRC, "rb").read()).hexdigest()[:16],
        "n_items": len(items),
        "strata": dict(Counter(v["stratum"] for v in prov.values())),
        "keyword_refusal_narrow_coverage": sum(1 for v in prov.values() if v["keyword_refusal_narrow"]),
        "keyword_refusal_broad_coverage": sum(1 for v in prov.values() if v["keyword_refusal_broad"]),
        "note": "narrow keyword set matches 17/30, broad set 30/30 — the count depends on which words "
                "you pick, which is exactly why a keyword rule cannot certify the ruling and a human "
                "pass is needed. Neither heuristic separates a genuine refusal from a fabrication worded "
                "like one; the human does.",
    }

    if check_only:
        return manifest, prov, items

    os.makedirs(OUT, exist_ok=True); os.makedirs(PROV, exist_ok=True)
    # shuffle deterministically (sort by a hash of task_id) so arm/dose order is not inferable
    items.sort(key=lambda it: hashlib.sha256(it["packet_item_id"].encode()).hexdigest())
    batch_index = []
    for i in range(0, len(items), BATCH_SIZE):
        chunk = items[i:i + BATCH_SIZE]
        bid = f"x6ff-refusal-batch{i // BATCH_SIZE + 1:02d}"
        json.dump({"batch_id": bid, "rubric": RUBRIC_X6FF, "instructions": INSTRUCTIONS,
                   "scope_note": "NARROW: confirm missing-input refusal vs other behavior. This is NOT "
                                 "scope-leak adjudication — the pilot is void for that (construction "
                                 "defect); OVERGENERALIZED/FABRICATED here would mean the defect hid a "
                                 "real signal, so flag them, but they are not expected.",
                   "n_items": len(chunk), "items": chunk},
                  open(os.path.join(OUT, bid + ".json"), "w"), indent=2)
        batch_index.append({bid: len(chunk)})
    manifest["batches"] = batch_index
    json.dump(manifest, open(os.path.join(OUT, "MANIFEST-x6ff.json"), "w"), indent=2)
    # merge provenance into the shared channel
    provfile = os.path.join(PROV, "item_provenance_x6ff.json")
    json.dump(prov, open(provfile, "w"), indent=2)
    return manifest, prov, items


def selftest():
    m, prov, items = build(check_only=True)
    fails = []
    if m["n_items"] != 30:
        fails.append(f"n_items {m['n_items']} != 30")
    if m["strata"] != {f"X6FF-{a}-D{d}": 5 for a in ("BLANKET", "SCOPED") for d in (1, 2, 3)}:
        fails.append(f"strata not 5×(2 arms×3 doses): {m['strata']}")
    banned = {"diagnosis_expected", "stratum", "keyword_refusal_narrow", "keyword_refusal_broad",
              "cases_by_class", "emitted_parsed", "A_correct", "A_wrong", "cell"}
    for it in items:
        leaked = banned & _deep_keys(it)
        if leaked:
            fails.append(f"LEAK {it['packet_item_id']}: {leaked}"); break
    for it in items:
        if it["label"]["judgment"] is not None:
            fails.append(f"prefilled {it['packet_item_id']}"); break
    # the narrow keyword set must UNDER-count (proving keyword fragility); broad may reach 30
    if m["keyword_refusal_narrow_coverage"] >= 30:
        fails.append(f"narrow keyword coverage {m['keyword_refusal_narrow_coverage']} — expected <30 "
                     "(the fragility evidence)")
    print(json.dumps({"n_items": m["n_items"], "strata": m["strata"],
                      "keyword_narrow": m["keyword_refusal_narrow_coverage"],
                      "keyword_broad": m["keyword_refusal_broad_coverage"]}, indent=2))
    if fails:
        print("X6FF SELFTEST FAIL:"); [print("  -", f) for f in fails]; return 1
    print(f"X6FF SELFTEST PASS — 30 items, 6 strata ×5, no machine-label leak, empty labels; keyword "
          f"fragility shown (narrow {m['keyword_refusal_narrow_coverage']}/30 vs broad "
          f"{m['keyword_refusal_broad_coverage']}/30 → human pass justified).")
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
    print(f"Built {m['n_items']} X6-FF packet items.")
    print("strata:", m["strata"], "| keyword refusal narrow/broad:",
          m["keyword_refusal_narrow_coverage"], "/", m["keyword_refusal_broad_coverage"], "of 30")
    print(f"Wrote packets/x6ff-*.json + MANIFEST-x6ff.json + _provenance/item_provenance_x6ff.json")
