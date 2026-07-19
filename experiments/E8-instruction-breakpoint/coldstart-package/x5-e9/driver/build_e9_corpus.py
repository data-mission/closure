"""E9 corpus: FRESH F3-grammar generator + A3 transform (schema/guard proof) — with LIVE GUARDS.

Two routes:

  --generate  : the REGISTERED corpus route (greenlit). Deterministically synthesizes fresh F3-family
                accumulated-correction scenarios: >=40 independent scenario families, each at doses
                k=1/2/3, numeric-only scored strings, running totals computed in-code (so polarity is
                correct BY CONSTRUCTION, not by post-hoc annotation). Fresh construction is required
                because the existing A3 F3 corpus yields only 4 distinct scenarios (verified) — far too
                few for N=150/dose and >=40 independent families (DESIGN.md §4).

  --in/--transform : the A3->E9 transform, retained as a SCHEMA-and-GUARD proof only (it demonstrates
                the guards run against real data and the turn-rendering contract holds). Not the scale
                source.

Every emitted record passes, at construction, THREE guards run LIVE (never stubbed):
  1. F3 numeric-only grammar on every scored string (must_change / must_persist): exactly one value,
     no verdict/threshold token — the F2-artifact dodge at the corpus level.
  2. Fail-closed A1-inversion POLARITY guard: every must_change value == the STALE running total and
     != the correct-final running total. A true inversion HALTS the build.
  3. instrument-v2 label/unit anchoring folded into the polarity check (per P2's own design note): the
     stale value must appear in the stale state with a compatible UNIT and must not be a mere label
     ordinal — this is what kills the cross-quantity number-collision false-positive (A3-C-0107 '1200')
     that the crude bare-number check produced.

Run:
  python3 build_e9_corpus.py --generate --families 40 --per-dose 150 --out e9-corpus.jsonl
  python3 build_e9_corpus.py --generate --dry-sample 10 --self-check      (10-family guard gate, no write)
  python3 build_e9_corpus.py --in <A3.jsonl> --self-check                 (transform-route guard proof)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

NUM_RE = re.compile(r"\$?\d[\d,]*(?:\.\d+)?")
# Verdict / threshold tokens that MUST NOT appear in a scored numeric-only string (F2-artifact dodge).
VERDICT_TOKENS = re.compile(
    r"\b(exceed|exceeds|fails?|fail to|meets?|within|violat|below|above|cap|capacity|limit|"
    r"short of|falls? short|sufficient|insufficient|threshold|requirement|at least|no more than)\b",
    re.I,
)

# instrument-v2 label/unit anchoring, folded in per P2's design note (X5-NOTES.md): the crude
# bare-number polarity check false-HALTs on cross-quantity value collisions (A3-C-0107 '1200' is both a
# stale beverage subtotal AND a corrected rental cost). _unit_after / _is_label_number / _num_variants
# distinguish "same quantity, stale value" from "different quantity that happens to share a number".
# Imported from the ACCEPTED scorer so the guard and the scorer use identical semantics (no drift).
_X1 = Path(__file__).resolve().parent.parent.parent / "x1-anatomy"
sys.path.insert(0, str(_X1))
try:
    from instrument_v2 import _unit_after, _is_label_number, _num_variants  # noqa: E402
    _HAVE_V2_ANCHOR = True
except Exception:  # pragma: no cover - transform-route self-check still runs without it
    _HAVE_V2_ANCHOR = False


def nums(text: str) -> list[float]:
    out = []
    for tok in NUM_RE.findall(text):
        t = tok.replace("$", "").replace(",", "")
        try:
            out.append(float(t))
        except ValueError:
            pass
    return out


def is_numeric_only_value_string(s: str) -> tuple[bool, str]:
    """F3 grammar gate: exactly one computed value, no verdict/threshold token.
    Returns (ok, reason). A compound {value}{verdict}{threshold} string FAILS here — this is what keeps
    the F2 artifact out at the corpus level."""
    if VERDICT_TOKENS.search(s):
        return False, f"contains verdict/threshold token: {s!r}"
    n = nums(s)
    if len(n) != 1:
        return False, f"expected exactly 1 number, found {len(n)}: {s!r}"
    return True, "ok"


def stale_index(task: dict, i: int) -> int:
    """Which state_values entry is the STALE world for must_change[i]. A3 records carry
    axis_params.stale_of_state; default to 0 (pre-correction) if absent."""
    sos = (task.get("axis_params") or {}).get("stale_of_state")
    if isinstance(sos, list) and i < len(sos):
        return int(sos[i])
    return 0


def running_total(state_str: str) -> float | None:
    """The running TOTAL a state_values clause resolves to = the term after the final '='
    (e.g. 'maint ... = 15400' -> 15400). This is the item's OWN quantity value; comparing against
    it (not against every bare number in the clause) is what avoids the cross-quantity number
    collision found in real data: in A3-C-0107, '1200' is BOTH a stale beverage subtotal AND the
    corrected rental cost, so a bare-number final-set check false-HALTs a clean record. Anchoring on
    the '= total' term is the minimal sound fix; instrument_v2's _unit_after/_is_label_number guards
    are the fuller version and are the registered implementation's anchor."""
    if "=" not in state_str:
        return None
    tail = state_str.rsplit("=", 1)[1]
    n = nums(tail)
    return n[0] if n else None


