#!/usr/bin/env python3
"""X4 — deterministic polarity-correcting transform for the E8-A1 depth corpus.

THE BUG (P2-confirmed, 450/450): A1 `must_change` items carry the CORRECTED-world value
(e.g. "Basic MRR is $3,000" = 30x100), but the scorer semantics (outcomes._still_asserts) require
`must_change` to hold the STALE-world value the model must revise AWAY from. A correctly-revising
Arm-B model is therefore scored CONTAMINATED — the axis measures the inverse of its claim.

THE FIX (this file, deterministic, zero model calls):
  1. Recompute every derivation node in the STALE world = substitute corrected_node.a_value for its
     .value, then re-run derivation.ops in order (operators: * + - >= <= ceil_div).
  2. NUMERIC must_change item (strata + numeric primary): find the CORRECTED number in the prose and
     rewrite it to the STALE number. Fail-closed if the corrected number cannot be located uniquely
     (word-form spellouts, ambiguous multi-number prose) — reject the record, never half-transform.
  3. BOOLEAN primary item (final op is a >=/<= comparison; 145/145 flip corr->stale): the free-form
     verdict ("Finance flags the month as healthy") has NO deterministic English negation (82/145
     uncovered by any antonym table — verified). Replace it with a DETERMINISTIC canonical stale
     sentence built from the derivation: "<quantity> is <stale_intermediate>, which <meets|does not
     meet> the <target> <target-noun>." Polarity is the stale boolean. This is the same shape as the
     A3 threshold template and carries the correct stale proposition unambiguously for the NLI scorer.
  4. DROP the insurance item (last must_change entry; P2: 2nd operand unrecoverable in the large
     majority of families; "never leave it in place"). Drop the parallel verdict_item and item_roles
     entries too, keeping them consistent (lead charter req 4).
  5. FAIL-CLOSED per record: after transform, assert every emitted must_change NUMBER equals its
     stale-world node value; assert 0 corrected-world values remain; assert lengths of must_change /
     verdict_item / item_roles are consistent. Any violation => the record is REJECTED and recorded
     in the register with the reason; it is NOT emitted.

Outputs: A1-depth-v2.jsonl (accepted records), transform-register.json (every record's disposition,
per-item before/after, and every drop/reject with reason).
"""
from __future__ import annotations
import json, re, os

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(BASE, "corpus-candidates/A1-depth.jsonl")
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_JSONL = os.path.join(OUT_DIR, "A1-depth-v2.jsonl")
OUT_REGISTER = os.path.join(OUT_DIR, "transform-register.json")

OPS = {
    "*": lambda a, b: a * b,
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    "ceil_div": lambda a, b: -(-a // b),
}

class RejectRecord(Exception):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)

# ---------- stale-world computation ----------
def compute_vals(ap, use_a):
    """Return {label: value} for all derivation outputs. use_a swaps the corrected node to a_value."""
    nodes = {n["label"]: n["value"] for n in ap["derivation"]["nodes"]}
    cn = ap["corrected_node"]
    if use_a:
        nodes[cn["label"]] = cn["a_value"]
    vals = dict(nodes)
    for op in ap["derivation"]["ops"]:
        ins = op["in"]
        if ins[0] not in vals or ins[1] not in vals:
            raise RejectRecord(f"op {op['id']} operand not resolvable: {ins}")
        vals[op["output"]] = OPS[op["operator"]](vals[ins[0]], vals[ins[1]])
    return vals

def op_outputs(ap, use_a):
    """Ordered list of op output values (parallel to non-insurance must_change items)."""
    vals = compute_vals(ap, use_a)
    return [vals[op["output"]] for op in ap["derivation"]["ops"]], vals

# ---------- number formatting / prose rewrite ----------
def fmt_int_or_float(v):
    if isinstance(v, float) and v == int(v):
        v = int(v)
    return v

def number_forms(v):
    """All string forms a numeric value could appear as in prose (comma / no-comma / $ / decimal)."""
    v = fmt_int_or_float(v)
    forms = set()
    if isinstance(v, int):
        forms |= {str(v), f"{v:,}"}
    else:
        # floats: as-is, 2dp (e.g. 4.5 -> '4.50'), and comma-grouped 2dp
        forms |= {str(v), f"{v:.2f}", f"{v:,.2f}"}
        if v == round(v, 1):
            forms.add(f"{v:.1f}")
    return {f"${f}" for f in list(forms)} | forms

