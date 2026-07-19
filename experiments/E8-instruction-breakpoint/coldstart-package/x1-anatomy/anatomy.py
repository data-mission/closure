#!/usr/bin/env python3
"""X1 FAILURE ANATOMY — classify every contaminated E8-A3 item (deterministic, CPU-only).

Contamination flag source: results/*.json arms.B.must_change_asserted_by_index[str(i)] == True.
The instrument (batched_stage2_scorer -> outcomes._still_asserts) is a PURELY TEXTUAL bidirectional
NLI test at threshold 0.7 between the model output (conclusion + claim texts, source_ids EXCLUDED)
and the stale must_change[i] sentence. Citations play NO role in the flag. This script therefore
re-examines each flagged item with string/numeric analysis of the claims JSON to answer:

  (a) ECHO vs RE-DERIVED vs INSTRUMENT-FALSE-POSITIVE
  (b) ACKNOWLEDGMENT-WITHOUT-INTEGRATION (per output)
  (c) correlates (dose, position, type, family)
  (d) operator-target synthesis (in the report, not here)

Join keys (all 1:1, verified): task_id across results/, stage2-gen.jsonl, A3-corrections.jsonl.
Correction docs are appended AFTER sources in the prompt, so correction j sits at document index
len(sources)+j and supersedes corrections[j].supersedes_source_id.
"""
from __future__ import annotations
import json, re, glob, os
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# BASE = .../E8-instruction-breakpoint
RESULTS = os.path.join(BASE, "coldstart-package/e8-run/A3-stage2/results")
GEN = os.path.join(BASE, "coldstart-package/e8-run/A3-stage2/stage2-gen.jsonl")
CORPUS = os.path.join(BASE, "corpus-candidates/A3-corrections.jsonl")
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------- number helpers ----------
NUM_RE = re.compile(r'\$?\d[\d,]*(?:\.\d+)?')

def norm_num(tok: str):
    t = tok.replace("$", "").replace(",", "")
    try:
        return float(t)
    except ValueError:
        return None

def extract_nums(text: str) -> set:
    out = set()
    for tok in NUM_RE.findall(text):
        n = norm_num(tok)
        if n is not None:
            out.add(n)
    return out

def extract_ordered_nums(text: str) -> list:
    out = []
    for tok in NUM_RE.findall(text):
        n = norm_num(tok)
        if n is not None:
            out.append(n)
    return out

# ---------- must_change typing ----------
JUDGMENT_MARKERS = ["exceeds", "fits within", "fits", "fails", "meets", "violation",
                    "cannot", "may not", "life-safety", "short of", "blocked",
                    "sufficient", "within the", "below", "above the", "under the",
                    "no longer", "still", "not all"]

def mc_type(text: str) -> str:
    tl = text.lower()
    if any(m in tl for m in JUDGMENT_MARKERS):
        return "judgment"
    if re.search(r'\bis\b.{0,40}?\$?\d[\d,]*', tl):
        return "value"
    return "other"

# ---------- load ----------
def load():
    corpus = {}
    for line in open(CORPUS):
        c = json.loads(line)
        corpus[c["task_id"]] = c
    gen = {}
    for line in open(GEN):
        g = json.loads(line)
        gen[g["task_id"]] = g
    results = {}
    for f in glob.glob(os.path.join(RESULTS, "*.json")):
        if "_oracle_result" in f:
            continue
        d = json.load(open(f))
        results[d["task_id"]] = d
    return corpus, gen, results

# ---------- per-task correction geometry ----------
def correction_geometry(task: dict):
    """Return dict: correction doc index -> superseded source id, and reverse."""
    nsrc = len(task["sources"])
    corr = task["axis_params"]["corrections"]
    doc_of_corr = {}      # correction j -> doc index nsrc+j
    superseded_by_docidx = {}  # doc index -> superseded source id
    for j, co in enumerate(corr):
        docidx = nsrc + j
        doc_of_corr[j] = docidx
        superseded_by_docidx[docidx] = co.get("supersedes_source_id")
    superseded_src_ids = {co.get("supersedes_source_id") for co in corr}
    correction_doc_ids = set(doc_of_corr.values())
    return {
        "nsrc": nsrc,
        "correction_doc_ids": correction_doc_ids,
        "superseded_src_ids": superseded_src_ids,
        "superseded_by_docidx": superseded_by_docidx,
    }

