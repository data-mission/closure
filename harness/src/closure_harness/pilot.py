"""A-dependency pilot runner (E5 corpus spec §5).

The pilot is the pre-registered exclusion filter for the E5 corpus. For each candidate task it
generates the model-under-test's output in two evidence states — A present (withA) and A replaced
by its ¬A correction (withNotA) — three draws each, scores every annotation with the real NLI
scorer, and applies the majority-vote flip rule: a candidate PASSES iff at least one must_change
conclusion is asserted under A and dropped under ¬A. It reuses generate.generate_row (so the
model-identity guard fires) and outcomes._still_asserts (so no new scoring logic is invented).

CLI:
    uv run python -m closure_harness.pilot --candidates <jsonl> --outdir <dir> [--limit N] [--dry-run]

Two JSONL artifacts are written under --outdir:
    pilot-log.jsonl       one line per (task_id, state, draw_index) generation (spec §5c)
    pilot-verdicts.jsonl  one PASS/EXCLUDE verdict per candidate, recomputed from the full log

The runner is resumable and idempotent: on start it reads pilot-log.jsonl, skips any
(task_id, state, draw_index) triple already present with a matching config_hash, and re-runs
stale ones (config drift invalidates prior pilot results). Verdicts are recomputed from the full
log at the end, so a partial pilot-verdicts.jsonl is always safe to overwrite.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from .config import CONFIG, config_hash
from .generate import GeneratedRow, generate_row
from .outcomes import _still_asserts
from .schema import Output

# ---------------------------------------------------------------------------
# Pilot-only constants (documented as outside the frozen config, per spec §5b).
# ---------------------------------------------------------------------------

# Number of draws per state. A pilot-only robustness knob (majority of 3 breaks a single-sample
# tie at t=0.7 without inflating the pilot budget). Spec §5b: disclosed in PROTOCOL, does NOT
# touch the frozen scoring config — it lives here, outside config.py, on purpose.
N_PILOT_DRAWS = 3

STATE_WITH_A = "withA"
STATE_WITH_NOT_A = "withNotA"
STATES = (STATE_WITH_A, STATE_WITH_NOT_A)

LOG_FILENAME = "pilot-log.jsonl"
VERDICTS_FILENAME = "pilot-verdicts.jsonl"

# ---------------------------------------------------------------------------
# Frozen prompt template (spec §5a).
#
# This is a frozen artifact: it will be disclosed VERBATIM in PROTOCOL.md so a reviewer can see
# exactly what the model under test was shown. It is deliberately minimal and neutral — numbered
# documents, then the question, then the structured-output instruction citing source indices. It
# introduces no reasoning scaffolding, no chain-of-thought hint, and no revision framing (the
# arms, not the pilot, measure revision behaviour). {documents} is the numbered source block and
# {question} is the task question; both are filled by _build_prompt.
# ---------------------------------------------------------------------------

PROMPT_TEMPLATE = """You are given a set of source documents and a question. Read the documents \
and answer the question using only the information they contain.

Documents:
{documents}

Question: {question}