def rewrite_numeric(prose, corrected_val, stale_val):
    """Replace the corrected number in prose with the stale number, preserving $/comma/decimal style.
    Fail-closed: the corrected number must appear EXACTLY ONCE in a recognizable numeric form and no
    other transform ambiguity. Returns the rewritten prose."""
    cf = number_forms(corrected_val)
    # match the longest corrected form present (prefer $ + comma + decimal forms)
    present = sorted((f for f in cf if f in prose), key=len, reverse=True)
    if not present:
        raise RejectRecord(f"corrected value {corrected_val!r} not found verbatim in prose {prose!r}")
    token = present[0]
    # count occurrences of THIS token to ensure a unique swap
    if prose.count(token) != 1:
        raise RejectRecord(f"corrected token {token!r} not unique in prose {prose!r}")
    # build the stale token mirroring the corrected token's style ($ and comma presence)
    stale_token = mirror_style(token, corrected_val, stale_val)
    new_prose = prose.replace(token, stale_token, 1)
    # post: the corrected value's distinctive form must be gone as a STANDALONE number (word-boundary
    # aware, so the stale '-60' does not count as a leftover '60', and '$3,000'->'$2,500' is clean).
    if (fmt_int_or_float(stale_val) != fmt_int_or_float(corrected_val)
            and _standalone_number_present(new_prose, token)):
        raise RejectRecord(f"corrected token {token!r} still present after rewrite: {new_prose!r}")
    return new_prose

def _standalone_number_present(text, token):
    """True if `token` (a numeric string, possibly $-prefixed) appears in text as a standalone number,
    i.e. not immediately preceded by a digit/minus/dot or followed by a digit/comma/dot. This lets a
    stale '-60' or '160' not read as a leftover corrected '60'."""
    esc = re.escape(token)
    # not preceded by digit, '-', '.', or '$' (unless token itself starts with $); not followed by
    # digit, ',' or '.'
    pat = r'(?<![\d\-.$])' + esc + r'(?![\d.,])'
    if token.startswith("$"):
        pat = r'(?<![\d\-.])' + esc + r'(?![\d.,])'
    return re.search(pat, text) is not None

def mirror_style(token, corrected_val, stale_val):
    """Render stale_val in the same $/comma/decimal style as the corrected token."""
    has_dollar = token.startswith("$")
    body = token[1:] if has_dollar else token
    has_comma = "," in body
    has_decimal = "." in body
    sv = fmt_int_or_float(stale_val)
    if has_decimal or isinstance(sv, float):
        # decimal places = match corrected token's decimals, default 2
        dp = len(body.split(".")[1]) if has_decimal else 2
        s = f"{sv:,.{dp}f}" if has_comma else f"{sv:.{dp}f}"
    else:
        s = f"{sv:,}" if has_comma else f"{sv}"
    return ("$" + s) if has_dollar else s

# ---------- boolean primary canonical sentence ----------
def canonical_bool_sentence(ap, stale_vals):
    """Deterministic stale-verdict sentence for a boolean primary whose final op is a >=/<= compare.
    'The <quantity> is <stale_intermediate>, which <meets|does not meet|is within|exceeds> the
    <target> <target-noun>.' Polarity = the stale boolean."""
    lastop = ap["derivation"]["ops"][-1]
    if lastop["operator"] not in (">=", "<="):
        raise RejectRecord(f"boolean primary final op is {lastop['operator']!r}, not a comparison")
    q_label, t_label = lastop["in"]
    q_val = stale_vals[q_label]
    t_val = stale_vals[t_label]
    stale_bool = OPS[lastop["operator"]](q_val, t_val)
    q_txt = fmt_int_or_float(q_val)
    t_txt = fmt_int_or_float(t_val)
    q_str = f"{q_txt:,}" if isinstance(q_txt, int) else f"{q_txt:,.2f}"
    t_str = f"{t_txt:,}" if isinstance(t_txt, int) else f"{t_txt:,.2f}"
    # verb from operator + polarity: >= means "meets/at-least"; <= means "is within/at-most"
    if lastop["operator"] == ">=":
        verb = "meets or exceeds" if stale_bool else "falls short of"
    else:
        verb = "is within" if stale_bool else "exceeds"
    return (f"The {q_label} is {q_str}, which {verb} the {t_str} {t_label}."), stale_bool

