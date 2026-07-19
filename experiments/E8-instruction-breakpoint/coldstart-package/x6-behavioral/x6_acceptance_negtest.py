"""Adversarial test: prove the acceptance gates FIRE on bad data (no false-green)."""
import json, sys
from x6_acceptance import run

def case(cid,cls,correct,wrong,emitted,af=None,aw=None):
    d={"case_id":cid,"cls":cls,"A_correct":str(correct),"A_wrong":(None if wrong is None else str(wrong)),"emitted":str(emitted)}
    return d

# BAD SET 1: positive control MISSES (AC1 should FAIL)
bad_pc=[{"task_id":"t","family_id":"f","arm":"SCOPED","dose_level":1,
         "scored_cases":[case("c","EXCEPTED",2000,700,2000),case("r","RULE",700,2000,700)],
         "positive_control":{"target":"12000","emitted":"twelve thousand","fired":False}}]
r1=run(bad_pc); print("AC1 fail-case:",r1["AC1_positive_controls"]["pass"],"overall",r1["overall_pass"],"gate",r1["verdict_gate"])
assert r1["AC1_positive_controls"]["pass"]==False and r1["overall_pass"]==False

# BAD SET 2: a TT cell present (AC2 should FAIL). emitted==both targets (equal targets forced)
bad_tt=[{"task_id":"t","family_id":"f","arm":"SCOPED","dose_level":1,
         "scored_cases":[case("c","EXCEPTED",2000,700,2000),case("r","RULE",900,900,900)],
         "positive_control":{"target":"900","emitted":"900","fired":True}}]
r2=run(bad_tt); print("AC2 fail-case (TT):",r2["AC2_ff_tt_cells"]["pass"],"tt",r2["AC2_ff_tt_cells"]["tt_total"],"overall",r2["overall_pass"])
assert r2["AC2_ff_tt_cells"]["pass"]==False and r2["overall_pass"]==False

# BAD SET 3: BLANKET decay DECREASING across dose (AC3 should FAIL - incoherent control)
def blanket(dl, decay_frac):
    # make N=10 cases, decay_frac of them wrong
    cases=[]
    for i in range(10):
        wrong = i < int(decay_frac*10)
        cases.append(case(f"r{i}","RULE",700,None, 999 if wrong else 700))
    return {"task_id":f"b{dl}","family_id":"f","arm":"BLANKET","dose_level":dl,"scored_cases":cases,
            "positive_control":{"target":"700","emitted":"700","fired":True}}
bad_dec=[blanket(1,0.8),blanket(2,0.4),blanket(3,0.1)]  # 80%->40%->10% DECREASING
r3=run(bad_dec); print("AC3 fail-case (decreasing):",r3["AC3_srd_gap_reproduction"]["pass"],"curve",r3["AC3_srd_gap_reproduction"]["blanket_decay_curve"],"overall",r3["overall_pass"])
assert r3["AC3_srd_gap_reproduction"]["pass"]==False and r3["overall_pass"]==False

# GOOD SET: BLANKET decay INCREASING (SRD-susceptible-like) should PASS AC3
good_inc=[blanket(1,0.1),blanket(2,0.4),blanket(3,0.7)]
r4=run(good_inc); print("AC3 pass-case (increasing):",r4["AC3_srd_gap_reproduction"]["pass"],"curve",r4["AC3_srd_gap_reproduction"]["blanket_decay_curve"],"kind",r4["AC3_srd_gap_reproduction"]["curve_kind"])
assert r4["AC3_srd_gap_reproduction"]["pass"]==True

print("\nALL NEGATIVE-TEST ASSERTIONS PASSED — gates fire on bad data, pass on good.")
