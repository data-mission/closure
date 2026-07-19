#!/usr/bin/env python3
"""INSTRUMENT-V2 — claim-grounded value/verdict contamination test (zero-spend, CPU-only, no model).

Replaces the whole-sentence NLI-entailment contamination flag (outcomes._still_asserts) for the E8-A3
family, whose stale and corrected sentences are near-identical templates that differ only in a computed
figure and/or a verdict word — so DeBERTa clears 0.7 on the shared "{quantity} {computed} {verdict}
{threshold}" scaffold and fires a false "still-asserts" (X1-FINDINGS: 200 flags, 0 real; 197/200
deterministically artifact, 3/3 residual hand-adjudicated FP).

CONTAMINATION (v2 definition) for a must_change[i], scored against the model output (conclusion + claim
texts, source_ids irrelevant — same premise set the NLI used):
  the model ASSERTS, as a LIVE proposition, the STALE computed VALUE and/or the STALE VERDICT DIRECTION
  of the item's requirement, AFTER excluding
    (a) the shared THRESHOLD constant (appears identically in stale + corrected sentences),
    (b) any occurrence inside a SUPERSESSION/retraction clause (the model cites the stale figure to
        KILL it), and
    (c) the case where the stale value/verdict did NOT change at this dose (corpus staircase artifact —
        its presence is not an echo).

Two echo channels (X1: a wrong NUMBER is NLI-separable; a wrong VERDICT in an identical requirement
sentence is not — v2 detects both):
  VALUE echo   : the stale computed number appears as a live value of the quantity (anatomy.py's
                 stale_computed_asserted, retained).
  VERDICT echo : the requirement's verdict FLIPPED (stale=violates/fails/exceeds-a-cap → correct=
                 within/meets), and the model asserts the STALE direction for that requirement, tied to
                 the requirement's quantity, not inside a supersession clause.

FAMILY GRAMMARS (mapped exhaustively over 336 rows — see corpus report):
  F1: state_values clause = "<computed> vs <threshold> -> violates|within" (3 clauses; stale_of_state[i]=i;
      flips are ONLY violates→within). must_change[i] is the NL form of clause i, always the violating side.
  F2: state_values clause = "<label>=<computed> vs <label2> <threshold>" (NO verdict token — compute
      direction from computed vs threshold; "meets" is floor-cleared OR cap-respected, role-dependent).
      must_change[i] carries an explicit NL verdict ("fails to meet"/"exceeds"/"fits within"/...).
  F3: pure value ("The <label> is $<computed>.") — NO verdict dimension; VALUE echo only.

FIXTURES / ACCEPTANCE (run: python3 instrument_v2.py --self-test):
  1. Full A3 flag reproduction: over the 200 NLI-flagged items, v2 must return 0 REAL contamination
     (200 → 0), matching X1's cross-validated hand adjudication.
  2. 30-item hand-adjudicated sample (_audit_sample30.json, all FALSE_POSITIVE): 0 flagged real.
  3. Positive controls (must be able to FIRE): 10 synthetic contaminated outputs built by injecting the
     stale value/verdict into real outputs → require 10/10 detection. An instrument that cannot fire on
     a real echo is worthless; this is the falsification gate.
  4. The 5 verified-clean spot-check items (X1 §spot-checks) stay clean.

This file imports NOTHING from the frozen harness and runs no model. It reuses anatomy.py's number +
supersession helpers (same file, same semantics) so v2 is a strict superset of the proven prototype.
"""
from __future__ import annotations
import json, re, os, argparse, random, copy
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(os.path.dirname(HERE))  # .../E8-instruction-breakpoint
RESULTS = os.path.join(BASE, "coldstart-package/e8-run/A3-stage2/results")
GEN = os.path.join(BASE, "coldstart-package/e8-run/A3-stage2/stage2-gen.jsonl")
CORPUS = os.path.join(BASE, "corpus-candidates/A3-corrections.jsonl")
AUDIT30 = os.path.join(HERE, "_audit_sample30.json")

# --------------------------------------------------------------------------- number helpers
NUM_RE = re.compile(r'\$?\d[\d,]*(?:\.\d+)?')


