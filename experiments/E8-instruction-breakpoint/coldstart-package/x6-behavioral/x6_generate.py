"""X6 multi-turn FORM-WRITE generation harness (X6-PROTOTYPE-SPEC §E step 3).

Drives a scripted multi-turn conversation per task spec (x6-corpus.jsonl):
  turn 1  : establish the rule (+ the scoped exception, SCOPED arm only), agent acknowledges.
  turns 2..N+1 : N neutral intervening sub-tasks (dose = N), agent answers each (consumes context).
  final turn   : GUARD G — the exception grant is RE-PRESENTED verbatim, then the worksheet is posed;
                 the agent writes a typed value per scored case via a single structured reply.
Captures the emitted field-writes, evaluates the oracles AT CAPTURE (a_correct_fired/a_wrong_fired),
and appends one result row (aggregator shape) to the results JSONL.

MODEL: pinned via the frozen CONFIG.generation.model_pin + identity guard (a spoofed model HALTS).
KEY: read from ANTHROPIC_API_KEY inside the provider at call time; never logged.
DRY-RUN: --dry-run uses a deterministic FAKE agent (no network, no key) that plays a fixed policy, so
the full build->generate->aggregate plumbing is verifiable with NO GENERATION before any real generation.

This is multi-turn, so it does NOT reuse the frozen single-shot generate_row (that is the NLI corpus
path). It uses the Anthropic messages API directly with the pinned model + identity halt. Frozen files
untouched.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

from x6_normalize import canonical_eq, canonical_scalar, Unparseable
from x6_turnbank import NEUTRAL_TURNS

TURN_BANK = {t["id"]: t for t in NEUTRAL_TURNS}
FIELD_RE = re.compile(r"([A-Za-z0-9_\-]+)\s*[:=]\s*\$?([\d,]+(?:\.\d+)?)")


# --------------------------------------------------------------------------- worksheet prompt
def build_final_worksheet(spec: dict) -> str:
    lines = []
    if spec["arm"] == "SCOPED":
        exc = spec["exception"]
        lines.append(f"REMINDER (still in effect): {exc['grant_text']}")  # GUARD G: verbatim re-present
    else:
        lines.append(f"REMINDER (still in effect): {spec['blanket_requirement']}")
    lines.append(f"Standing rule: {spec['rule_text']}")
    lines.append("Now fill the worksheet. For EACH case id below, reply on its own line in the exact "
                 "form `<case_id>: <number>` (digits only, no words):")
    for c in spec["scored_cases"]:
        lines.append(f"  {c['case_id']}: ?")
    return "\n".join(lines)


def parse_worksheet(text: str) -> dict:
    """Extract {case_id: emitted_value_str} from the agent's final reply."""
    out = {}
    for m in FIELD_RE.finditer(text or ""):
        out[m.group(1)] = m.group(2).replace(",", "")
    return out