# ---------- (a) echo vs re-derived vs false-positive ----------
def distinguishing_stale_nums(task: dict, i: int) -> set:
    """Numbers in must_change[i] that are NOT shared by any OTHER must_change item.
    For 'value' items this isolates the stale answer figure; for judgment items it is often empty
    (verdicts differ in polarity, not number)."""
    this_n = extract_nums(task["must_change"][i])
    other = set()
    for j, m in enumerate(task["must_change"]):
        if j != i:
            other |= extract_nums(m)
    return this_n - other

def output_texts(output: dict):
    """(conclusion, [claim dicts]) — the exact premise material the instrument used (minus ids)."""
    return output["conclusion"], output["claims"]

def classify_echo(task, output, i):
    """Classify a contaminated VALUE-type item as echo / re-derived / no-stale-number.
    Also returns where the stale number landed."""
    dist = distinguishing_stale_nums(task, i)
    concl = output["conclusion"]
    claims = output["claims"]
    concl_nums = extract_nums(concl)
    # locate stale number occurrences
    in_conclusion = bool(dist & concl_nums)
    claim_hits = []
    for cl in claims:
        if dist & extract_nums(cl["text"]):
            claim_hits.append(cl)
    stale_number_present = in_conclusion or bool(claim_hits)
    return {
        "distinguishing_stale_nums": sorted(dist),
        "stale_number_present": stale_number_present,
        "stale_in_conclusion": in_conclusion,
        "stale_in_claim_ids": [cl["id"] for cl in claim_hits],
        "stale_claim_cites_superseded_only": _cites_superseded_only(task, claim_hits),
    }

def _cites_superseded_only(task, claim_hits):
    """For claims that assert the stale number: do they cite ONLY superseded sources (echo) or do
    they cite correction docs too (integration/annotation)?"""
    geo = correction_geometry(task)
    corr_ids = geo["correction_doc_ids"]
    sup_ids = geo["superseded_src_ids"]
    verdicts = []
    for cl in claim_hits:
        sids = set(cl.get("source_ids", []))
        cites_corr = bool(sids & corr_ids)
        cites_superseded = bool(sids & sup_ids)
        verdicts.append({
            "claim_id": cl["id"],
            "source_ids": sorted(sids),
            "cites_correction_doc": cites_corr,
            "cites_superseded_source": cites_superseded,
        })
    return verdicts

# ---------- (b) acknowledgment-without-integration ----------
CORRECTED_MARKERS = ["corrected", "revised", "revision", "now $", "now a fixed", "replacing",
                     "updated", "no longer", "new "]

def acknowledgment(task, output):
    """Does the OUTPUT acknowledge the corrections anywhere?
    Signal 1 (citation): any claim cites a correction doc index.
    Signal 2 (lexical): any claim/conclusion text uses a correction/revision marker.
    Signal 3 (numeric): any claim states a corrected component value (the 'now' figure from a
                        correction) verbatim.
    """
    geo = correction_geometry(task)
    corr_ids = geo["correction_doc_ids"]
    cites_correction = False
    for cl in output["claims"]:
        if set(cl.get("source_ids", [])) & corr_ids:
            cites_correction = True
            break
    alltext = output["conclusion"] + " " + " ".join(c["text"] for c in output["claims"])
    tl = alltext.lower()
    lexical = any(m in tl for m in CORRECTED_MARKERS)
    # corrected component values
    corr_nums = set()
    for co in task["axis_params"]["corrections"]:
        corr_nums |= extract_nums(co["text"])
    # remove numbers that also appear in the original (superseded) source to isolate the NEW value
    orig_nums = set()
    for co in task["axis_params"]["corrections"]:
        sid = co.get("supersedes_source_id")
        for s in task["sources"]:
            if s["id"] == sid:
                orig_nums |= extract_nums(s["text"])
    new_component_nums = corr_nums - orig_nums
    out_nums = extract_nums(alltext)
    states_corrected_value = bool(new_component_nums & out_nums)
    return {
        "cites_correction_doc": cites_correction,
        "lexical_ack": lexical,
        "states_corrected_component_value": states_corrected_value,
        "acknowledges": cites_correction or lexical or states_corrected_value,
    }

