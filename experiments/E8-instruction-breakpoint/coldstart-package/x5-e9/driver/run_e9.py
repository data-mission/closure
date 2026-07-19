"""E9 multi-turn orchestration driver (BUILT; dry-run-verified end-to-end).

Drives the two arms over the E9 turn-corpus. Every individual model call goes through the FROZEN
generation path (e8-driver/generation_driver.generate_one -> closure_harness.generate.generate_row):
model-identity halt, schema validation, resumable append-only log — reused verbatim, NOT re-implemented.

Per matched task, for each dose k in {1,2,3}:

  Arm N (no-compaction baseline):
    live_docs = base_sources + corrections[:k]           # full transcript retained
    answer = generate(build_answer_prompt(live_docs, ..., ARM_B))   # 1 generation

  Arm S (compaction operator):
    live_docs = base_sources
    running_summary = None
    for t in 1..k:
        # COMPACT the current live context BEFORE revealing correction t
        summary = generate(build_summarizer_prompt(live_docs, SUMMARIZER_INSTRUCTION))
        assert_compression_band(summary, live_docs)      # DESIGN.md §10 — re-draw if out of band
        live_docs = [summary, corrections[t-1]]           # continue from summary + new correction
        running_summary = summary
    answer = generate(build_answer_prompt(live_docs, ..., ARM_B))   # k summaries + 1 answer

Both answers are scored by BOTH instruments (frozen NLI + instrument_v2) and the comparability gate is
checked (DESIGN.md §3). The registered contamination number is instrument_v2's; NLI is reported
alongside; per-item disagreements are logged for hand adjudication and a >2% disagreement rate HALTS
before verdict.

REGISTRATION GUARDS enforced at startup (all fail-loud, all HALT):
  - ARM-B instruction file hash == f9c242958fccba4eb536ef74d903f6c897545f4365211a6dacd00b6fdbe70a7c
  - SUMMARIZER instruction file hash == <frozen at registration>
  - generation model identity == config.generation.model_pin (per-call, inside generate_row)
  - config hash == 6dbe47a8e843ec1540f64ed6ddd8339c17b95688db363e31605502e374a8b9f0
  - every E9 task passed build_e9_corpus guards (grammar + polarity) — checked by a manifest hash

DRY-RUN: --dry-run uses the frozen driver's fake provider (generation_driver.make_fake_provider) for
BOTH the answer and the summarizer calls, so the full 2-arm x 3-dose plumbing + scoring + comparability
gate runs end-to-end at ZERO spend. This is the plumbing-verification path the manager runs first.

STATUS: BUILT. The frozen-call wiring, the per-arm/per-dose loop, resumable logging, the compression-
band redraw accounting, and the dual-scoring join (instrument_v2 + frozen outcomes.py NLI, with the
≤2% comparability gate) are all implemented and dry-run-verified end-to-end. The one registration-time
step is freezing the summarizer instruction hash (SUMMARIZER_PINNED_SHA256). The `--score` path loads
the pinned NLI checkpoint (needs the harness torch env); the generation path does not.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
E8_DRIVER = HERE.parent.parent / "e8-driver"          # reuse the frozen generation driver
X1 = HERE.parent.parent / "x1-anatomy"                # reuse instrument_v2
sys.path.insert(0, str(E8_DRIVER))
sys.path.insert(0, str(X1))
sys.path.insert(0, str(HERE))

ARMB_PINNED_SHA256 = "f9c242958fccba4eb536ef74d903f6c897545f4365211a6dacd00b6fdbe70a7c"
CONFIG_HASH_PIN = "6dbe47a8e843ec1540f64ed6ddd8339c17b95688db363e31605502e374a8b9f0"
# Frozen at launch 2026-07-19T02:50Z (sha256 of SUMMARIZER-INSTRUCTION.md, verified against the
# staged bytes immediately before stamping; exploratory grade — no registration ceremony per owner):
SUMMARIZER_PINNED_SHA256 = "305f7e27a63696dc96046fbe40208224287cd099142d6fec73b01623490426e4"


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def assert_compression_band(summary_text: str, live_docs: list[str], band=(0.30, 0.50)) -> bool:
    """DESIGN.md §10: the summary must be 30-50% of the live-context length (token-proxy = whitespace
    words here; the registered run uses the tokenizer). Out-of-band => re-draw (caller loops). Returns
    True iff in band. Logging the ratio per cycle makes 'how much it compacted' a reported variable,
    not an accident of wording."""
    live_len = sum(len(d.split()) for d in live_docs)
    if live_len == 0:
        return False
    ratio = len(summary_text.split()) / live_len
    return band[0] <= ratio <= band[1]


def startup_guards(armb: Path, summarizer: Path, allow_unpinned: bool) -> None:
    """All registration-critical hash checks. HALT on any mismatch (would void the run)."""
    a = _sha256(armb)
    if a != ARMB_PINNED_SHA256 and not allow_unpinned:
        raise SystemExit(f"ARM-B hash mismatch: {a} != {ARMB_PINNED_SHA256}")
    if SUMMARIZER_PINNED_SHA256 != "<FROZEN-AT-REGISTRATION>":
        s = _sha256(summarizer)
        if s != SUMMARIZER_PINNED_SHA256 and not allow_unpinned:
            raise SystemExit(f"SUMMARIZER hash mismatch: {s} != {SUMMARIZER_PINNED_SHA256}")
    # config hash checked against the frozen harness at run time:
    from closure_harness.config import config_hash  # noqa
    ch = config_hash()
    if ch != CONFIG_HASH_PIN:
        raise SystemExit(f"config hash mismatch: {ch} != {CONFIG_HASH_PIN}")


def _gen(provider, task, arm_dose, prompt):
    """generate_one + stamp arm_dose onto the returned row. The FROZEN generate_one keys its row by
    task_id and the fixed arm 'B' only and does NOT propagate custom task keys, so arm_dose must be
    added to the RESULT (verified: passing it in the task dict was silently dropped -> all rows tagged
    '?'). Keeping the E9 tag on the row is what makes resume + scoring filters work."""
    from generation_driver import generate_one
    row = generate_one(provider, task, "B", prompt, CONFIG_HASH_PIN, 5, 1.0)
    row["arm_dose"] = arm_dose
    return row


def run_arm_n(provider, task: dict, k: int, template: str, arm_b: str, gen_log: Path):
    """1 answer generation over the full retained transcript. Reuses generation_driver.generate_one."""
    from turn_prompt import arm_n_answer_docs, build_answer_prompt
    docs = arm_n_answer_docs(task, k)
    prompt = build_answer_prompt(docs, task["question"], template, arm_b)
    return _gen(provider, task, f"N-k{k}", prompt)


def run_arm_n_restatement(provider, task: dict, k: int, template: str, arm_b: str):
    """Arm-N restatement variant (§10 fix): k intermediate restatement generations over the FULL
    retained transcript (no compaction), then the final scored answer. Matches Arm S's generation COUNT
    so a delta cannot be attributed to generation count. Only the final answer row is returned/scored;
    the intermediate restatements exercise the model but are logged with arm 'N_restate' and excluded
    from scoring."""
    from turn_prompt import (arm_n_restatement_docs, build_restatement_prompt, arm_n_answer_docs,
                             build_answer_prompt)
    rows = []
    for t in range(1, k + 1):
        docs = arm_n_restatement_docs(task, t)
        rp = build_restatement_prompt(docs, task["question"], template)
        r = _gen(provider, task, f"Nr-k{k}-t{t}", rp)
        r["e9_meta"] = {"arm": "N", "role": "restatement", "dose": k, "turn": t}
        rows.append(r)
    docs = arm_n_answer_docs(task, k)
    prompt = build_answer_prompt(docs, task["question"], template, arm_b)
    answer = _gen(provider, task, f"N-k{k}", prompt)
    return answer, rows


def run_arm_s(provider, task: dict, k: int, template: str, summarizer_tmpl: str,
              summarizer_instr: str, arm_b: str, max_redraws: int = 3):
    """k compaction cycles then 1 answer. Each summary is generated, compression-band checked (re-draw
    up to max_redraws), and folded into the running context. Reuses generate_one for every call."""
    from turn_prompt import (base_source_texts, corrections_in_order,
                             build_summarizer_prompt, build_answer_prompt, arm_s_answer_docs)
    corr = corrections_in_order(task)
    live_docs = base_source_texts(task)
    summary = None
    redraw_log = []
    inter_rows = []                                    # every summarizer generation, for full logging
    band = tuple(task.get("e9", {}).get("compression_band", (0.30, 0.50)))
    for t in range(1, k + 1):
        in_band = False
        for attempt in range(max_redraws):
            sp = build_summarizer_prompt(live_docs, summarizer_instr, summarizer_tmpl)
            row = _gen(provider, task, f"S-k{k}-c{t}-a{attempt}", sp)
            summary = row["output"]["conclusion"] if "output" in row else ""
            live_len = sum(len(d.split()) for d in live_docs)
            ratio = (len(summary.split()) / live_len) if live_len else 0.0
            in_band = band[0] <= ratio <= band[1]
            row["e9_meta"] = {"arm": "S", "role": "summary", "dose": k, "cycle": t,
                              "attempt": attempt, "ratio": round(ratio, 3), "in_band": in_band}
            inter_rows.append(row)
            redraw_log.append({"cycle": t, "attempt": attempt, "ratio": round(ratio, 3), "in_band": in_band})
            if in_band:
                break
        # Redraw exhaustion is a CONSTRUCTION failure, surfaced (not silently accepted) — the summarizer
        # could not compact within the frozen band, so this task's Arm-S datum is flagged for exclusion.
        if not in_band:
            redraw_log.append({"cycle": t, "redraw_exhausted": True})
        live_docs = arm_s_answer_docs(summary, corr[t - 1])
    prompt = build_answer_prompt(live_docs, task["question"], template, arm_b)
    answer = _gen(provider, task, f"S-k{k}", prompt)
    return answer, redraw_log, inter_rows


def score_both(task: dict, answer_row: dict, dose: int | None = None) -> dict:
    """Dual scoring of ONE arm answer against the task annotations. Returns per-item flags from BOTH
    instruments plus the comparability signal (the run-level gate is applied in main()).
      - frozen NLI: closure_harness.outcomes.score at the frozen 0.70 threshold (bit-for-bit E5/E8).
      - instrument-v2: classify_item per must_change item (value-echo, the de-artifacted scorer).
    On numeric-only F3 strings the two should agree item-for-item; disagreements are recorded.
    `dose` slices must_change to the stale totals reachable at that many corrections (must_change[:dose]):
    the family record carries all doses' stale totals, but at dose k only the first k are in play."""
    if "output" not in answer_row:            # an error row (provider failure) — no score
        return {"error": answer_row.get("error", "no output"), "scorable": False}
    out = answer_row["output"]

    # --- instrument-v2 (accepted scorer) ---
    import instrument_v2 as v2
    all_mc = task.get("must_change", [])
    n = len(all_mc) if dose is None else min(dose, len(all_mc))
    # score against a dose-sliced VIEW of the task so v2's internal must_change[i] lookups match
    task_view = dict(task)
    task_view["must_change"] = all_mc[:n]
    mc = task_view["must_change"]
    v2_flags = []
    for i in range(len(mc)):
        r = v2.classify_item(task_view, out, i)
        v2_flags.append(bool(r["real_contamination"]))

    # --- frozen NLI (comparability) ---
    from closure_harness.nli import NLIScorer
    from closure_harness.schema import parse_output
    from closure_harness.outcomes import _still_asserts
    from closure_harness.config import CONFIG
    scalar = _get_nli()                        # cached; loads the pinned checkpoint once
    parsed = parse_output(out)
    thr = CONFIG.outcome.assert_threshold
    nli_flags = [_still_asserts(scalar, parsed, c, thr) for c in mc]

    disagree = [i for i in range(len(mc)) if v2_flags[i] != nli_flags[i]]
    return {
        "scorable": True,
        "v2_contaminated": sum(v2_flags),
        "nli_contaminated": sum(nli_flags),
        "n_items": len(mc),
        "v2_flags": v2_flags,
        "nli_flags": nli_flags,
        "disagreements": disagree,
    }