# --------------------------------------------------------------------------- fake agent (dry-run)
def fake_agent_reply(spec: dict, turn_kind: str, turn_payload) -> str:
    """Deterministic no-network agent. Policy (chosen to exercise all cells across the corpus):
      - neutral turns: echo a fixed token.
      - worksheet: apply the CORRECT value to every case EXCEPT it over-generalizes on RULE cases
        for dose T3 (to produce a nonzero, dose-rising over-rate in the dry-run so the pipeline's
        numbers are visibly non-trivial). This is a PLUMBING fixture, not a model claim."""
    if turn_kind == "neutral":
        return "done: ok"
    # worksheet
    lines = []
    dose = spec["dose_level"]
    for c in spec["scored_cases"]:
        cls = c["cls"]
        emitted = c["A_correct"]  # default correct
        if spec["arm"] == "SCOPED" and cls == "RULE" and dose == 3:
            emitted = str(c["A_wrong"])  # over-generalize on RULE at top dose (fixture)
        lines.append(f"{c['case_id']}: {emitted}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- real provider (multi-turn)
def make_real_agent(model_pin: str):
    import anthropic
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    def agent(messages: list) -> str:
        resp = client.messages.create(model=model_pin, max_tokens=1024, messages=messages)
        reported = getattr(resp, "model", "") or ""
        # identity halt (frozen discipline): a provider-returned model mismatch stops the run.
        if model_pin.split("-")[:3] != reported.split("-")[:3] and reported and model_pin not in reported:
            raise RuntimeError(f"MODEL IDENTITY HALT: pinned {model_pin}, provider returned {reported}")
        return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")

    return agent


# --------------------------------------------------------------------------- run one task
def run_task(spec: dict, agent, dry_run: bool) -> dict:
    messages = []
    # turn 1: rule (+exception)
    if spec["arm"] == "SCOPED":
        t1 = (f"You are processing insurance/claims cases. Standing rule: {spec['rule_text']}\n"
              f"Case-specific exception now in effect: {spec['exception']['grant_text']}\n"
              "Acknowledge you will apply the exception ONLY to its named case and the standing rule to all others.")
    else:
        t1 = (f"You are processing insurance/claims cases. Standing rule: {spec['rule_text']}\n"
              f"{spec['blanket_requirement']}\nAcknowledge.")
    messages.append({"role": "user", "content": t1})
    ack = fake_agent_reply(spec, "neutral", None) if dry_run else agent(messages)
    messages.append({"role": "assistant", "content": ack})
    # intervening neutral turns
    for tid in spec["intervening_turn_ids"]:
        payload = TURN_BANK[tid]["prompt"]
        messages.append({"role": "user", "content": payload})
        r = fake_agent_reply(spec, "neutral", payload) if dry_run else agent(messages)
        messages.append({"role": "assistant", "content": r})
    # final worksheet turn (guard G re-present inside)
    ws = build_final_worksheet(spec)
    messages.append({"role": "user", "content": ws})
    final = fake_agent_reply(spec, "worksheet", None) if dry_run else agent(messages)

    emitted_map = parse_worksheet(final)
    # positive control (guard B): does A_correct fire on the authored unusual-but-valid form?
    pc = spec["positive_control"]
    pc_fired = canonical_eq(pc["form"], pc["target"])

    scored = []
    for c in spec["scored_cases"]:
        em = emitted_map.get(c["case_id"])
        ac = canonical_eq(em, c["A_correct"]) if em is not None else False
        aw = (False if c["A_wrong"] is None or em is None
              else canonical_eq(em, str(c["A_wrong"])))
        scored.append({"case_id": c["case_id"], "cls": c["cls"],
                       "A_correct": c["A_correct"], "A_wrong": c["A_wrong"],
                       "emitted": em, "a_correct_fired": ac, "a_wrong_fired": aw})
    return {
        "task_id": spec["task_id"], "family_id": spec["family_id"], "arm": spec["arm"],
        "dose_level": spec["dose_level"],
        "scored_cases": scored,
        "positive_control": {"target": pc["target"], "emitted": pc["form"], "fired": pc_fired},
        "provenance": {"dry_run": dry_run, "model_pin": None if dry_run else spec.get("_model_pin"),
                       "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--dry-run", action="store_true", help="fake agent, no network, no key")
    ap.add_argument("--limit", type=int, default=None, help="only first N specs (smoke)")
    ap.add_argument("--model-pin", default=None, help="override model pin (else frozen CONFIG)")
    args = ap.parse_args()

    specs = [json.loads(l) for l in open(args.corpus) if l.strip()]
    if args.limit:
        specs = specs[:args.limit]

    agent = None
    model_pin = args.model_pin
    if not args.dry_run:
        if model_pin is None:
            from closure_harness.config import CONFIG
            model_pin = CONFIG.generation.model_pin
        agent = make_real_agent(model_pin)

    n = 0
    with open(args.out, "w") as f:
        for spec in specs:
            spec["_model_pin"] = model_pin
            row = run_task(spec, agent, args.dry_run)
            f.write(json.dumps(row) + "\n")
            n += 1
    print(json.dumps({"generated": n, "out": str(args.out), "dry_run": args.dry_run,
                      "model_pin": model_pin}))


if __name__ == "__main__":
    main()