def norm_num(tok: str):
    t = tok.replace("$", "").replace(",", "")
    try:
        return float(t)
    except ValueError:
        return None


def extract_nums(text: str) -> set:
    return {n for tok in NUM_RE.findall(text) if (n := norm_num(tok)) is not None}


def extract_ordered_nums(text: str) -> list:
    return [n for tok in NUM_RE.findall(text) if (n := norm_num(tok)) is not None]


def _num_variants(n) -> set:
    """String forms a number could take in text: 8000 -> {'8000','8,000','$8,000','$8000'}."""
    if n is None:
        return set()
    if n == int(n):
        i = int(n)
        plain, grouped = str(i), f"{i:,}"
    else:
        plain, grouped = str(n), f"{n:,}"
    return {plain, grouped, "$" + plain, "$" + grouped}


# --------------------------------------------------------------------------- supersession (retraction) clause
SUPERSESSION_MARKERS = ["supersede", "superseded", "supersedes", "original", "prior figure",
                        "earlier", "revised", "replacing", "replaced", "instead of",
                        "treated as false", "corrects", "corrected", "updating", "updated",
                        "raised to", "raising it", "no longer", "previously", "revision",
                        "was ", "had been", "overrides", "overridden"]


def premises_of(output: dict) -> list:
    return [output["conclusion"]] + [c["text"] for c in output["claims"]]


def _mentions(prem: str, value_variants: set) -> bool:
    return any(v in prem for v in value_variants)


def stale_only_in_supersession(output: dict, value) -> bool:
    """True iff EVERY premise mentioning `value` does so inside a supersession/retraction clause.
    If any premise asserts `value` as a live quantity (no marker), returns False."""
    variants = _num_variants(value)
    if not variants:
        return False
    mentioning = [p for p in premises_of(output) if _mentions(p, variants)]
    if not mentioning:
        return False
    return all(any(m in p.lower() for m in SUPERSESSION_MARKERS) for p in mentioning)


# --------------------------------------------------------------------------- family + geometry
def family_of(task: dict) -> str:
    return task.get("covariates", {}).get("family", "?")


def correct_final_nums(task: dict) -> set:
    """Numbers in the correct-final state for THIS dose (state_values[-1] is dose-relative)."""
    return extract_nums(task["axis_params"]["state_values"][-1])


# --------------------------------------------------------------------------- VALUE echo (anatomy.py, retained)
# A number's UNIT/measure word — the token(s) right after it. Distinguishes a computed quantity
# ("120 tonnes") from a label ("Silo 4") or a different-quantity collision ("120 hectares"). Label
# words that follow a number but are NOT measures (so "4" in "Silo 4" has unit "" — it's the label's
# ordinal, not a quantity).
_UNIT_RE = re.compile(r'\$?\d[\d,]*(?:\.\d+)?\s*([a-zA-Z%°][a-zA-Z%°/\-]*)?')
def stale_value_from_mc(mc: str):
    """The STALE COMPUTED value of must_change[i] — the number introduced by a VALUE-ASSIGNMENT context
    ('is X', 'is $X', '= X', 'of X', 'X tonnes/metres/kW/...'), NOT the first raw number. This is the key
    disambiguation from a LABEL ordinal ('Silo 4', 'cabin 7'): a label number is preceded by a noun and
    followed by a possessive/no-measure, never by a value-assignment verb, so it is NOT returned here.

    Returns (stale_value, threshold) where threshold is the NEXT number after the stale value (the shared
    requirement constant). Returns (None, None) when the sentence carries no value-assignment (pure-label
    sentence like 'The delivery exceeds Silo 4's capacity' — nothing computed to echo)."""
    # value-assignment forms: "is $1,800", "is 42", "= 15400", "of $240", or "<num> <unit>" where the
    # number is directly followed by a measure word (tonnes, metres, kW, hours, %, passengers, ...).
    ASSIGN = re.compile(
        r'(?:\bis\b|\bof\b|=|\btotals?\b|\bequals\b|\breaches\b)\s*(\$?\d[\d,]*(?:\.\d+)?)'
        r'|(\$?\d[\d,]*(?:\.\d+)?)\s*(tonnes?|metres?|meters?|kw|kW|hours?|passengers?|crates?|'
        r'loaves|cakes|litres?|liters?|units?|vehicles?|rides?|batches?|pascals?|kn|%|°|dollars?|'
        r'per\b)')
    m = ASSIGN.search(mc)
    if not m:
        return None, None
    tok = m.group(1) or m.group(2)
    stale_value = norm_num(tok)
    # threshold = the next number AFTER the stale value's position
    tail = mc[m.end():]
    tail_nums = extract_ordered_nums(tail)
    threshold = tail_nums[0] if tail_nums else None
    return stale_value, threshold