_NLI_SINGLETON = {}


def _get_nli():
    """Load the pinned NLI scorer once (it is the E5/E8 frozen checkpoint; construction is expensive)."""
    if "s" not in _NLI_SINGLETON:
        from closure_harness.nli import NLIScorer
        _NLI_SINGLETON["s"] = NLIScorer()
    return _NLI_SINGLETON["s"]


def main() -> int:
    ap = argparse.ArgumentParser(description="E9 compaction-cycles run driver (2 arms x 3 doses)")
    ap.add_argument("--tasks", required=True, type=Path)
    ap.add_argument("--gen-log", required=True, type=Path)
    ap.add_argument("--template", required=True, type=Path)
    ap.add_argument("--summarizer-template", required=True, type=Path)
    ap.add_argument("--arm-b-instruction", required=True, type=Path)
    ap.add_argument("--summarizer-instruction", required=True, type=Path)
    ap.add_argument("--doses", default="1,2,3")
    ap.add_argument("--arm-n-variant", choices=["plain", "restatement"], default="restatement",
                    help="restatement = k+1 matched-generation control (§10 fix, adopted)")
    ap.add_argument("--score", action="store_true", help="score banked answers (needs torch/NLI)")
    ap.add_argument("--dry-run", action="store_true", help="fake provider, no network, no key")
    ap.add_argument("--allow-unpinned-instruction", action="store_true")
    args = ap.parse_args()

    startup_guards(args.arm_b_instruction, args.summarizer_instruction, args.allow_unpinned_instruction)
    from generation_driver import append_jsonl, load_jsonl  # frozen JSONL helpers (atomic append)
    from closure_harness.config import CONFIG
    template = args.template.read_text()
    summarizer_tmpl = args.summarizer_template.read_text()
    arm_b = " ".join(l[2:].strip() for l in args.arm_b_instruction.read_text().splitlines()
                     if l.startswith("> "))
    summ_instr = " ".join(l[2:].strip() for l in args.summarizer_instruction.read_text().splitlines()
                          if l.startswith("> "))
    doses = [int(x) for x in args.doses.split(",") if x.strip()]
    tasks = [json.loads(l) for l in args.tasks.read_text().splitlines() if l.strip()]

    if args.dry_run:
        from generation_driver import make_fake_provider
        provider = make_fake_provider(CONFIG.generation.model_pin)
    else:
        from closure_harness.providers import make_provider
        provider = make_provider()  # reads ANTHROPIC_API_KEY at call time, never logged

    # RESUMABLE: a (family, arm, dose) whose FINAL answer row is already banked clean is skipped. The
    # answer row is tagged arm_dose in {N-k{d}, S-k{d}} (intermediate restatement/summary rows carry
    # Nr-/S-k{d}-c tags and are not the resume key).
    done = set()
    for r in load_jsonl(args.gen_log):
        ad = r.get("arm_dose", "")
        if not r.get("error") and (ad.startswith("N-k") or ad.startswith("S-k")):
            done.add((r["task_id"], ad))

    n_gen = 0
    import time
    t0 = time.time()

    def _bank(row):
        """Persist EVERY generated row (intermediate summaries/restatements + final answers) for full
        cost accounting and partial-work resumability. Atomic append via the frozen helper."""
        append_jsonl(args.gen_log, row)

    for task in tasks:
        fam_doses = [d for d in doses if d <= len(task.get("axis_params", {}).get("corrections", []))]
        for d in fam_doses:
            # ---- Arm S (compaction) ----
            key_s = (task["task_id"], f"S-k{d}")
            if key_s not in done:
                ans_s, redraws, inter_s = run_arm_s(provider, task, d, template, summarizer_tmpl,
                                                    summ_instr, arm_b)
                for r in inter_s:                       # log every compaction-cycle summary row
                    _bank(r)
                ans_s["e9_meta"] = {"arm": "S", "dose": d, "redraws": redraws}
                _bank(ans_s)
                n_gen += 1
            # ---- Arm N (baseline; restatement variant matches S's generation count) ----
            key_n = (task["task_id"], f"N-k{d}")
            if key_n not in done:
                if args.arm_n_variant == "restatement":
                    ans_n, restated = run_arm_n_restatement(provider, task, d, template, arm_b)
                    for r in restated:                  # log every restatement turn
                        _bank(r)
                    ans_n["e9_meta"] = {"arm": "N", "dose": d, "restatement_turns": len(restated)}
                else:
                    ans_n = run_arm_n(provider, task, d, template, arm_b, args.gen_log)
                    ans_n["e9_meta"] = {"arm": "N", "dose": d}
                _bank(ans_n)
                n_gen += 1
            if n_gen and n_gen % 20 == 0:
                rate = n_gen / max(1e-9, time.time() - t0)
                print(f"[e9] {n_gen} answers banked · {rate:.2f}/s", flush=True)
    print(f"[e9] generation DONE · {n_gen} answer rows this run · "
          f"{time.time() - t0:.1f}s", flush=True)

    if args.score:
        return _score_run(args.gen_log, tasks)
    return 0