# ---------- main ----------
def main():
    corpus, gen, results = load()
    records = []
    for tid, d in results.items():
        c = corpus[tid]
        g = gen[tid]
        output = g["output"]
        dose = d["routing"]["dose_level"]
        family = c["covariates"].get("family", "?")
        flags = d["arms"]["B"]["must_change_asserted_by_index"]
        n_corrections = len(c["axis_params"]["corrections"])
        ack = acknowledgment(c, output)
        n_claims = len(output["claims"])
        for idx_s, flag in flags.items():
            if not flag:
                continue
            i = int(idx_s)
            mc = c["must_change"][i]
            typ = mc_type(mc)
            echo = classify_echo(c, output, i)
            disc = stale_computed_asserted(c, output, i)
            # correction position of the correction that produces state i (state i uses corrections 0..i-1;
            # the stale item i is "you stopped before applying correction i"). Position of the NEXT
            # unapplied correction = i (0-indexed) within n_corrections.
            rec = {
                "task_id": tid,
                "item_idx": i,
                "family": family,
                "dose": dose,
                "n_corrections": n_corrections,
                "mc_text": mc,
                "mc_type": typ,
                "n_claims": n_claims,
                "state_index": i,              # which chain state this stale item is
                "unapplied_correction_pos": i, # correction not-yet-applied that would fix it (0-indexed)
                "echo": echo,
                "discriminator": disc,
                "acknowledgment": ack,
            }
            # final per-item classification
            rec["classification"] = final_class(typ, echo, ack, disc)
            records.append(rec)
    aggregates = aggregate(records, results, corpus)
    report = {"n_contaminated_items": len(records), "aggregates": aggregates, "records": records}
    with open(os.path.join(OUT_DIR, "anatomy-report.json"), "w") as f:
        json.dump(report, f, indent=2)
    emit_nli_probe(records, corpus, gen)
    print(json.dumps(aggregates, indent=2))
    return report


def emit_nli_probe(records, corpus, gen):
    """Emit the residual PROBE_NEEDED_NLI cases as premise/hypothesis pairs for the Mini GPU.
    Hypothesis = the stale must_change sentence. Premises = the model output's asserted texts
    (conclusion + each claim text) — EXACTLY the instrument's premise set. The probe re-scores with
    a targeted question the aggregate 0.7 flag cannot answer: does the output assert the stale
    COMPUTED value as its answer, or only mention it as superseded? We add a decisive contrast pair
    per item: (model_conclusion, stale_sentence) vs (model_conclusion, corrected_sentence). If the
    corrected sentence scores >= the stale sentence, the flag is a template collision (false positive).
    """
    probes = []
    for r in records:
        if r["classification"] != "probe_needed_nli":
            continue
        tid = r["task_id"]; i = r["item_idx"]
        g = gen[tid]; c = corpus[tid]
        output = g["output"]
        premises = [output["conclusion"]] + [cl["text"] for cl in output["claims"]]
        probes.append({
            "task_id": tid,
            "item_idx": i,
            "stale_hypothesis": c["must_change"][i],
            "correct_final_state": c["axis_params"]["state_values"][-1],
            "premises": premises,
            "stale_computed": r["discriminator"]["stale_computed"],
            "note": "score max-over-premises bidirectional NLI of stale_hypothesis; compare to a "
                    "corrected-sentence hypothesis built from correct_final_state. stale>=corrected "
                    "=> real contamination; corrected>stale => instrument false positive.",
        })
    path = os.path.join(OUT_DIR, "nli-probe-pairs.json")
    with open(path, "w") as f:
        json.dump({"n_probes": len(probes),
                   "nli_model": "MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli",
                   "revision": "b3546ea6b0346eb6f8d5d68b13c7dc6d0376b3d7",
                   "threshold": 0.7,
                   "scalar": "max over premises of bidirectional avg of (P(entail)-P(contradict)+1)/2",
                   "runner": "run on Mini GPU via the frozen NLIScorer; DO NOT run locally",
                   "probes": probes}, f, indent=2)
    print(f"[probe] wrote {len(probes)} NLI probe items to {path}")

