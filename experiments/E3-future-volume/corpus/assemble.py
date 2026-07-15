"""
Reproducible assembly of corpus/candidates.jsonl -- the script the corpus was missing.

It is DECLARATIVE: it reads the current candidates.jsonl as the base, then applies
  (1) ARITH_VERIFY : attach a machine-checkable `verify` arithmetic expression to every arithmetic
      item so its gold is recomputed from scratch (never asserted) -- CORPUS.md labeling protocol;
  (2) REPLACEMENTS : replace-in-place (same id, new content) for the 6 decontamination fixes and the
      d4 kind-based hardening conversions. Every replacement item is disjoint from the disposable
      manifest and carries its own verification hook (`verify` for arithmetic, `ded_spec` for
      deduction re-derivation, source note for factual).
Counts (42/42/42/37/37) are preserved because every change is in-place. The output is verified by
assemble_verify.py (run it after this). Re-runnable and deterministic.

d4 additions carry: difficulty=4, hard_kind (the calibrated kind label), and expected_diversity
"mid" (their role is correctness-NEGATIVE injection for the e3-0003 AUROC arm, not volume-band
extension; see CORPUS.md).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CANDIDATES = HERE / "candidates.jsonl"
sys.path.insert(0, str(HERE.parent / "hardening"))

# --- (1) arithmetic gold recomputation exprs (every arithmetic id) -------------------------------
ARITH_VERIFY = {
    "arith-001": "8*7", "arith-002": "144/12", "arith-003": "25+38", "arith-004": "90-47",
    "arith-005": "6**2", "arith-006": "15*4", "arith-007": "100-63", "arith-008": "9*9",
    "arith-009": "72/8", "arith-010": "13+29", "arith-011": "7*12", "arith-012": "45+55",
    "arith-013": "84/7", "arith-014": "11*11",
    "arith-016": "0.20*150", "arith-017": "3+4*5", "arith-018": "(12+8)/4", "arith-019": "7*6-10",
    "arith-020": "250/5+12", "arith-021": "96/2", "arith-022": "0.30*90", "arith-023": "2**6",
    "arith-024": "(10+20+30)/3", "arith-025": "18*5-40", "arith-026": "0.08*50",
    "arith-027": "1000/25", "arith-028": "14**2",
    "arith-029": "40*0.75", "arith-030": "12*5", "arith-031": "150/10", "arith-032": "3*24-12",
    "arith-033": "300/25", "arith-034": "2*9", "arith-035": "500*0.60", "arith-036": "5*12",
    "arith-037": "18*7", "arith-038": "70/1.4", "arith-039": "2*(8+6)", "arith-040": "3*12.50",
    "arith-041": "32*0.75", "arith-042": "(600-450)/600*100",
    # arith-015 omitted here: it is REPLACED below (was the byte-exact pilot duplicate).
}


def _arith(id_, difficulty, prompt, gold, expr, div, hard_kind=None):
    it = {"id": id_, "family": "arithmetic", "prompt": prompt, "gold": gold,
          "difficulty": difficulty, "expected_diversity": div,
          "provenance": "hand-authored, GSM8K-style word/number problem (original)",
          "answerable": True, "verify": expr}
    if hard_kind:
        it["hard_kind"] = hard_kind
    return it


def _fact(id_, difficulty, prompt, gold, div, accept=None, verify=None, hard_kind=None, prov=None):
    it = {"id": id_, "family": "factual", "prompt": prompt, "gold": gold,
          "difficulty": difficulty, "expected_diversity": div,
          "provenance": prov or "hand-authored, TriviaQA/NaturalQuestions-style closed question (original)",
          "answerable": True}
    if accept:
        it["accept"] = accept
    if verify:
        it["verify"] = verify
    if hard_kind:
        it["hard_kind"] = hard_kind
    return it


def _ded(id_, difficulty, prompt, gold, div, ded_spec=None, hard_kind=None):
    it = {"id": id_, "family": "deduction", "prompt": prompt, "gold": gold,
          "difficulty": difficulty, "expected_diversity": div,
          "provenance": "hand-authored, bAbI/ProofWriter-style forced-answer logic (original)",
          "answerable": True}
    if ded_spec:
        it["ded_spec"] = ded_spec
    if hard_kind:
        it["hard_kind"] = hard_kind
    return it


def _crea(id_, difficulty, prompt, div):
    return {"id": id_, "family": "creative", "prompt": prompt, "gold": None,
            "difficulty": difficulty, "expected_diversity": div,
            "provenance": "hand-authored, open-generation prompt (original)", "answerable": False}


# --- (2) replacements: decontamination (6) + d4 hardening conversions ----------------------------
# Filled by build() from DECON + D4_CONVERSIONS below so the two concerns are documented separately.

# 2a. decontamination -- 6 ids flagged by decontaminate.py, replaced in place with clean,
#     disposable-disjoint content at the SAME family and difficulty.
DECON = {
    "arith-015": _arith("arith-015", 2, "What is 45 percent of 80?", "36", "0.45*80", "low"),
    "fact-003": _fact("fact-003", 1, "How many wheels does a standard bicycle have?", "2", "low",
                      verify="2"),
    "fact-028": _fact("fact-028", 2, "How many sides does a pentagon have?", "5", "low",
                      verify="5"),
    # NOTE: fact-037 (currency of Japan) is NOT here -- it is a d3 slot and is decontaminated AND
    # hardened in one move by the d4 conversion below (fact-037 -> reverse superheavy lookup).
    "crea-031": _crea("crea-031", 3, "Invent a board game and describe how it is played.", "high"),
    "crea-036": _crea("crea-036", 3,
                      "Invent a musical instrument and describe the sound it makes.", "high"),
}

# 2b. d4 hardening conversions -- 14 per answerable family, mapped onto the d3 ids they replace.
from d4_items import build_d4  # noqa: E402
D4_CONVERSIONS: dict[str, dict] = build_d4()


def load_base():
    return [json.loads(l) for l in CANDIDATES.read_text().splitlines() if l.strip()]


def build(write=True):
    rows = load_base()
    replacements = {**DECON, **D4_CONVERSIONS}
    out = []
    for r in rows:
        rid = r["id"]
        if rid in replacements:
            out.append(replacements[rid])
            continue
        if r["family"] == "arithmetic" and rid in ARITH_VERIFY and "verify" not in r:
            r = {**r, "verify": ARITH_VERIFY[rid]}
        out.append(r)
    if write:
        with CANDIDATES.open("w") as f:
            for r in out:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"[assemble] wrote {len(out)} items "
              f"({len(DECON)} decontam + {len(D4_CONVERSIONS)} d4 conversions applied)")
    return out


if __name__ == "__main__":
    build()