Provide your answer as structured output with two fields:
- "claims": a list of atomic factual claims, each an object with "id" (an integer), "text" (the \
claim as a single sentence), and "source_ids" (a list of the document numbers, as shown above, \
that the claim draws on; use an empty list if the claim draws on no specific document).
- "conclusion": a single sentence that directly answers the question, following from the claims.
"""


def _build_prompt(sources_text: list[str], question: str) -> str:
    """Render the frozen template from a list of source texts and the question.

    Documents are numbered 0..len-1 so the indices the model cites in source_ids line up with
    the positional source indices the harness uses everywhere else.
    """
    documents = "\n".join(f"[{i}] {text}" for i, text in enumerate(sources_text))
    return PROMPT_TEMPLATE.format(documents=documents, question=question)


# ---------------------------------------------------------------------------
# Candidate record (the §2 fields the pilot consumes).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Candidate:
    task_id: str
    sources: list[str]  # ordered source texts; index == source_id
    a_source_id: int  # which source carries A (assumption_A.source_id)
    not_a_text: str  # not_A_evidence.text, substituted for the A source in withNotA
    question: str
    must_change: list[str]
    must_persist: list[str]


def parse_candidate(record: dict[str, Any]) -> Candidate:
    """Extract the §2 fields the pilot needs from one candidate JSON object.

    Only the pilot-relevant fields are read; drafting provenance, covariates, and depth tags are
    ignored here (they matter at QA/selection, not at the flip test).
    """
    sources = record["sources"]
    sources_text = [s["text"] for s in sorted(sources, key=lambda s: s["id"])]
    return Candidate(
        task_id=record["task_id"],
        sources=sources_text,
        a_source_id=record["assumption_A"]["source_id"],
        not_a_text=record["not_A_evidence"]["text"],
        question=record["question"],
        must_change=list(record["must_change"]),
        must_persist=list(record["must_persist"]),
    )


def load_candidates(path: Path, limit: int | None = None) -> list[Candidate]:
    candidates: list[Candidate] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            candidates.append(parse_candidate(json.loads(line)))
            if limit is not None and len(candidates) >= limit:
                break
    return candidates


def _state_sources(candidate: Candidate, state: str) -> list[str]:
    """Source texts for a given state.

    withA: all sources verbatim.
    withNotA: the A-carrying source's text is REPLACED by not_A_evidence.text; all other sources
    are unchanged, and the ordering/count is preserved so source indices stay stable.
    """
    if state == STATE_WITH_A:
        return list(candidate.sources)
    if state == STATE_WITH_NOT_A:
        swapped = list(candidate.sources)
        swapped[candidate.a_source_id] = candidate.not_a_text
        return swapped
    raise ValueError(f"unknown state: {state!r}")


# ---------------------------------------------------------------------------
# Generation-log records.
# ---------------------------------------------------------------------------


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _score_flags(
    scalar: Callable[..., float],
    output: Output,
    annotations: list[str],
    threshold: float,
) -> list[bool]:
    """Parallel list of _still_asserts(...) over each annotation string."""
    return [_still_asserts(scalar, output, ann, threshold) for ann in annotations]


def read_log(log_path: Path) -> list[dict[str, Any]]:
    """Read all generation-log records (skips blanks). Missing file → empty list."""
    if not log_path.exists():
        return []
    records: list[dict[str, Any]] = []
    with log_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _existing_keys(
    records: Iterable[dict[str, Any]], current_config_hash: str
) -> set[tuple[str, str, int]]:
    """Keys (task_id, state, draw_index) already logged with the CURRENT config_hash.

    A record whose config_hash differs is treated as stale (config drift invalidates it) and is
    NOT counted as done — its triple will be re-run and a fresh line appended.
    """
    done: set[tuple[str, str, int]] = set()
    for rec in records:
        if rec.get("config_hash") != current_config_hash:
            continue
        done.add((rec["task_id"], rec["state"], rec["draw_index"]))
    return done


def _append_log_line(log_path: Path, record: dict[str, Any]) -> None:
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Verdict computation from the full log (spec §5b/§5c).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Verdict:
    task_id: str
    n_flipped: int
    n_change: int
    persist_stability: float
    verdict: str  # "PASS" | "EXCLUDE"
    exclude_reason: str | None
    flagged_for_qa: bool


def _majority_true(flags: list[bool]) -> bool:
    """>= 2 of 3 (strictly, > half) is 'asserted' at the majority level."""
    return sum(1 for f in flags if f) * 2 > len(flags)


def compute_verdicts(
    records: list[dict[str, Any]],
    candidates_by_id: dict[str, Candidate],
    current_config_hash: str,
) -> list[Verdict]:
    """Recompute one verdict per candidate from the full generation log.

    Majority rule (spec §5b): using only non-error records at the current config_hash, a
    must_change item is 'asserted under A' iff asserted in >= 2/3 withA draws, and 'not asserted
    without' iff asserted in <= 1/3 withNotA draws. flipped = items asserted-under-A AND
    not-asserted-without. PASS iff |flipped| >= 1.

    persist_stability (diagnostic): fraction of must_persist items whose majority-asserted state
    is the SAME under withA and withNotA. < 1.0 flags the candidate for human QA (suspected
    A-leak) even if it PASSES on the must_change side.

    Only candidates with a complete, non-error draw set in both states are given a PASS/EXCLUDE
    verdict here; candidates missing draws (all draws errored, or not yet run) get an EXCLUDE with
    an 'insufficient draws' reason so the count stays auditable.
    """
    verdicts: list[Verdict] = []
    for task_id, candidate in candidates_by_id.items():
        # Collect per-state, non-error records at the current config hash.
        by_state: dict[str, list[dict[str, Any]]] = {s: [] for s in STATES}
        for rec in records:
            if rec.get("task_id") != task_id:
                continue
            if rec.get("config_hash") != current_config_hash:
                continue
            if rec.get("error") is not None:
                continue
            state = rec.get("state")
            if state in by_state:
                by_state[state].append(rec)

        n_change = len(candidate.must_change)
        withA = by_state[STATE_WITH_A]
        withNotA = by_state[STATE_WITH_NOT_A]

        if not withA or not withNotA:
            verdicts.append(
                Verdict(
                    task_id=task_id,
                    n_flipped=0,
                    n_change=n_change,
                    persist_stability=0.0,
                    verdict="EXCLUDE",
                    exclude_reason="insufficient draws (a state has no non-error draw)",
                    flagged_for_qa=False,
                )
            )
            continue

        # Majority per must_change item, per state.
        asserted_withA = [
            _majority_true([r["asserted_must_change"][i] for r in withA])
            for i in range(n_change)
        ]
        asserted_withNotA = [
            _majority_true([r["asserted_must_change"][i] for r in withNotA])
            for i in range(n_change)
        ]
        flipped = [
            asserted_withA[i] and not asserted_withNotA[i] for i in range(n_change)
        ]
        n_flipped = sum(1 for f in flipped if f)

        # persist_stability diagnostic (majority per must_persist item, per state).
        n_persist = len(candidate.must_persist)
        if n_persist == 0:
            persist_stability = 1.0
        else:
            persist_withA = [
                _majority_true([r["asserted_must_persist"][i] for r in withA])
                for i in range(n_persist)
            ]
            persist_withNotA = [
                _majority_true([r["asserted_must_persist"][i] for r in withNotA])
                for i in range(n_persist)
            ]
            stable = sum(
                1 for i in range(n_persist) if persist_withA[i] == persist_withNotA[i]
            )
            persist_stability = stable / n_persist

        passed = n_flipped >= 1
        verdicts.append(
            Verdict(
                task_id=task_id,
                n_flipped=n_flipped,
                n_change=n_change,
                persist_stability=persist_stability,
                verdict="PASS" if passed else "EXCLUDE",
                exclude_reason=None if passed else "no must_change item flipped",
                flagged_for_qa=persist_stability < 1.0,
            )
        )
    return verdicts


def write_verdicts(verdicts_path: Path, verdicts: list[Verdict]) -> None:
    """Overwrite the verdicts file with one JSON line per candidate (idempotent)."""
    with verdicts_path.open("w", encoding="utf-8") as fh:
        for v in verdicts:
            fh.write(
                json.dumps(
                    {
                        "task_id": v.task_id,
                        "n_flipped": v.n_flipped,
                        "n_change": v.n_change,
                        "persist_stability": v.persist_stability,
                        "verdict": v.verdict,
                        "exclude_reason": v.exclude_reason,
                        "flagged_for_qa": v.flagged_for_qa,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )


# ---------------------------------------------------------------------------
# Draw execution.
# ---------------------------------------------------------------------------


def run_draw(
    candidate: Candidate,
    state: str,
    draw_index: int,
    generate: Callable[[str], Any],
    scalar: Callable[..., float],
    threshold: float,
    current_config_hash: str,
) -> dict[str, Any]:
    """Run one (candidate, state, draw) generation and build its log record.

    A draw that fails parsing or hits a provider/API error is logged with an 'error' field and
    otherwise-null scoring fields — it does NOT raise. The one exception is the model-identity
    guard (generate_row raises ModelIdentityError), which is allowed to propagate and halt the
    whole run: a spoofed/misrouted model must stop everything, per its purpose.
    """
    sources_text = _state_sources(candidate, state)
    prompt = _build_prompt(sources_text, candidate.question)

    base = {
        "task_id": candidate.task_id,
        "state": state,
        "draw_index": draw_index,
        "config_hash": current_config_hash,
        "ts": _utc_now(),
    }

    try:
        row: GeneratedRow = generate_row(generate, prompt)
    except Exception as exc:
        # generate_row raises ModelIdentityError on a pin mismatch — that must halt the run, so
        # re-raise it. Everything else (provider/API error, schema parse failure) is a logged,
        # skippable error draw.
        from .generate import ModelIdentityError

        if isinstance(exc, ModelIdentityError):
            raise
        base.update(
            {
                "reported_model": None,
                "output": None,
                "asserted_must_change": None,
                "asserted_must_persist": None,
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
        return base

    output = row.output
    change_flags = _score_flags(scalar, output, candidate.must_change, threshold)
    persist_flags = _score_flags(scalar, output, candidate.must_persist, threshold)

    base.update(
        {
            "reported_model": row.reported_model,
            "output": {
                "claims": [
                    {"id": c.id, "text": c.text, "source_ids": list(c.source_ids)}
                    for c in output.claims
                ],
                "conclusion": output.conclusion,
            },
            "asserted_must_change": change_flags,
            "asserted_must_persist": persist_flags,
            "error": None,
        }
    )
    return base


# ---------------------------------------------------------------------------
# Dry-run plan + cost estimate.
# ---------------------------------------------------------------------------


def dry_run_report(candidates: list[Candidate]) -> str:
    """Execution plan + a tokenizer-free rough cost estimate.

    Token estimate uses chars/3.5 over the rendered prompt for input and a flat per-draw output
    estimate; cost at $3/$15 per MTok. Rough by design — this is a budget sanity check, not a
    billing figure.
    """
    n_tasks = len(candidates)
    draws_per_task = len(STATES) * N_PILOT_DRAWS
    total_draws = n_tasks * draws_per_task

    est_input_tokens = 0
    for candidate in candidates:
        for state in STATES:
            prompt = _build_prompt(_state_sources(candidate, state), candidate.question)
            per_draw_input = int(len(prompt) / 3.5)
            est_input_tokens += per_draw_input * N_PILOT_DRAWS

    # Flat output estimate per draw: the 0001 output is a short claim list + one conclusion.
    est_output_tokens_per_draw = 400
    est_output_tokens = total_draws * est_output_tokens_per_draw

    input_cost = est_input_tokens / 1_000_000 * 3.0
    output_cost = est_output_tokens / 1_000_000 * 15.0
    total_cost = input_cost + output_cost

    lines = [
        "E5 A-dependency pilot — DRY RUN (no API calls, no NLI model loaded)",
        "",
        f"config_hash: {config_hash()}",
        f"model_pin:   {CONFIG.generation.model_pin}",
        f"sampler:     temperature={CONFIG.sampler.temperature}, top_p={CONFIG.sampler.top_p}",
        f"n_pilot_draws per state: {N_PILOT_DRAWS}",
        "",
        f"Plan: {n_tasks} tasks x {len(STATES)} states x {N_PILOT_DRAWS} draws = {total_draws} generations",
        "",
        "Rough cost estimate (chars/3.5 input est, flat 400-token output est, $3/$15 per MTok):",
        f"  est input tokens:  {est_input_tokens:,}",
        f"  est output tokens: {est_output_tokens:,}",
        f"  est input cost:    ${input_cost:.2f}",
        f"  est output cost:   ${output_cost:.2f}",
        f"  est TOTAL cost:    ${total_cost:.2f}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Run orchestration.
# ---------------------------------------------------------------------------


def run_pilot(
    candidates: list[Candidate],
    outdir: Path,
    generate: Callable[[str], Any],
    scalar: Callable[..., float],
) -> list[Verdict]:
    """Execute the full pilot: fill missing/stale draws, then recompute verdicts from the log.

    generate is the provider callable; scalar is the NLIScorer (constructed once by the caller).
    Resumability is keyed on (task_id, state, draw_index) at the current config_hash.
    """
    outdir.mkdir(parents=True, exist_ok=True)
    log_path = outdir / LOG_FILENAME
    verdicts_path = outdir / VERDICTS_FILENAME

    current_hash = config_hash()
    threshold = CONFIG.outcome.assert_threshold

    existing = read_log(log_path)
    done = _existing_keys(existing, current_hash)

    for candidate in candidates:
        for state in STATES:
            for draw_index in range(N_PILOT_DRAWS):
                key = (candidate.task_id, state, draw_index)
                if key in done:
                    continue
                record = run_draw(
                    candidate=candidate,
                    state=state,
                    draw_index=draw_index,
                    generate=generate,
                    scalar=scalar,
                    threshold=threshold,
                    current_config_hash=current_hash,
                )
                _append_log_line(log_path, record)

    # Recompute verdicts from the full (now-complete) log.
    all_records = read_log(log_path)
    candidates_by_id = {c.task_id: c for c in candidates}
    verdicts = compute_verdicts(all_records, candidates_by_id, current_hash)
    write_verdicts(verdicts_path, verdicts)
    return verdicts


def _summarize(verdicts: list[Verdict]) -> str:
    n = len(verdicts)
    n_pass = sum(1 for v in verdicts if v.verdict == "PASS")
    n_exclude = n - n_pass
    n_flagged = sum(1 for v in verdicts if v.flagged_for_qa)
    reasons: dict[str, int] = {}
    for v in verdicts:
        if v.exclude_reason:
            reasons[v.exclude_reason] = reasons.get(v.exclude_reason, 0) + 1
    lines = [
        f"candidates: {n}",
        f"PASS:       {n_pass}",
        f"EXCLUDE:    {n_exclude}",
        f"flagged_for_qa: {n_flagged}",
    ]
    if reasons:
        lines.append("exclude reasons:")
        for reason, count in sorted(reasons.items()):
            lines.append(f"  {count:>4}  {reason}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="closure_harness.pilot",
        description="E5 A-dependency pilot runner (corpus spec §5).",
    )
    parser.add_argument("--candidates", required=True, type=Path, help="candidates JSONL")
    parser.add_argument("--outdir", required=True, type=Path, help="output directory")
    parser.add_argument("--limit", type=int, default=None, help="only the first N candidates")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the plan and cost estimate, then exit (no API, no NLI)",
    )
    args = parser.parse_args(argv)

    candidates = load_candidates(args.candidates, limit=args.limit)

    if args.dry_run:
        print(dry_run_report(candidates))
        return 0

    # Real run: construct the provider (SDK-bound) and the NLI scorer (CPU, frozen config) once.
    from .nli import NLIScorer
    from .providers import make_provider

    generate = make_provider()
    scalar = NLIScorer()

    verdicts = run_pilot(candidates, args.outdir, generate, scalar)
    print(_summarize(verdicts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