# ---------- per-record transform ----------
def transform_record(rec):
    ap = rec["axis_params"]
    roles = list(ap["item_roles"])
    verdict = list(ap["verdict_item"])
    mc = list(rec["must_change"])
    mc_depth = list(rec.get("must_change_depth", []))
    n_mc = len(mc)
    if not (len(roles) == len(verdict) == n_mc):
        raise RejectRecord(f"length mismatch roles/verdict/must_change: {len(roles)}/{len(verdict)}/{n_mc}")

    corr_outs, corr_vals = op_outputs(ap, use_a=False)
    stale_outs, stale_vals = op_outputs(ap, use_a=True)
    n_ops = len(ap["derivation"]["ops"])

    non_ins_idx = [k for k, r in enumerate(roles) if r != "insurance"]
    ins_idx = [k for k, r in enumerate(roles) if r == "insurance"]
    if len(non_ins_idx) != n_ops:
        raise RejectRecord(f"non-insurance item count {len(non_ins_idx)} != ops {n_ops}")

    # sanity: corrected op outputs must equal the corresponding node values (corpus integrity)
    per_item = []
    new_mc = []
    new_roles = []
    new_verdict = []
    new_depth = []
    emitted_numeric = []  # (stale_val)

    for pos, k in enumerate(non_ins_idx):
        corr_v = corr_outs[pos]
        stale_v = stale_outs[pos]
        role = roles[k]
        old = mc[k]
        if isinstance(corr_v, bool):
            # boolean primary -> canonical stale sentence
            new_text, stale_bool = canonical_bool_sentence(ap, stale_vals)
            if stale_bool != stale_v:
                raise RejectRecord("boolean recompute inconsistency")
            per_item.append({"role": role, "kind": "boolean", "corrected": old,
                             "corrected_bool": corr_v, "stale_bool": stale_v, "stale": new_text})
        else:
            # numeric -> rewrite prose
            new_text = rewrite_numeric(old, corr_v, stale_v)
            emitted_numeric.append((new_text, fmt_int_or_float(stale_v)))
            per_item.append({"role": role, "kind": "numeric", "corrected": old,
                             "corrected_val": fmt_int_or_float(corr_v),
                             "stale_val": fmt_int_or_float(stale_v), "stale": new_text})
        new_mc.append(new_text)
        new_roles.append(role)
        new_verdict.append(verdict[k])
        if k < len(mc_depth):
            new_depth.append(mc_depth[k])

    # ---- DROP insurance ----
    dropped = [{"index": k, "text": mc[k]} for k in ins_idx]

    # ---- FAIL-CLOSED assertions ----
    # (a) every emitted numeric must_change value must contain the STALE value in a recognizable form.
    #     (We check presence of the stale form, not "first number == stale": prose may carry entity
    #     labels like "Rosa-2" or nouns with incidental digits that are not the quantity value.)
    for text, stale_val in emitted_numeric:
        forms = number_forms(stale_val)
        if not any(f in text for f in forms):
            raise RejectRecord(f"post-assert: stale value {stale_val!r} not present in emitted prose {text!r}")
    # (b) ZERO corrected-world values remain: no emitted numeric must_change contains the corrected
    #     value's distinctive form when stale differs
    for pos, k in enumerate(non_ins_idx):
        corr_v = corr_outs[pos]
        if isinstance(corr_v, bool):
            continue
        stale_v = stale_outs[pos]
        if fmt_int_or_float(corr_v) == fmt_int_or_float(stale_v):
            continue  # coincides; unavoidable, not a leak
        emitted = new_mc[pos]
        for f in number_forms(corr_v):
            # only flag $/comma forms (bare small ints like '2' can appear incidentally in nouns),
            # boundary-aware so a stale '-60' is not read as a leftover corrected '60'
            if (f.startswith("$") or "," in f) and _standalone_number_present(emitted, f):
                raise RejectRecord(f"corrected-world value leak: {f!r} in {emitted!r}")
    # (c) consistency of parallel arrays
    if not (len(new_mc) == len(new_roles) == len(new_verdict)):
        raise RejectRecord("post-transform array length mismatch")
    if "insurance" in new_roles:
        raise RejectRecord("insurance role survived the drop")

    out = dict(rec)
    out["must_change"] = new_mc
    out["must_change_depth"] = new_depth
    out_ap = dict(ap)
    out_ap["item_roles"] = new_roles
    out_ap["verdict_item"] = new_verdict
    out_ap["x4_transform"] = {
        "polarity": "stale",
        "insurance_dropped": dropped,
        "method": "numeric-prose-rewrite + boolean-canonical",
    }
    out["axis_params"] = out_ap
    return out, {"task_id": rec["task_id"], "status": "accepted", "per_item": per_item,
                 "insurance_dropped": dropped}

def extract_single_number(text):
    nums = re.findall(r'-?\$?\d[\d,]*(?:\.\d+)?', text)
    if not nums:
        return None
    # take the FIRST number (the quantity value in these templates)
    t = nums[0].replace("$", "").replace(",", "")
    try:
        return float(t)
    except ValueError:
        return None

def main():
    recs = [json.loads(l) for l in open(SRC)]
    accepted = []
    register = []
    n_reject = 0
    for rec in recs:
        try:
            out, info = transform_record(rec)
            accepted.append(out)
            register.append(info)
        except RejectRecord as e:
            n_reject += 1
            register.append({"task_id": rec["task_id"], "status": "rejected", "reason": e.reason})
    with open(OUT_JSONL, "w") as f:
        for r in accepted:
            f.write(json.dumps(r) + "\n")
    summary = {
        "source": SRC,
        "n_source": len(recs),
        "n_accepted": len(accepted),
        "n_rejected": n_reject,
        "insurance_items_dropped": sum(len(r.get("insurance_dropped", [])) for r in register
                                       if r["status"] == "accepted"),
        "records": register,
    }
    with open(OUT_REGISTER, "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps({k: summary[k] for k in
                      ["n_source", "n_accepted", "n_rejected", "insurance_items_dropped"]}, indent=2))
    return summary

if __name__ == "__main__":
    main()