def stale_computed_asserted(task, output, i):
    """The load-bearing discriminator. A judgment/value must_change item has the shape
    '<quantity> is <COMPUTED>, which <verdict> the <THRESHOLD>'. The stale COMPUTED value is the
    FIRST number; the THRESHOLD is a shared constant that appears in BOTH the stale sentence and the
    model's CORRECT output (so it must be excluded). Real contamination = the model asserts the stale
    COMPUTED value as the quantity's value.

    Returns dict with:
      stale_computed: first number of must_change[i] (or None)
      threshold: second number (the shared requirement constant) or None
      correct_final_nums: numbers appearing in the corrected final-state description
      stale_computed_present_in_output: stale_computed appears verbatim in output text
      stale_equals_correct: stale_computed also appears in the correct final-state (corpus staircase
                            artifact — the value did not change at this dose, so its presence in the
                            output is NOT contamination)
      probe_needed: True when string analysis cannot decide (stale_computed present, not the
                    threshold, not equal to the correct value) — hand to NLI.
    """
    mc = task["must_change"][i]
    mcn = extract_ordered_nums(mc)
    stale_computed = mcn[0] if mcn else None
    threshold = mcn[1] if len(mcn) > 1 else None
    alltext = output["conclusion"] + " " + " ".join(c["text"] for c in output["claims"])
    out_nums = extract_nums(alltext)
    correct_final = extract_nums(task["axis_params"]["state_values"][-1])
    present = stale_computed is not None and stale_computed in out_nums
    is_threshold = stale_computed is not None and stale_computed == threshold
    equals_correct = stale_computed is not None and stale_computed in correct_final
    probe = bool(present and not is_threshold and not equals_correct)
    supersession = stale_only_in_supersession(output, stale_computed) if probe else False
    return {
        "stale_computed": stale_computed,
        "threshold": threshold,
        "correct_final_nums": sorted(correct_final),
        "stale_computed_present_in_output": present,
        "stale_equals_threshold": is_threshold,
        "stale_equals_correct": equals_correct,
        "probe_needed": probe,
        "stale_only_in_supersession": supersession,
    }


SUPERSESSION_MARKERS = ["supersede", "superseded", "supersedes", "original", "prior figure",
                        "earlier", "revised", "replacing", "replaced", "instead of",
                        "treated as false", "corrects", "corrected", "updating", "updated",
                        "raised to", "raising it"]

def stale_only_in_supersession(output, stale_computed):
    """True iff EVERY premise that mentions stale_computed does so inside a supersession/retraction
    clause (the model cites the stale value only to retract it). If any premise asserts the stale
    value as a live quantity (no supersession marker in that sentence), returns False -> genuinely
    needs a probe."""
    if stale_computed is None:
        return False
    num_txt = _num_variants(stale_computed)
    mentioning = []
    for prem in [output["conclusion"]] + [c["text"] for c in output["claims"]]:
        if any(v in prem for v in num_txt):
            mentioning.append(prem)
    if not mentioning:
        return False
    for prem in mentioning:
        low = prem.lower()
        if not any(m in low for m in SUPERSESSION_MARKERS):
            return False  # asserted as a live value somewhere
    return True

def _num_variants(n):
    """String forms a number could take in text: 8000 -> {'8000','8,000','$8,000','$8000'}."""
    if n == int(n):
        i = int(n)
        plain = str(i)
        grouped = f"{i:,}"
    else:
        plain = str(n)
        grouped = f"{n:,}"
    out = {plain, grouped, "$" + plain, "$" + grouped}
    return out