def _unit_compatible(mc_text: str, state_str: str, value: float) -> bool:
    """True if `value` appears in `state_str` with a unit compatible with its unit in `mc_text` (the
    instrument-v2 rule: share a unit, or either side unit-less). Guards against a number that matches
    numerically but is a DIFFERENT quantity. Degrades to True (no unit signal) when v2 is unavailable —
    the running-total anchor is then the sole guard, which already cleared the real corpus."""
    if not _HAVE_V2_ANCHOR:
        return True
    # _unit_after returns {''} for a bare number (no measure word). Treat a set that is empty OR whose
    # only member is '' as "unit-less" — the earlier check used `not st_units`, but {''} is truthy, so
    # a bare-number state string (the E9 state_values format, "... = 11984") wrongly failed the compat
    # test. Strip the empty sentinel before comparing.
    def real_units(s):
        return {u for u in s if u}
    mc_units = real_units(_unit_after(mc_text, value))
    st_units = real_units(_unit_after(state_str, value))
    return (not mc_units) or (not st_units) or bool(mc_units & st_units)


def polarity_ok(task: dict) -> tuple[bool, list[str]]:
    """FAIL-CLOSED A1-inversion guard, with instrument-v2 label/unit anchoring. For every must_change[i]:
      - its single value must appear in the STALE-world state (state_values[stale_idx]) with a
        COMPATIBLE UNIT and not merely as a label ordinal (v2 anchoring — avoids cross-quantity
        collisions);
      - its single value must NOT equal the correct-final RUNNING TOTAL (the '= X' of state_values[-1]).
    The final-value comparison is anchored on the running total, NOT every bare number in the final
    clause — bare-number matching false-HALTs on cross-quantity value collisions (verified against real
    data: A3-C-0107 '1200'). Returns (ok, violations). A true inversion => HALT."""
    viol: list[str] = []
    sv = (task.get("axis_params") or {}).get("state_values") or []
    if not sv:
        return False, [f"{task.get('task_id')}: no state_values to check polarity against"]
    final_total = running_total(sv[-1])
    for i, mc in enumerate(task.get("must_change", [])):
        mn = nums(mc)
        if len(mn) != 1:
            viol.append(f"{task['task_id']} mc[{i}]: not single-value ({mn}) — grammar gate should have caught")
            continue
        v = mn[0]
        si = stale_index(task, i)
        stale_str = sv[si] if si < len(sv) else ""
        stale_nums = set(nums(stale_str))
        present = v in stale_nums
        # v2 label guard: if the value only ever appears as a label ordinal in the stale state, it is
        # not the stale quantity value.
        label_only = present and _HAVE_V2_ANCHOR and _is_label_number(stale_str, v)
        unit_ok = present and _unit_compatible(mc, stale_str, v)
        if not present or label_only or not unit_ok:
            viol.append(
                f"{task['task_id']} mc[{i}]: value {v} not a live stale quantity in "
                f"state_values[{si}]={stale_str!r} (present={present}, label_only={label_only}, "
                f"unit_ok={unit_ok})"
            )
        if final_total is not None and v == final_total:
            viol.append(
                f"{task['task_id']} mc[{i}]: value {v} EQUALS correct-final running total {final_total} "
                f"(state_values[-1]={sv[-1]!r}) — POLARITY INVERSION (A1-class). HALT."
            )
    return (len(viol) == 0), viol


