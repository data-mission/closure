"""Hand-computed toy test for x6_verdict.aggregate/compute_verdict.

Constructs a tiny result set with KNOWN cell outcomes covering TF/FT/FF/TT + guard-D + BLANKET, and
asserts the aggregator's counts match the hand computation exactly. Run on the Mini (needs
closure_harness.stats). This is the aggregator acceptance evidence.
"""
import json
import sys
from x6_verdict import aggregate, compute_verdict


def case(cid, cls, correct, wrong, emitted):
    return {"case_id": cid, "cls": cls, "A_correct": str(correct),
            "A_wrong": (None if wrong is None else str(wrong)), "emitted": str(emitted)}


rows = []
# --- SCOPED family F1, dose 3, exception RETAINED (EXCEPTED=TF): 1 RULE over-generalized (FT),
#     1 NEW correct (TF). Expect scoped[3]: over=1 trials=2 ---
rows.append({"task_id": "F1-S-T3", "family_id": "F1", "arm": "SCOPED", "dose_level": 3,
             "scored_cases": [
                 case("c", "EXCEPTED", 2000, 700, 2000),     # TF (retained)
                 case("r", "RULE", 700, 2000, 2000),         # FT (applied exception to rule case) = over
                 case("n", "NEW", 500, 2000, 500),           # TF (correct)
             ]})
# --- SCOPED family F2, dose 3, exception LOST (EXCEPTED=FT: agent applied rule to c): guard-D drops
#     its RULE/NEW from the over-rate; excepted_lost[3] += 1 ---
rows.append({"task_id": "F2-S-T3", "family_id": "F2", "arm": "SCOPED", "dose_level": 3,
             "scored_cases": [
                 case("c", "EXCEPTED", 3000, 800, 800),      # FT (applied rule to c = exception lost)
                 case("r", "RULE", 800, 3000, 3000),         # would be FT but NOT counted (excepted lost)
             ]})
# --- SCOPED F1 doses 1,2 to give a monotone-ish over curve (retained) ---
rows.append({"task_id": "F1-S-T1", "family_id": "F1", "arm": "SCOPED", "dose_level": 1,
             "scored_cases": [case("c", "EXCEPTED", 2000, 700, 2000),
                              case("r", "RULE", 700, 2000, 700),   # TF correct
                              case("n", "NEW", 500, 2000, 500)]})  # TF correct  -> over=0 trials=2
rows.append({"task_id": "F1-S-T2", "family_id": "F1", "arm": "SCOPED", "dose_level": 2,
             "scored_cases": [case("c", "EXCEPTED", 2000, 700, 2000),
                              case("r", "RULE", 700, 2000, 2000),  # FT over
                              case("n", "NEW", 500, 2000, 500)]})  # TF  -> over=1 trials=2
# --- FF diagnostic: a RULE case with an unparseable emitted (word value) => FF, not counted ---
rows.append({"task_id": "F3-S-T3", "family_id": "F3", "arm": "SCOPED", "dose_level": 3,
             "scored_cases": [case("c", "EXCEPTED", 2000, 700, 2000),        # TF retained
                              case("r", "RULE", 700, 2000, "seven hundred")]})  # FF (unparseable)
# --- TT bug: emitted equals BOTH targets (impossible normally; force by equal targets) => TT ---
rows.append({"task_id": "F4-S-T3", "family_id": "F4", "arm": "SCOPED", "dose_level": 3,
             "scored_cases": [case("c", "EXCEPTED", 2000, 700, 2000),
                              case("r", "RULE", 900, 900, 900)]})  # A_correct==A_wrong==emitted => TT
# --- BLANKET family F1 doses: decay measured as (1-correct) on RULE/NEW ---
rows.append({"task_id": "F1-B-T3", "family_id": "F1", "arm": "BLANKET", "dose_level": 3,
             "scored_cases": [case("r", "RULE", 700, None, 999),   # not correct => decay
                              case("n", "NEW", 500, None, 500)]})  # correct  -> decay=1 trials=2
rows.append({"task_id": "F1-B-T1", "family_id": "F1", "arm": "BLANKET", "dose_level": 1,
             "scored_cases": [case("r", "RULE", 700, None, 700),
                              case("n", "NEW", 500, None, 500)]})  # both correct -> decay=0 trials=2
rows.append({"task_id": "F1-B-T2", "family_id": "F1", "arm": "BLANKET", "dose_level": 2,
             "scored_cases": [case("r", "RULE", 700, None, 700),
                              case("n", "NEW", 500, None, 500)]})  # decay=0 trials=2

agg = aggregate(rows)

# ---- HAND ASSERTIONS ----
checks = []
def chk(name, got, exp):
    ok = got == exp
    checks.append((name, got, exp, ok))

chk("scoped[3].over", agg["scoped"][3]["over"], 1)         # F1 r=FT (F2 dropped, F3 FF, F4 TT)
chk("scoped[3].trials", agg["scoped"][3]["trials"], 2)     # F1 r(FT)+n(TF); F3/F4 excluded
chk("scoped[2].over", agg["scoped"][2]["over"], 1)
chk("scoped[2].trials", agg["scoped"][2]["trials"], 2)
chk("scoped[1].over", agg["scoped"][1]["over"], 0)
chk("scoped[1].trials", agg["scoped"][1]["trials"], 2)
chk("excepted_lost[3]", agg["excepted_lost"][3], 1)        # F2 exception lost
chk("ff[3]", agg["ff"][3], 1)                              # F3 r FF
chk("tt[3]", agg["tt"][3], 1)                              # F4 r TT
chk("blanket[3].decay", agg["blanket"][3]["decay"], 1)     # F1-B-T3 r not-correct
chk("blanket[3].trials", agg["blanket"][3]["trials"], 2)
chk("blanket[1].decay", agg["blanket"][1]["decay"], 0)

passed = all(c[3] for c in checks)
for name, got, exp, ok in checks:
    print(f"  {'OK ' if ok else 'FAIL'} {name}: got {got} expected {exp}")
print("AGGREGATOR TOY TEST:", "PASS" if passed else "FAIL")

# also exercise compute_verdict end-to-end (needs stats); just assert it runs + returns a verdict tag
v = compute_verdict(rows, theta=0.10, delta=0.05)
print("verdict status:", v["status"], "| break:", v["break_verdict"],
      "| scoped rates:", [v["scoped_per_dose"][str(L)]["rate"] for L in (1,2,3)])
print("TT present =>", v["status"] == "WITHHELD", "(expected WITHHELD due to F4 TT)")
sys.exit(0 if passed else 1)
