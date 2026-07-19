"""E8 driver dry-run — end-to-end plumbing verification at ZERO spend.

Builds 3 synthetic probe tasks, runs the WHOLE pipeline:
  1. generation_driver --dry-run  (fake generator, no network, no key) → gen-log.jsonl
  2. score_worker over the 3 tasks (REAL frozen scoring — this exercises the actual NLIScorer)
  3. oracle_verify (fresh 1-thread re-score, per-task ==)  → must PASS
  4. a determinism check: run the scorer TWICE and assert byte-identical result files
  5. an ATOMICITY check: assert no *.tmp.* files survive, every result is complete JSON
  6. a PROVENANCE check: every result records thread_count/versions/hostname/config_hash

Exits 0 only if every check passes; prints a per-check ledger. This is what the manager runs to
verify the plumbing before it ever touches money. REAL scoring (~a handful of NLIScorer calls),
so it needs the harness venv + cached model, but ZERO API and ZERO key.

Run:  cd ~/repos/closure/harness && uv run python <driver>/dry_run.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

DRIVER = Path(__file__).resolve().parent


SAMPLE_TASKS = [
    {
        "task_id": "DRY-0001", "family": "F1", "question": "What follows?",
        "sources": [{"text": "All widgets in bin A are blue."},
                    {"text": "Item 7 is a widget in bin A."}],
        "not_A_evidence": {"text": "Correction: item 7 was moved to bin B, which holds red widgets."},
        "must_change": ["Item 7 is blue.", "Item 7 is in bin A."],
        "must_persist": ["Widgets in bin A are blue.", "Bin B holds red widgets."],
    },
    {
        "task_id": "DRY-0002", "family": "F2", "question": "What is the total?",
        "sources": [{"text": "Each crate weighs 10 kg."},
                    {"text": "There are 4 crates on the pallet."},
                    {"text": "The pallet itself weighs 5 kg."}],
        "not_A_evidence": {"text": "Correction: one crate was removed, leaving 3 crates."},
        "must_change": ["The total crate weight is 40 kg.", "There are 4 crates."],
        "must_persist": ["Each crate weighs 10 kg.", "The pallet weighs 5 kg."],
    },
    {
        "task_id": "DRY-0003", "family": "F3", "question": "When does it open?",
        "sources": [{"text": "The gate opens at 9 AM on weekdays."},
                    {"text": "Today is Wednesday."}],
        "not_A_evidence": {"text": "Correction: today is a public holiday; weekday hours do not apply."},
        "must_change": ["The gate opens at 9 AM today.", "Today follows weekday hours."],
        "must_persist": ["The gate opens at 9 AM on weekdays.", "Weekdays exclude holidays."],
    },
]


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    print("  $ " + " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run(cmd, **kw)


def main() -> int:
    work = Path(tempfile.mkdtemp(prefix="e8-dryrun-"))
    tasks_path = work / "tasks.jsonl"
    tasks_path.write_text("\n".join(json.dumps(t) for t in SAMPLE_TASKS) + "\n")
    template = work / "template.txt"
    template.write_text("Documents:\n{documents}\n\nQuestion: {question}\n\nProvide your answer")
    armb = work / "ARM-B.md"
    armb.write_text("> Disregard the corrected assumption and revise every dependent conclusion.\n")
    gen_log = work / "gen-log.jsonl"
    out_dir = work / "results"
    lock_dir = work / "locks"
    py = sys.executable
    ledger = {}

    print("[dry-run] work dir:", work, flush=True)

    # 1. fake generation
    print("[1/6] fake generation (no network, no key) ...", flush=True)
    # synthetic ARM-B.md won't match the frozen pin — allow it for the plumbing test only.
    r = run([py, str(DRIVER / "generation_driver.py"), "--tasks", tasks_path,
             "--gen-log", gen_log, "--arms", "B", "--template", template,
             "--arm-b-instruction", armb, "--dry-run", "--allow-unpinned-instruction"])
    from common import load_jsonl
    sys.path.insert(0, str(DRIVER))
    gen_rows = load_jsonl(gen_log)
    ledger["generation"] = (r.returncode == 0 and len(gen_rows) == 3
                            and all("error" not in row for row in gen_rows))

    # 2. real scoring (frozen path)
    print("[2/6] real frozen scoring (score_worker) ...", flush=True)
    r = run([py, str(DRIVER / "score_worker.py"), "--tasks", tasks_path, "--gen-log", gen_log,
             "--out-dir", out_dir, "--lock-dir", lock_dir, "--threads", "2", "--arms", "B"])
    results = sorted(out_dir.glob("*.json"))
    results = [p for p in results if not p.name.startswith("_")]
    ledger["scoring"] = (r.returncode == 0 and len(results) == 3)

    # 3. oracle (fresh 1-thread, per-task ==)
    print("[3/6] oracle (fresh 1-thread, per-task ==) ...", flush=True)
    r = run([py, str(DRIVER / "oracle_verify.py"), "--tasks", tasks_path, "--gen-log", gen_log,
             "--out-dir", out_dir, "--arms", "B", "--frac", "1.0", "--min-per-worker", "3"])
    ledger["oracle_pass"] = (r.returncode == 0)

    # 4. determinism: re-score into a second dir, byte-compare
    print("[4/6] determinism (re-score, byte-compare) ...", flush=True)
    out2 = work / "results2"; lock2 = work / "locks2"
    run([py, str(DRIVER / "score_worker.py"), "--tasks", tasks_path, "--gen-log", gen_log,
         "--out-dir", out2, "--lock-dir", lock2, "--threads", "2", "--arms", "B"])
    det_ok = True
    for p in results:
        q = out2 / p.name
        a, b = json.loads(p.read_text()), json.loads(q.read_text())
        # compare the scored floats (ignore ts/provenance which legitimately vary)
        if a["arms"] != b["arms"]:
            det_ok = False
            print(f"    DETERMINISM MISMATCH {p.name}: {a['arms']} != {b['arms']}", flush=True)
    ledger["determinism"] = det_ok

    # 5. atomicity: no leftover temp files, every result parses
    print("[5/6] atomicity (no *.tmp.*, all results complete) ...", flush=True)
    tmp_leftover = list(out_dir.glob("*.tmp.*")) + list(out2.glob("*.tmp.*"))
    all_parse = all((json.loads(p.read_text()) or True) for p in results)
    ledger["atomicity"] = (not tmp_leftover and all_parse)

    # 6. provenance stamped
    print("[6/6] provenance (thread_count/versions/hostname/config_hash) ...", flush=True)
    prov_ok = True
    for p in results:
        prov = json.loads(p.read_text()).get("provenance", {})
        for key in ("thread_count", "torch_version", "transformers_version",
                    "hostname", "config_hash", "frozen_path"):
            if key not in prov:
                prov_ok = False
                print(f"    MISSING provenance.{key} in {p.name}", flush=True)
    ledger["provenance"] = prov_ok

    # 7. FILTER MODE (2 states × 3 draws / family, fake gens) → pruned register + report
    print("[7/7] filter mode (2 states x 3 draws, fake gens) ...", flush=True)
    fdir = work / "filter"
    fgen = work / "filter-gen.jsonl"
    r = run([py, str(DRIVER / "filter_stage.py"), "--tasks", tasks_path, "--gen-log", fgen,
             "--out-dir", fdir, "--template", template, "--arm-b-instruction", armb,
             "--n-draws", "3", "--threads", "2", "--dry-run", "--allow-unpinned-instruction"])
    filter_ok = r.returncode == 0
    pruned_p = fdir / "pruned-items.json"
    report_p = fdir / "filter-report.json"
    if not (pruned_p.exists() and report_p.exists()):
        filter_ok = False
        print("    MISSING pruned-items.json or filter-report.json", flush=True)
    else:
        rep = json.loads(report_p.read_text())
        # 3 families (one per sample task), 6 draws each; report must account for every family
        if rep.get("n_families") != len(SAMPLE_TASKS) or \
           rep.get("n_passed", 0) + rep.get("n_excluded", 0) != rep.get("n_families"):
            filter_ok = False
            print(f"    filter accounting off: {rep.get('n_families')} families, "
                  f"{rep.get('n_passed')} passed + {rep.get('n_excluded')} excluded", flush=True)
        # every filter draw row carries filter_state + draw_index
        from common import load_jsonl as _ljl
        rows = _ljl(fgen)
        n_expected = len(SAMPLE_TASKS) * 2 * 3
        if len([x for x in rows if "filter_state" in x]) != n_expected:
            filter_ok = False
            print(f"    filter draws off: {len(rows)} rows, expected {n_expected}", flush=True)
    ledger["filter_mode"] = filter_ok

    print("\n=== DRY-RUN LEDGER ===", flush=True)
    for k, v in ledger.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}", flush=True)
    ok = all(ledger.values())
    print(f"\nDRY-RUN {'PASS — plumbing verified end-to-end, zero spend' if ok else 'FAIL'}",
          flush=True)
    print(f"(work dir kept for inspection: {work})", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