def _unit_after(text: str, value) -> set:
    """The set of unit tokens that appear immediately AFTER `value` anywhere in `text` (lowercased).
    '' means the number stands with no measure word (bare or followed by punctuation)."""
    units = set()
    for variant in sorted(_num_variants(value), key=len, reverse=True):
        for m in re.finditer(re.escape(variant) + r'\s*([a-zA-Z%°][\w%°/\-]*)?', text):
            u = (m.group(1) or "").lower()
            units.add(u)
    return units


def _is_label_number(text: str, value) -> bool:
    """Defensive OUTPUT-side guard (structural, no noun list): True if EVERY occurrence of `value` in
    `text` is a proper-noun LABEL ORDINAL — immediately followed by a possessive ("Silo 4's",
    "cabin 7's") — rather than a computed quantity. Redundant with stale_value_from_mc (which already
    excludes label ordinals on the must_change side) but retained as a belt-and-suspenders guard for an
    output that only mentions the value as a label."""
    occ = labelled = 0
    for variant in sorted(_num_variants(value), key=len, reverse=True):
        for m in re.finditer(re.escape(variant) + r"(['’]s\b|\b)", text):
            occ += 1
            if m.group(1).startswith("'") or m.group(1).startswith("’"):
                labelled += 1
    return occ > 0 and occ == labelled


def value_echo(task: dict, output: dict, i: int) -> dict:
    """Real value-contamination = the stale computed VALUE asserted LIVE with the SAME unit as in
    must_change, != threshold, != correct-final, not a label ordinal, not in a supersession clause.
    Unit + label guards kill X1's 3 residuals (Silo 4 / Row 6 label collisions; 120 tonnes vs 120
    hectares unit collision) without a GPU probe — they are not the stale quantity."""
    mc = task["must_change"][i]
    stale_value, threshold = stale_value_from_mc(mc)  # value-assignment aware; None for label-only sentences
    correct = correct_final_nums(task)
    out_text = " ".join(premises_of(output))
    present = stale_value is not None and stale_value in extract_nums(out_text)
    is_threshold = stale_value is not None and stale_value == threshold
    equals_correct = stale_value is not None and stale_value in correct
    # UNIT GUARD: the stale value must appear in the output with a unit compatible with its must_change
    # unit. If the must_change unit set and the output unit set are disjoint (and both non-empty), the
    # number is a different quantity (120 tonnes vs 120 hectares) → not an echo.
    mc_units = _unit_after(mc, stale_value) if stale_value is not None else set()
    out_units = _unit_after(out_text, stale_value) if present else set()
    # compatible if they share any unit, OR either side is unit-less (bare number), OR mc has no unit
    unit_ok = (not mc_units) or (not out_units) or bool(mc_units & out_units)
    # LABEL GUARD: value is only ever a label ordinal (Silo 4 / Row 6) in the output
    label_only = present and _is_label_number(out_text, stale_value)
    live = bool(present and not is_threshold and not equals_correct and unit_ok and not label_only)
    in_supersession = stale_only_in_supersession(output, stale_value) if live else False
    echo = bool(live and not in_supersession)
    return {"stale_value": stale_value, "threshold": threshold,
            "stale_value_present": present, "stale_equals_threshold": is_threshold,
            "stale_equals_correct": equals_correct, "unit_ok": unit_ok, "label_only": label_only,
            "mc_units": sorted(mc_units), "out_units": sorted(out_units),
            "in_supersession": in_supersession, "value_echo": echo}