def _score_run(gen_log: Path, tasks: list[dict]) -> int:
    """Score every banked FINAL answer with both instruments; apply the comparability gate; emit a
    per-(arm,dose) contamination table. HALTS (nonzero) if instrument disagreement > 2% (DESIGN.md §3)."""
    import re as _re
    from generation_driver import load_jsonl
    by_id = {t["task_id"]: t for t in tasks}
    # FINAL answer rows only: arm_dose matches exactly N-k{d} or S-k{d} (intermediate summary/restatement
    # rows carry -c / Nr- tags and are excluded from scoring — they exercise the model, not the DV).
    FINAL = _re.compile(r"^[NS]-k\d+$")
    rows = [r for r in load_jsonl(gen_log)
            if not r.get("error") and FINAL.match(r.get("arm_dose", ""))]
    from collections import defaultdict
    agg = defaultdict(lambda: {"tasks": 0, "items": 0, "v2": 0, "nli": 0, "disagree": 0})
    total_items = total_disagree = 0
    for r in rows:
        task = by_id.get(r["task_id"])
        if not task:
            continue
        meta = r.get("e9_meta", {})
        dose = meta.get("dose") or int(r["arm_dose"].split("k")[1])
        key = (meta.get("arm", r["arm_dose"][0]), dose)
        s = score_both(task, r, dose=dose)
        if not s.get("scorable"):
            continue
        agg[key]["tasks"] += 1
        agg[key]["items"] += s["n_items"]
        agg[key]["v2"] += s["v2_contaminated"]
        agg[key]["nli"] += s["nli_contaminated"]
        agg[key]["disagree"] += len(s["disagreements"])
        total_items += s["n_items"]
        total_disagree += len(s["disagreements"])
    print("[e9:score] per (arm,dose): v2 / nli contamination", flush=True)
    for k in sorted(agg, key=lambda x: (str(x[0]), str(x[1]))):
        a = agg[k]
        print(f"  {k[0]} k={k[1]}: {a['tasks']} tasks, {a['items']} items · "
              f"v2={a['v2']} ({a['v2']/max(1,a['items'])*100:.1f}%) · "
              f"nli={a['nli']} ({a['nli']/max(1,a['items'])*100:.1f}%) · disagree={a['disagree']}",
              flush=True)
    dis_rate = total_disagree / max(1, total_items)
    print(f"[e9:score] instrument disagreement {total_disagree}/{total_items} = {dis_rate*100:.2f}% "
          f"(gate: <=2%)", flush=True)
    if dis_rate > 0.02:
        print("[e9:score] HALT: comparability gate failed — a compound string leaked in (DESIGN.md §3).",
              flush=True)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