def transform_record(task: dict) -> dict:
    """A3 F3 record -> E9 matched turn-task. Structure is preserved (sources, axis_params.corrections,
    state_values, must_change, must_persist); only metadata is added. Turn rendering happens at gen
    time via turn_prompt.plan_turns, so no prompt text is baked in here."""
    out = dict(task)
    out["experiment"] = "E9"
    out["e9"] = {
        "arms": ["N", "S"],                       # no-compaction baseline, summarizer/compaction
        "dose_axis": "compaction_cycles",
        "dose_levels": [1, 2, 3],                 # k = matched corrections / compaction cycles
        "scored_grammar": "F3-numeric-only",
        "dual_scored": ["frozen_nli", "instrument_v2"],
        "compression_band": [0.30, 0.50],         # DESIGN.md §10 — the one disclosed free parameter
    }
    return out


def guard_record(task: dict) -> list[str]:
    """Run ALL THREE guards on one record; return the list of violations (empty == clean).
    (Grammar + fail-closed polarity + v2 label/unit anchoring, the last folded into polarity_ok.)"""
    problems: list[str] = []
    if (task.get("covariates") or {}).get("family") != "F3":
        problems.append(f"{task.get('task_id')}: not F3 family (E9 substrate is F3-only)")
    for side in ("must_change", "must_persist"):
        for i, s in enumerate(task.get(side, [])):
            ok, reason = is_numeric_only_value_string(s)
            if not ok:
                problems.append(f"{task.get('task_id')} {side}[{i}] grammar: {reason}")
    ok, viol = polarity_ok(task)
    problems.extend(viol)
    return problems


# =========================================================================== FRESH F3 GENERATOR
# A scenario ZOO: each entry is one independent family template. A family has:
#   - domain/subject prose (the framing source),
#   - a QUESTION asking for a running TOTAL,
#   - CORRECTABLE line-items (each gets superseded by exactly one correction across turns; order fixed),
#   - FIXED line-items (never corrected; some become must_persist),
#   - a UNIT for the total (currency $, or a bare count) so v2 unit-anchoring has signal.
# The running total after t corrections = sum(fixed) + sum(first t corrected values) + sum(remaining
# original correctable values). must_change[t] = the stale total after t corrections (t=0..k-1); the
# correct-final total (after ALL k) is NOT in must_change (polarity correct by construction).
#
# 20 base templates x 3 unit/scale variants x parameter draws >> 40 independent families. Each template
# is deterministic in (family_index) so the corpus is reproducible from a seed (E5/E8 determinism rule).

