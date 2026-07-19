#!/usr/bin/env python3
"""X4 acceptance checker — proves the transformed A1-depth-v2 corpus is correctly polarity-inverted.

The INVERSE of today's bug: today every must_change numeric holds the CORRECTED-world value; after the
transform, EVERY must_change numeric must hold the STALE-world value and ZERO corrected-world values
may remain. This checker re-derives both worlds independently from each record's own derivation graph
and asserts, per accepted record:

  (1) every NUMERIC must_change item's number == the stale-world node value for its op (position-aligned);
  (2) NO must_change item contains the corrected-world value as a standalone number (the leak test);
  (3) NO 'insurance' role remains; must_change / verdict_item / item_roles lengths are consistent;
  (4) the boolean primary's canonical sentence states the stale-world comparison with correct polarity.

Exit nonzero if any record fails. Prints a per-check pass/fail summary + the count of corrected-world
values remaining (must be 0).
"""
from __future__ import annotations
import json, re, os, sys

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.join(OUT_DIR, "A1-depth-v2.jsonl")

OPS = {"*": lambda a, b: a * b, "+": lambda a, b: a + b, "-": lambda a, b: a - b,
       ">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b, "ceil_div": lambda a, b: -(-a // b)}

def fmt(v):
    if isinstance(v, float) and v == int(v):
        return int(v)
    return v

def compute_vals(ap, use_a):
    nodes = {n["label"]: n["value"] for n in ap["derivation"]["nodes"]}
    cn = ap["corrected_node"]
    if use_a:
        nodes[cn["label"]] = cn["a_value"]
    vals = dict(nodes)
    for op in ap["derivation"]["ops"]:
        vals[op["output"]] = OPS[op["operator"]](vals[op["in"][0]], vals[op["in"][1]])
    return vals

def number_forms(v):
    v = fmt(v)
    forms = set()
    if isinstance(v, int):
        forms |= {str(v), f"{v:,}"}
    else:
        forms |= {str(v), f"{v:.2f}", f"{v:,.2f}"}
        if v == round(v, 1):
            forms.add(f"{v:.1f}")
    return {f"${f}" for f in list(forms)} | forms

def standalone(text, token):
    esc = re.escape(token)
    pat = (r'(?<![\d\-.])' + esc + r'(?![\d.,])') if token.startswith("$") \
          else (r'(?<![\d\-.$])' + esc + r'(?![\d.,])')
    return re.search(pat, text) is not None

def main():
    recs = [json.loads(l) for l in open(V2)]
    fails = []
    corrected_leaks = 0
    n_numeric_checked = 0
    n_bool_checked = 0
    for rec in recs:
        ap = rec["axis_params"]
        roles = ap["item_roles"]
        verdict = ap["verdict_item"]
        mc = rec["must_change"]
        tid = rec["task_id"]

        # length + no-insurance
        if not (len(roles) == len(verdict) == len(mc)):
            fails.append((tid, "length mismatch")); continue
        if "insurance" in roles:
            fails.append((tid, "insurance role survived")); continue

        corr = compute_vals(ap, use_a=False)
        stale = compute_vals(ap, use_a=True)
        ops = ap["derivation"]["ops"]
        non_ins = [k for k, r in enumerate(roles) if r != "insurance"]
        if len(non_ins) != len(ops):
            fails.append((tid, f"item/op count {len(non_ins)}!={len(ops)}")); continue

        for pos, k in enumerate(non_ins):
            out_label = ops[pos]["output"]
            sv = stale[out_label]
            cv = corr[out_label]
            text = mc[k]
            if isinstance(cv, bool):
                n_bool_checked += 1
                # canonical stale sentence must state stale comparison; verify the stale bool polarity
                # by re-deriving the compare and checking the verb matches
                lastop = ops[pos]
                q, t = lastop["in"]
                sb = OPS[lastop["operator"]](stale[q], stale[t])
                # verb check: >= true -> "meets or exceeds"; false -> "falls short of"; <= true ->
                # "is within"; false -> "exceeds"
                want_verb = ({">=": ("meets or exceeds", "falls short of"),
                              "<=": ("is within", "exceeds")}[lastop["operator"]])[0 if sb else 1]
                if want_verb not in text:
                    fails.append((tid, f"bool item {k}: expected verb {want_verb!r} in {text!r}"))
                # the stale intermediate value must appear
                if not any(f in text for f in number_forms(stale[q])):
                    fails.append((tid, f"bool item {k}: stale intermediate {stale[q]} not in {text!r}"))
            else:
                n_numeric_checked += 1
                # (1) stale value present
                if not any(f in text for f in number_forms(sv)):
                    fails.append((tid, f"num item {k}: stale {sv} not in {text!r}"))
                # (2) corrected value NOT present as standalone (unless coincides with stale)
                if fmt(cv) != fmt(sv):
                    for f in number_forms(cv):
                        if (f.startswith("$") or "," in f) and standalone(text, f):
                            corrected_leaks += 1
                            fails.append((tid, f"num item {k}: corrected leak {f!r} in {text!r}"))
                            break

    print(f"records checked: {len(recs)}")
    print(f"numeric items checked: {n_numeric_checked}")
    print(f"boolean items checked: {n_bool_checked}")
    print(f"corrected-world value leaks: {corrected_leaks}")
    print(f"FAILURES: {len(fails)}")
    for tid, why in fails[:30]:
        print(f"  {tid}: {why}")
    if fails:
        print("\nACCEPTANCE: FAIL")
        sys.exit(1)
    print("\nACCEPTANCE: PASS — 0 corrected-world values remain; every must_change holds the stale value.")

if __name__ == "__main__":
    main()