def final_class(typ, echo, ack, disc):
    """Per-item modal class, using the sharp computed-vs-threshold discriminator `disc`.

    FALSE_POSITIVE_INSTRUMENT — the stale computed value is absent from the output, OR it coincides
      with the shared threshold constant, OR it coincides with the (unchanged-at-this-dose) correct
      value. In all three the model did NOT assert the stale proposition; the NLI flag is a
      template-collision artifact.
    FALSE_POSITIVE_SUPERSESSION_MENTION — the stale value DOES appear in the output, but only inside a
      supersession/retraction clause ("supersedes the original $X, setting it to $Z"): the model
      cites the stale figure to RETRACT it, never asserts it. Also a false positive.
    PROBE_NEEDED_NLI — the stale computed value appears as an apparently-live value not inside a
      supersession clause and is neither threshold nor correct value. Genuinely undecidable by
      string analysis; NLI probe required. (Empirically 0 in this run.)
    """
    if disc["stale_computed_present_in_output"] and disc["probe_needed"]:
        if disc.get("stale_only_in_supersession"):
            return "false_positive_supersession_mention"
        return "probe_needed_nli"
    return "false_positive_instrument"

def aggregate(records, results, corpus):
    by_class = Counter(r["classification"] for r in records)
    by_type = Counter(r["mc_type"] for r in records)
    by_dose = Counter(r["dose"] for r in records)
    by_family = Counter(r["family"] for r in records)
    ack_contaminated = Counter()
    for r in records:
        ack_contaminated["acknowledges" if r["acknowledgment"]["acknowledges"] else "silent"] += 1
    # value items: echo vs no-number
    val = [r for r in records if r["mc_type"] == "value"]
    val_present = sum(1 for r in val if r["echo"]["stale_number_present"])
    # correction position: distribution of unapplied_correction_pos
    pos = Counter(r["unapplied_correction_pos"] for r in records)
    # claim position of stale number (for value items where present)
    # dose totals (all items, for rate)
    dose_items = Counter(); dose_contam = Counter()
    for tid, d in results.items():
        dose = d["routing"]["dose_level"]
        flags = d["arms"]["B"]["must_change_asserted_by_index"]
        dose_items[dose] += len(flags)
        dose_contam[dose] += sum(1 for v in flags.values() if v)
    dose_rate = {dose: round(dose_contam[dose] / dose_items[dose], 4) for dose in dose_items}
    # per-type contamination rate needs per-type totals across ALL items (not just contaminated)
    type_total = Counter(); type_contam = Counter()
    for tid, d in results.items():
        c = corpus[tid]
        flags = d["arms"]["B"]["must_change_asserted_by_index"]
        for idx_s, flag in flags.items():
            t = mc_type(c["must_change"][int(idx_s)])
            type_total[t] += 1
            if flag:
                type_contam[t] += 1
    type_rate = {t: round(type_contam[t] / type_total[t], 4) for t in type_total}
    # probe split by dose/family/type
    probe = [r for r in records if r["classification"] == "probe_needed_nli"]
    fp = [r for r in records if r["classification"].startswith("false_positive")]
    fp_supersession = [r for r in records if r["classification"] == "false_positive_supersession_mention"]
    probe_by_dose = Counter(r["dose"] for r in probe)
    probe_by_family = Counter(r["family"] for r in probe)
    probe_by_item = Counter(r["item_idx"] for r in probe)
    return {
        "by_classification": dict(by_class),
        "false_positive_total": len(fp),
        "false_positive_supersession_mention": len(fp_supersession),
        "probe_needed_nli": len(probe),
        "by_mc_type": dict(by_type),
        "by_dose": dict(by_dose),
        "by_family": dict(by_family),
        "acknowledgment_of_contaminated_outputs": dict(ack_contaminated),
        "value_items_stale_number_present": {"present": val_present, "total_value": len(val),
                                             "absent": len(val) - val_present},
        "unapplied_correction_position": dict(pos),
        "dose_rate_all_items": dose_rate,
        "dose_totals": {d: {"items": dose_items[d], "contam": dose_contam[d]} for d in dose_items},
        "type_rate_all_items": {t: {"total": type_total[t], "contam": type_contam[t], "rate": type_rate[t]}
                                for t in type_total},
        "probe_split": {
            "by_dose": dict(probe_by_dose),
            "by_family": dict(probe_by_family),
            "by_item_idx": dict(probe_by_item),
        },
    }

if __name__ == "__main__":
    main()