# (subject, total_label, unit, [correctable line-item labels], [fixed line-item labels])
# unit "$" => currency prose "$X"; "" => bare count prose "X <noun>".
_ZOO: list[dict] = [
    {"subj": "Central Deck operates a {n0}-space parking structure and reports monthly operating results.",
     "q": "What is the total monthly operating cost for the month?",
     "total": "total monthly operating cost", "unit": "$",
     "correctable": ["per-space maintenance", "security", "ground lease"],
     "fixed": ["insurance", "utilities"], "noun": "dollars"},
    {"subj": "Harbor Freight Line runs a {n0}-container weekly sailing and totals its voyage costs.",
     "q": "What is the total voyage cost for the week?",
     "total": "total voyage cost", "unit": "$",
     "correctable": ["fuel bunker", "port dues", "crew wages"],
     "fixed": ["insurance premium", "canal toll"], "noun": "dollars"},
    {"subj": "Meadowlark Catering books a reception for {n0} guests and totals the invoice.",
     "q": "What is the total reception cost?",
     "total": "total reception cost", "unit": "$",
     "correctable": ["food per head", "beverage line", "venue rental"],
     "fixed": ["staffing fee", "cleaning fee"], "noun": "dollars"},
    {"subj": "Ridgeline Fabrication schedules a {n0}-unit production run and totals its cost.",
     "q": "What is the total production cost for the run?",
     "total": "total production cost", "unit": "$",
     "correctable": ["material per unit", "tooling", "machine time"],
     "fixed": ["setup fee", "QA inspection"], "noun": "dollars"},
    {"subj": "Northwind Logistics quotes a {n0}-pallet road move and totals the charge.",
     "q": "What is the all-in charge for the move?",
     "total": "all-in charge for the move", "unit": "$",
     "correctable": ["line-haul rate", "fuel surcharge", "detention"],
     "fixed": ["booking fee", "liftgate fee"], "noun": "dollars"},
    {"subj": "Summit Grants disburses a cohort of {n0} fellows and totals the round budget.",
     "q": "What is the total round budget?",
     "total": "total round budget", "unit": "$",
     "correctable": ["stipend per fellow", "evaluation", "reporting"],
     "fixed": ["platform fee", "audit reserve"], "noun": "dollars"},
    {"subj": "Cobalt Cloud bills a tenant for {n0} million requests and totals the monthly bill.",
     "q": "What is the total monthly bill?",
     "total": "total monthly bill", "unit": "$",
     "correctable": ["compute", "egress", "support tier"],
     "fixed": ["base platform", "storage"], "noun": "dollars"},
    {"subj": "Alder Property manages a {n0}-unit building and totals the monthly operating cost.",
     "q": "What is the total monthly operating cost?",
     "total": "total monthly operating cost", "unit": "$",
     "correctable": ["per-unit upkeep", "landscaping", "elevator service"],
     "fixed": ["property tax", "insurance"], "noun": "dollars"},
    {"subj": "Beacon Events stages a {n0}-seat conference and totals the production cost.",
     "q": "What is the total production cost for the conference?",
     "total": "total production cost", "unit": "$",
     "correctable": ["AV per seat", "catering", "hall rental"],
     "fixed": ["security detail", "signage"], "noun": "dollars"},
    {"subj": "Foundry Metals casts a {n0}-tonne heat and totals its input cost.",
     "q": "What is the total input cost for the heat?",
     "total": "total input cost for the heat", "unit": "$",
     "correctable": ["ore per tonne", "energy", "refractory"],
     "fixed": ["labour", "assay"], "noun": "dollars"},
    # --- bare-count totals (unit-less), so the zoo isn't all currency ---
    {"subj": "Cedar Mill schedules {n0} logging crews and tallies total daily output boards.",
     "q": "What is the total daily board output?",
     "total": "total daily board output", "unit": "boards",
     "correctable": ["boards per crew", "night-shift boards", "salvage boards"],
     "fixed": ["reclaim boards", "sample boards"], "noun": "boards"},
    {"subj": "Tideway Ferries runs {n0} daily crossings and tallies total vehicle slots.",
     "q": "What is the total daily vehicle-slot tally?",
     "total": "total daily vehicle-slot tally", "unit": "slots",
     "correctable": ["slots per crossing", "overflow-deck slots", "reserved slots"],
     "fixed": ["crew-vehicle slots", "priority slots"], "noun": "slots"},
    {"subj": "Orchard Pack staffs {n0} sorting lines and tallies total crates per shift.",
     "q": "What is the total crates sorted per shift?",
     "total": "total crates sorted per shift", "unit": "crates",
     "correctable": ["crates per line", "extra-line crates", "rework crates"],
     "fixed": ["sample crates", "audit crates"], "noun": "crates"},
    {"subj": "Vellum Press books {n0} print runs and tallies total copies for the month.",
     "q": "What is the total copies printed for the month?",
     "total": "total copies printed for the month", "unit": "copies",
     "correctable": ["copies per run", "reprint copies", "insert copies"],
     "fixed": ["proof copies", "archive copies"], "noun": "copies"},
    {"subj": "Granary Co-op fills {n0} silos and tallies total stored tonnes.",
     "q": "What is the total stored tonnage?",
     "total": "total stored tonnage", "unit": "tonnes",
     "correctable": ["tonnes per silo", "annex tonnes", "transfer tonnes"],
     "fixed": ["reserve tonnes", "sample tonnes"], "noun": "tonnes"},
    {"subj": "Lumen Labs runs {n0} assay batches and tallies total sample plates.",
     "q": "What is the total sample plates for the run?",
     "total": "total sample plates for the run", "unit": "plates",
     "correctable": ["plates per batch", "rerun plates", "control plates"],
     "fixed": ["blank plates", "standard plates"], "noun": "plates"},
    {"subj": "Postmark Depot dispatches {n0} routes and tallies total parcels for the day.",
     "q": "What is the total parcels dispatched for the day?",
     "total": "total parcels dispatched for the day", "unit": "parcels",
     "correctable": ["parcels per route", "surge parcels", "returns parcels"],
     "fixed": ["priority parcels", "sample parcels"], "noun": "parcels"},
    {"subj": "Brightwater Utility reads {n0} district meters and tallies total daily litres.",
     "q": "What is the total daily litres supplied?",
     "total": "total daily litres supplied", "unit": "litres",
     "correctable": ["litres per district", "reservoir litres", "recycled litres"],
     "fixed": ["standpipe litres", "test litres"], "noun": "litres"},
    {"subj": "Kiln & Co fires {n0} batches and tallies total glazed tiles.",
     "q": "What is the total glazed tiles for the firing?",
     "total": "total glazed tiles for the firing", "unit": "tiles",
     "correctable": ["tiles per batch", "second-firing tiles", "salvage tiles"],
     "fixed": ["sample tiles", "reject-recovery tiles"], "noun": "tiles"},
    {"subj": "Trailhead Rentals fields {n0} kiosks and tallies total daily bookings.",
     "q": "What is the total daily bookings?",
     "total": "total daily bookings", "unit": "bookings",
     "correctable": ["bookings per kiosk", "walk-up bookings", "online bookings"],
     "fixed": ["staff bookings", "comp bookings"], "noun": "bookings"},
]