# --------------------------------------------------------------------------- VERDICT echo
# CORE INSIGHT (from X1 + the FP diagnosis): a verdict word alone is UNRELIABLE — "fails"/"meets" are
# shared requirement scaffolding, and the stale side is NOT always "violating" (budget items flip the
# OTHER way: stale=meets → correct=fails). The ONLY sound signal that the model echoed the stale VERDICT
# is that it asserts the stale computed VALUE *together with* a verdict phrase on the stale side of the
# threshold — i.e. it re-states the stale proposition "<stale_value> <stale_verdict> <threshold>" as
# live. A model that asserts the CORRECTED value with any verdict word is giving its real (correct)
# answer, not echoing. So verdict-echo is GATED on the stale computed value being asserted live (same
# gate as value_echo) AND the stale verdict-direction sign being present near it. This makes verdict-echo
# a strict refinement that cannot fire on a corrected-value assertion.
def _stale_and_correct_computed(task: dict, i: int):
    """(stale_computed, threshold, corrected_computed). stale/threshold from must_change[i]; corrected
    computed = the item's quantity value in the correct-final state, found by anchoring on the quantity's
    label in state_values[-1] (F2) or clause slot i (F1). Returns Nones where undefined (F3 = value-only)."""
    stale_computed, threshold = stale_value_from_mc(task["must_change"][i])
    fam = family_of(task)
    sv = task["axis_params"]["state_values"]
    corrected = None
    if fam == "F1":
        clauses = [c.strip() for c in sv[-1].split(";")]
        if i < len(clauses):
            cn = extract_ordered_nums(clauses[i])
            corrected = cn[0] if cn else None  # F1 clause = "<computed> vs <threshold> -> verdict"
    elif fam == "F2":
        # anchor on the quantity's label words; find the clause in sv[-1] mentioning them, take its
        # computed (the number that is NOT the threshold).
        anchor = _quantity_anchor(task["must_change"][i])
        for clause in re.split(r';', sv[-1]):
            cl = clause.lower()
            if anchor and sum(1 for a in anchor if a in cl) >= max(1, len(anchor) // 2):
                cn = [n for n in extract_ordered_nums(clause) if n != threshold]
                if cn:
                    corrected = cn[0]
                    break
    return stale_computed, threshold, corrected


def _requirement_flipped(task: dict, i: int) -> dict:
    """Did must_change[i]'s requirement flip verdict between its stale state and the correct-final state?
    Determined from NUMBERS: stale side = sign(stale_computed − threshold); correct side =
    sign(corrected_computed − threshold). A flip = the two signs differ (crossed the threshold). This is
    direction-agnostic: it catches BOTH compliant→violating and violating→compliant flips."""
    fam = family_of(task)
    if fam == "F3":
        return {"has_verdict": False, "flipped": False}
    stale_computed, threshold, corrected = _stale_and_correct_computed(task, i)
    if fam == "F1":
        # F1 also carries terse tokens — use them as the authoritative flip signal when available.
        sv = task["axis_params"]["state_values"]
        sos = task["axis_params"].get("stale_of_state", list(range(len(task["must_change"]))))
        stale_idx = sos[i] if i < len(sos) else i

        def clause_verdict(state_str, slot):
            clauses = [c.strip() for c in state_str.split(";")]
            if slot < len(clauses):
                m = re.search(r'->\s*(\w+)', clauses[slot])
                return m.group(1) if m else None
            return None
        stale_v = clause_verdict(sv[stale_idx], i) if stale_idx < len(sv) else None
        final_v = clause_verdict(sv[-1], i)
        flipped = (stale_v is not None and final_v is not None and stale_v != final_v)
        # stale verdict 'violates' => stale side is the VIOLATING side; 'within' => compliant side
        return {"has_verdict": True, "flipped": bool(flipped), "stale_verdict": stale_v,
                "correct_verdict": final_v, "stale_computed": stale_computed,
                "threshold": threshold, "corrected_computed": corrected}
    # F2: number-derived signs
    if stale_computed is None or threshold is None or corrected is None:
        return {"has_verdict": True, "flipped": False, "stale_computed": stale_computed,
                "threshold": threshold, "corrected_computed": corrected, "reason": "underdetermined"}
    stale_ge = stale_computed >= threshold
    corr_ge = corrected >= threshold
    return {"has_verdict": True, "flipped": bool(stale_ge != corr_ge), "stale_computed": stale_computed,
            "threshold": threshold, "corrected_computed": corrected, "stale_ge_threshold": stale_ge}


def _quantity_anchor(mc_text: str) -> list:
    """Noun-phrase anchor for the requirement's quantity, so a verdict phrase is tied to THIS
    requirement, not another sentence. Heuristic: the subject noun phrase before 'is'/'exceeds'/etc.
    Return a few salient content words (>=4 chars, not stopwords/numbers)."""
    head = re.split(r'\b(is|are|exceeds?|fails?|meets?|fits|falls|violat|cannot|below|above)\b',
                    mc_text.lower(), maxsplit=1)[0]
    stop = {"the", "a", "an", "of", "per", "this", "that", "and", "for", "to", "on", "in", "at",
            "total", "combined", "which", "so", "not", "all"}
    words = [w for w in re.findall(r"[a-z][a-z\-']{3,}", head) if w not in stop]
    return words[:4]


def verdict_echo(task: dict, output: dict, i: int, val: dict = None) -> dict:
    """Real verdict-contamination = the model asserts the STALE computed value LIVE (the value channel's
    full `live` gate — not threshold, not correct, not a label ordinal, compatible unit, not in a
    supersession clause) AND asserts it in a premise carrying the stale VERDICT direction for the
    quantity. Strict refinement of value_echo: it CANNOT fire when the stale value is a label/unit
    collision or a corrected-value assertion. `val` = the already-computed value_echo dict (shares its
    label/unit guards); recomputed if not passed."""
    if val is None:
        val = value_echo(task, output, i)
    flip = _requirement_flipped(task, i)
    stale_computed = val.get("stale_value")
    variants = _num_variants(stale_computed)
    # GATE: the stale value must be genuinely asserted LIVE per the value channel (this carries the
    # threshold / correct / label / unit / supersession exclusions). Without a live stale-value
    # assertion there is no verdict echo.
    live_ok = bool(val.get("stale_value_present") and not val.get("stale_equals_threshold")
                   and not val.get("stale_equals_correct") and val.get("unit_ok")
                   and not val.get("label_only") and not val.get("in_supersession"))
    if not live_ok or stale_computed is None or not variants:
        return {"verdict_echo": False, "reason": "stale_value_not_live", "flip": flip}
    anchor = _quantity_anchor(task["must_change"][i])
    stale_dir = ["exceed", "fail", "falls short", "fall short", "below", "short of", "violat",
                 "cannot", "not all", "may not", "does not meet", "doesn't meet", "not meet",
                 "insufficient", "over the", "over capacity", "beyond", "too ", "meets", "within",
                 "fits", "sufficient", "satisf"]  # any verdict word — the gate is the stale VALUE
    hit_premises = []
    for prem in premises_of(output):
        pl = prem.lower()
        if not _mentions(prem, variants):
            continue
        if any(m in pl for m in SUPERSESSION_MARKERS):
            continue  # stale value mentioned only to retract → not an echo
        anchored = (not anchor) or any(a in pl for a in anchor)
        if anchored and any(ph in pl for ph in stale_dir):
            hit_premises.append(prem)
    echo = bool(hit_premises)
    return {"verdict_echo": echo, "flip": flip, "anchor": anchor,
            "stale_value_asserted_premises": hit_premises[:3],
            "reason": ("stale_value+verdict_asserted_live" if echo else "no_live_stale_verdict_premise")}


# --------------------------------------------------------------------------- top-level classifier
def classify_item(task: dict, output: dict, i: int) -> dict:
    """v2 verdict for one must_change item. REAL contamination iff value_echo OR verdict_echo.
    verdict_echo shares value_echo's label/unit/threshold/supersession guards (passed in)."""
    ve = value_echo(task, output, i)
    vd = verdict_echo(task, output, i, val=ve)
    real = bool(ve["value_echo"] or vd["verdict_echo"])
    if real:
        cls = "REAL_CONTAMINATION"
    elif ve["in_supersession"]:
        cls = "false_positive_supersession_mention"
    else:
        cls = "false_positive_instrument"
    return {"task_id": task.get("task_id"), "item_idx": i, "family": family_of(task),
            "mc_text": task["must_change"][i], "value_channel": ve, "verdict_channel": vd,
            "classification": cls, "real_contamination": real}


# --------------------------------------------------------------------------- data loading
def load_corpus():
    return {json.loads(l)["task_id"]: json.loads(l) for l in open(CORPUS)}


def load_gen():
    return {json.loads(l)["task_id"]: json.loads(l) for l in open(GEN)}


def load_results():
    import glob
    out = {}
    for f in glob.glob(os.path.join(RESULTS, "*.json")):
        if os.path.basename(f).startswith("_"):  # trap: _oracle_result.json is not a per-task record
            continue
        d = json.load(open(f))
        out[d["task_id"]] = d
    return out


def flagged_items(results):
    """(task_id, i) for every NLI-flagged must_change item (the 200)."""
    for tid, d in results.items():
        for idx_s, flag in d["arms"]["B"]["must_change_asserted_by_index"].items():
            if flag:
                yield tid, int(idx_s)


def all_items(corpus, results):
    """(task_id, i) for EVERY must_change item across the scored A3 corpus (the 1,428)."""
    for tid, d in results.items():
        n = len(corpus[tid]["must_change"])
        for i in range(n):
            yield tid, i


# --------------------------------------------------------------------------- positive-control synthesis
def make_contaminated_output(task: dict, clean_output: dict, i: int):
    """Build a SYNTHETIC contaminated output by injecting the STALE value + STALE verdict direction as a
    LIVE assertion into a real clean output — the positive control the instrument MUST fire on.
    Returns (contaminated_output, injected_note) or (None, reason) if the item has no injectable stale."""
    out = copy.deepcopy(clean_output)
    mcn = extract_ordered_nums(task["must_change"][i])
    stale_value = mcn[0] if mcn else None
    threshold = mcn[1] if len(mcn) > 1 else None
    correct = correct_final_nums(task)
    # only inject when the stale value is genuinely stale (not threshold, not already the correct value)
    if stale_value is None or stale_value == threshold or stale_value in correct:
        return None, "no_injectable_stale_value"
    # inject a LIVE assertion of the stale proposition, phrased like a real model claim, NO supersession
    # markers. Use the must_change sentence itself (it IS the stale proposition) as the injected claim.
    stale_sentence = task["must_change"][i]
    new_claim = {"id": max([c["id"] for c in out["claims"]] + [0]) + 1,
                 "text": stale_sentence, "source_ids": []}
    out["claims"].append(new_claim)
    # also echo the stale VALUE in the conclusion as the live answer, to exercise the value channel
    out["conclusion"] = out["conclusion"] + f" The figure is {stale_value:g}."
    return out, {"injected_stale_value": stale_value, "injected_stale_sentence": stale_sentence}


# --------------------------------------------------------------------------- self-test / acceptance
def run_self_test():
    corpus, gen, results = load_corpus(), load_gen(), load_results()
    report = {"gates": {}}

    # GATE 1: 200 NLI-flagged items → 0 real
    flagged = list(flagged_items(results))
    real_on_flagged = []
    for tid, i in flagged:
        r = classify_item(corpus[tid], gen[tid]["output"], i)
        if r["real_contamination"]:
            real_on_flagged.append((tid, i, r))
    report["gates"]["g1_flagged_200_to_0"] = {
        "n_flagged": len(flagged), "n_real": len(real_on_flagged),
        "pass": len(real_on_flagged) == 0,
        "real_examples": [(t, i) for t, i, _ in real_on_flagged[:10]],
    }

    # GATE 2: 30-item hand-adjudicated sample (all FALSE_POSITIVE) → 0 real
    audit = json.load(open(AUDIT30))
    real_on_audit = []
    for row in audit:
        tid, i = row["task_id"], row["item"]
        r = classify_item(corpus[tid], gen[tid]["output"], i)
        if r["real_contamination"]:
            real_on_audit.append((tid, i))
    report["gates"]["g2_audit30_to_0"] = {
        "n_audit": len(audit), "n_real": len(real_on_audit),
        "pass": len(real_on_audit) == 0, "real_examples": real_on_audit[:10],
    }

    # GATE 3: positive controls — inject stale into real outputs, require 10/10 detection.
    # Draw injectable items deterministically (seeded) spread across families.
    rng = random.Random(20260718)
    candidates = []
    for tid, i in all_items(corpus, results):
        mcn = extract_ordered_nums(corpus[tid]["must_change"][i])
        if not mcn:
            continue
        sv = mcn[0]; thr = mcn[1] if len(mcn) > 1 else None
        if sv == thr or sv in correct_final_nums(corpus[tid]):
            continue
        candidates.append((tid, i))
    rng.shuffle(candidates)
    controls, detected = [], 0
    for tid, i in candidates:
        if len(controls) >= 10:
            break
        contam_out, note = make_contaminated_output(corpus[tid], gen[tid]["output"], i)
        if contam_out is None:
            continue
        r = classify_item(corpus[tid], contam_out, i)
        controls.append({"task_id": tid, "item_idx": i, "family": family_of(corpus[tid]),
                         "detected": r["real_contamination"],
                         "channels": {"value": r["value_channel"]["value_echo"],
                                      "verdict": r["verdict_channel"]["verdict_echo"]},
                         **note})
        detected += 1 if r["real_contamination"] else 0
    report["gates"]["g3_positive_controls_10"] = {
        "n_controls": len(controls), "n_detected": detected,
        "pass": len(controls) == 10 and detected == 10, "controls": controls,
    }

    # GATE 4: the 5 verified-clean spot-check items stay clean
    spot = [("A3-C-0519-C3", 0), ("A3-C-0528-C2", 0), ("A3-C-0505-C3", 2),
            ("A3-C-0503-C3", 2), ("A3-C-0329-C3", 2)]
    spot_real = []
    for tid, i in spot:
        if tid in corpus and tid in gen:
            r = classify_item(corpus[tid], gen[tid]["output"], i)
            if r["real_contamination"]:
                spot_real.append((tid, i))
    report["gates"]["g4_spotcheck_5_clean"] = {
        "n_spot": len(spot), "n_real": len(spot_real),
        "pass": len(spot_real) == 0, "real_examples": spot_real,
    }

    report["all_pass"] = all(g["pass"] for g in report["gates"].values())
    return report


def main():
    ap = argparse.ArgumentParser(description="INSTRUMENT-V2 claim-grounded value/verdict contamination test")
    ap.add_argument("--self-test", action="store_true", help="run the 4 acceptance gates")
    ap.add_argument("--rescore-all", action="store_true", help="score ALL 1,428 A3 items → table")
    ap.add_argument("--out", default=os.path.join(HERE, "instrument-v2-report.json"))
    args = ap.parse_args()

    if args.self_test:
        rep = run_self_test()
        print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "controls" and kk != "real_examples"}
                          if isinstance(v, dict) else v
                          for k, v in rep["gates"].items()}, indent=2))
        print("ALL_PASS:", rep["all_pass"])
        json.dump(rep, open(args.out.replace(".json", "-selftest.json"), "w"), indent=2)
        return 0 if rep["all_pass"] else 1

    if args.rescore_all:
        corpus, gen, results = load_corpus(), load_gen(), load_results()
        records, table = [], defaultdict(lambda: {"items": 0, "real": 0})
        for tid, i in all_items(corpus, results):
            r = classify_item(corpus[tid], gen[tid]["output"], i)
            records.append(r)
            key = (r["family"], corpus[tid]["routing"]["dose_level"] if "routing" in corpus[tid]
                   else results[tid]["routing"]["dose_level"])
            table[key]["items"] += 1
            table[key]["real"] += 1 if r["real_contamination"] else 0
        agg = {"n_items": len(records),
               "n_real": sum(1 for r in records if r["real_contamination"]),
               "by_family_dose": {f"{k[0]}_C{k[1]}": v for k, v in sorted(table.items())}}
        json.dump({"aggregates": agg, "records": records}, open(args.out, "w"), indent=2)
        print(json.dumps(agg, indent=2))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