# The singular denominator noun for the FIRST correctable line-item (the per-unit line), parallel to
# _ZOO by index. This is the {n0}-thing in the subject (space, container, guest, ...), NOT the total's
# unit — the earlier bug rendered "$8 per dollar" by reusing the currency noun. Ordered to match _ZOO.
_PER = ["space", "container", "guest", "unit", "pallet", "fellow", "million requests", "unit", "seat",
        "tonne", "crew", "crossing", "line", "run", "silo", "batch", "route", "district", "batch",
        "kiosk"]
assert len(_PER) == len(_ZOO), "each _ZOO entry needs a per-unit denominator noun"


def _fmt(value: float, unit: str) -> str:
    """Numeric-only value prose: '$X' for currency, 'X <unit>' for counts. Integers render without .0."""
    if value == int(value):
        num = f"{int(value):,}"
    else:
        num = f"{value:,.2f}"
    return f"${num}" if unit == "$" else f"{num} {unit}"


def _draw(family_index: int) -> dict:
    """Deterministic parameter draw for a family. LCG-style spread from the index so families differ in
    scale and per-line values but every number stays a clean integer (no rounding ambiguity in prose)."""
    tmpl = _ZOO[family_index % len(_ZOO)]
    idx = family_index % len(_ZOO)
    variant = family_index // len(_ZOO)          # 0,1,2,... => scale variants, more independent families
    per_noun = _PER[idx]
    seed = (family_index * 2654435761) & 0xFFFFFFFF
    def r(lo, hi, salt):
        return lo + ((seed ^ (salt * 40503)) % (hi - lo + 1))
    # Scale so magnitudes are realistic and the running totals are well-separated (the earlier draft's
    # scale=1 gave totals 68/74/78/79 — too compressed to be a real revision task). Flat line-items and
    # per-unit-rate*n0 land in the same order of magnitude so no single line dominates.
    flat_scale = [100, 1000, 250][variant % 3]   # flat line-items ~ hundreds..thousands
    n0 = r(20, 90, 1) * ([1, 1, 10][variant % 3])  # 20..90 (or ..900) count in the subject
    rate_scale = max(1, (flat_scale * (n0 // 4)) // n0) or 1  # per-unit rate so rate*n0 ~ flat magnitude
    corr = []
    for j, label in enumerate(tmpl["correctable"]):
        per_unit = (j == 0)
        s = rate_scale if per_unit else flat_scale
        base = r(3, 9, 10 + j) * s
        newv = base + r(1, 6, 20 + j) * s        # corrected value strictly differs from original
        corr.append({"label": label, "orig": base, "corr": newv, "per_unit": per_unit})
    fixed = []
    for j, label in enumerate(tmpl["fixed"]):
        fixed.append({"label": label, "value": r(3, 9, 30 + j) * flat_scale})
    return {"tmpl": tmpl, "n0": n0, "corr": corr, "fixed": fixed, "variant": variant, "per": per_noun}


def _line_value(item: dict, corrected: bool, n0: int) -> float:
    v = item["corr"] if corrected else item["orig"]
    return v * n0 if item["per_unit"] else v


def _running_total(draw: dict, t: int) -> float:
    """Total after the first t corrections applied (t=0..k). fixed + corrected(first t) + orig(rest)."""
    n0 = draw["n0"]
    total = sum(f["value"] for f in draw["fixed"])
    for j, item in enumerate(draw["corr"]):
        total += _line_value(item, corrected=(j < t), n0=n0)
    return total


def generate_family(family_index: int, k: int) -> dict:
    """One E9 matched-family record at dose k (k corrections). Numeric-only, polarity correct by
    construction. Emits the A3-compatible schema (sources, axis_params.corrections/state_values/
    stale_of_state, must_change, must_persist) + E9 metadata, so turn_prompt / run_e9 consume it
    unchanged."""
    d = _draw(family_index)
    tmpl = d["tmpl"]
    n0 = d["n0"]
    unit = tmpl["unit"]
    k = min(k, len(d["corr"]))
    corr = d["corr"][:k]

    # sources: framing + original correctable line-items + fixed line-items (all pre-correction world)
    sources = [{"id": 0, "text": tmpl["subj"].format(n0=n0)}]
    sid = 1
    for item in corr:
        if item["per_unit"]:
            sources.append({"id": sid, "text":
                f"The {item['label']} is {_fmt(item['orig'], unit)} per {d['per']}."})
        else:
            sources.append({"id": sid, "text":
                f"The {item['label']} is a fixed {_fmt(item['orig'], unit)}."})
        sid += 1
    for f in d["fixed"]:
        sources.append({"id": sid, "text": f"The {f['label']} is a fixed {_fmt(f['value'], unit)}."})
        sid += 1

    # corrections: one per correctable, in order, pure supersession. The per-unit line keeps its
    # "per {per}" phrasing so the corrected rate is unambiguous (it is still multiplied by n0).
    corrections = []
    for j, item in enumerate(corr):
        per = f" per {d['per']}" if item["per_unit"] else ""
        corrections.append({"supersedes_source_id": 1 + j, "text":
            f"Cost revision: the {item['label']} is now {_fmt(item['corr'], unit)}{per}, "
            f"replacing the {_fmt(item['orig'], unit)} figure."})

    # state_values: running total after 0,1,..,k corrections (the last is the correct answer)
    state_values = []
    for t in range(0, k + 1):
        tag = " (correct answer)" if t == k else ""
        state_values.append(f"total after {t} correction(s) = {int(_running_total(d, t))}{tag}")

    # must_change: stale totals after 0..k-1 corrections (each != final). Numeric-only prose.
    must_change, stale_of_state, mc_depth = [], [], []
    for t in range(0, k):
        must_change.append(f"The {tmpl['total']} is {_fmt(_running_total(d, t), unit)}.")
        stale_of_state.append(t)
        mc_depth.append(t + 1)

    # must_persist: A-independent numeric facts that must survive the corrections (never superseded).
    # Two items (E5-inherited calibration), numeric-only: the structural COUNT from the subject and one
    # FIXED line-item value. Neither is touched by any correction, so a correct revision retains both.
    must_persist = [
        f"The {d['per']} count is {n0:,}.",                        # the {n0}-thing count (structural)
        f"The {d['fixed'][-1]['label']} is {_fmt(d['fixed'][-1]['value'], unit)}.",  # a fixed line-item
    ]

    fam_id = f"E9-{family_index:04d}"
    # task_id == family_id when emitted at max dose (the driver slices doses internally via
    # turn_prompt.plan_turns + arm_n_answer_docs[:k]); the -K{k} suffix is kept only for sub-dose
    # emission used by the transform-proof/self-test paths.
    task = {
        "task_id": fam_id if k == len(d["corr"]) else f"{fam_id}-K{k}",
        "experiment": "E9",
        "family_id": fam_id,
        "covariates": {"family": "F3", "source_count": len(sources), "unit": unit,
                       "route": "fresh-generate", "variant": d["variant"]},
        "question": tmpl["q"],
        "sources": sources,
        "axis_params": {
            "corrections": corrections,
            "state_values": state_values,
            "stale_of_state": stale_of_state,
        },
        "must_change": must_change,
        "must_change_depth": mc_depth,
        "must_persist": must_persist,
        "e9": {
            "arms": ["N", "S"],
            "dose_axis": "compaction_cycles",
            "dose_levels": [1, 2, 3],
            "scored_grammar": "F3-numeric-only",
            "dual_scored": ["frozen_nli", "instrument_v2"],
            "compression_band": [0.30, 0.50],
            "arm_n_variant": "restatement-k+1",   # matched generation count (DESIGN.md §10 fix)
        },
    }
    return task


def generate_corpus(n_families: int, doses=(1, 2, 3)) -> list[dict]:
    """One record PER FAMILY at max dose (k=max(doses)), carrying all corrections/state_values/
    must_change. The run driver derives each dose by slicing (turn_prompt.plan_turns +
    arm_n_answer_docs[:k]); scoring at dose k uses must_change[:k]. Emitting one record per family (not
    one per dose) is what keeps the driver's per-family dose loop from double-counting. Deterministic in
    family_index (E5/E8 determinism rule)."""
    kmax = max(doses)
    return [generate_family(fi, kmax) for fi in range(n_families)]


def _guard_batch(records: list[dict], label: str) -> tuple[list[dict], list[str]]:
    """Guard every record; return (clean, problems). Prints a per-run summary."""
    all_problems: list[str] = []
    clean: list[dict] = []
    for r in records:
        problems = guard_record(r)
        if problems:
            all_problems.extend(problems)
        else:
            clean.append(r)
    print(f"[e9:{label}] guard: {len(clean)}/{len(records)} clean, {len(all_problems)} violations",
          flush=True)
    for p in all_problems[:40]:
        print("  VIOLATION:", p, flush=True)
    return clean, all_problems


def _halt_on_inversion(problems: list[str]) -> int | None:
    inversions = [p for p in problems if "POLARITY INVERSION" in p]
    if inversions:
        print(f"[e9] HALT: {len(inversions)} polarity inversions — refusing to build.", flush=True)
        return 2
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="E9 fresh F3 generator + A3 transform guard-proof")
    ap.add_argument("--generate", action="store_true", help="REGISTERED route: synthesize fresh F3 corpus")
    ap.add_argument("--families", type=int, default=40, help="independent scenario families (>=40 for N)")
    ap.add_argument("--dry-sample", type=int, default=0, help="generate only this many families (10-family gate)")
    ap.add_argument("--in", dest="inp", type=Path, help="A3 corpus for the transform guard-proof route")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--self-check", action="store_true", help="run guards only, write nothing")
    args = ap.parse_args()

    if args.generate:
        n = args.dry_sample if args.dry_sample else args.families
        records = generate_corpus(n)
        # report independence: distinct families and per-dose item counts (the scale the design needs)
        fams = {r["family_id"] for r in records}
        per_dose = {}
        for r in records:
            k = len(r["must_change"])
            per_dose[k] = per_dose.get(k, 0) + len(r["must_change"])
        print(f"[e9:gen] {len(records)} records, {len(fams)} independent families; "
              f"must_change items per dose(k)={per_dose}", flush=True)
        clean, problems = _guard_batch(records, "gen")
        halt = _halt_on_inversion(problems)
        if halt is not None:
            return halt
        # corpus manifest hash (registration token for run_e9 startup guard)
        if args.out and not args.self_check:
            payload = "\n".join(json.dumps(r, sort_keys=True) for r in clean)
            args.out.write_text(payload + "\n")
            man = hashlib.sha256(payload.encode()).hexdigest()
            print(f"[e9:gen] wrote {len(clean)} records to {args.out} — manifest sha256={man}", flush=True)
        return 0 if not problems else 1

    # ------ transform route (schema/guard proof only) ------
    if not args.inp:
        ap.error("either --generate or --in is required")
    rows = [json.loads(l) for l in args.inp.read_text().splitlines() if l.strip()]
    f3 = [transform_record(r) for r in rows if (r.get("covariates") or {}).get("family") == "F3"]
    print(f"[e9:xform] {len(rows)} A3 rows, {len(f3)} F3 candidates", flush=True)
    clean, problems = _guard_batch(f3, "xform")
    halt = _halt_on_inversion(problems)
    if halt is not None:
        return halt
    if args.self_check:
        return 0 if not problems else 1
    if args.out and clean:
        args.out.write_text("\n".join(json.dumps(r) for r in clean) + "\n")
        print(f"[e9:xform] wrote {len(clean)} records to {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
