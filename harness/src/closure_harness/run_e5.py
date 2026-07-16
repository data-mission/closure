"""E5 registered-run runner (PROTOCOL-draft §2-S5, §4, §5, §6, §11).

The registered run of the three-arm reclosure comparison. For each of the 60 frozen tasks it
builds three arm outputs and scores every arm against the task's ground-truth annotations:

  Arm A — naive append: the task sources verbatim (A present), then the ¬A correction appended
          as an additional final numbered document. One generation.
  Arm B — instructed disregard: the same source block plus the frozen strong retract-and-revise
          instruction (ARM_B_INSTRUCTION), appended after the question. One generation.
  Arm C — mechanical contraction: NO generation. contraction.contract() is run on Arm A's parsed
          output against the same (A-present + ¬A) source block. This module never calls the
          detector directly — the contamination seam lives inside contract().

The entry point REFUSES to execute any generation unless the freeze-commit gate passes: the frozen
design must be PUBLIC before any data is generated. The gate requires ALL of:
  (a) the working tree is clean AND local HEAD equals origin/main (after a `git fetch origin`) —
      the freeze commit is pushed, not sitting local;
  (b) the live config_hash() equals the committed config.sha256 freeze token;
  (c) experiments/E5-reclosure/PROTOCOL.md exists at HEAD (the frozen protocol is committed, not a
      private draft);
  (d) experiments/E5-reclosure/corpus/tasks.jsonl exists at HEAD.
--dry-run prints the plan + cost and needs no gate. There is deliberately no flag to skip the gate.

The public commit history IS the pre-registration timestamp record (an OSF deposit was considered
and not adopted). The gate proves the design was committed and pushed before the
first generation ran.

Scoring uses outcomes.score() for every arm against the annotations, with the pilot prune register
applied (PROTOCOL §9b): must_change items listed in pruned-items.json are excluded from scoring by
(task_id, item_index). Statistics follow stats.py (PROTOCOL §6): pooled pairwise two-proportion
z-tests on contamination, completeness non-inferiority C-vs-B, MDE at the observed B baseline.

CLI:
    uv run python -m closure_harness.run_e5 \
        --corpus <tasks.jsonl> --outdir <dir> \
        [--dry-run] [--limit N] [--score-only] [--pruned-items <path>]

Artifacts written under --outdir:
    run-log.jsonl         one line per (task_id, arm) generation, keyed with config_hash
    freeze-gate.json      the freeze-commit gate snapshot (HEAD/origin hashes, protocol sha256)
    results-summary.json   scores + pairwise stats + non-inferiority + MDE
    VERDICT-numbers.md     the numbers block (interpretation belongs in VERDICT.md, not here)
    manifest.json         full run provenance (versions, hashes, device, timestamps, error counts)

Resumable and idempotent, same pattern as pilot.py: a (task_id, arm) generation already logged at
the current config_hash is skipped. --score-only recomputes scoring/stats from an existing log
with no generation at all (and no gate — it produces no new data).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import metadata as _im
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from .config import CONFIG, config_hash
from .contraction import contract
from .generate import GeneratedRow, ModelIdentityError, generate_row
from .outcomes import Annotations, Score, score
from .pilot import PROMPT_TEMPLATE, _build_prompt
from .schema import Claim, Output
from . import stats as _stats

# ---------------------------------------------------------------------------
# Arm identifiers and the two generating arms.
# ---------------------------------------------------------------------------

ARM_A = "A"
ARM_B = "B"
ARM_C = "C"
ARMS = (ARM_A, ARM_B, ARM_C)
# Only A and B generate; C is deterministic contraction of A's output.
GENERATING_ARMS = (ARM_A, ARM_B)

LOG_FILENAME = "run-log.jsonl"
FREEZE_GATE_FILENAME = "freeze-gate.json"
SUMMARY_FILENAME = "results-summary.json"
VERDICT_NUMBERS_FILENAME = "VERDICT-numbers.md"
MANIFEST_FILENAME = "manifest.json"

# Repo-relative paths the freeze-commit gate requires to exist at HEAD.
PROTOCOL_REPO_PATH = "experiments/E5-reclosure/PROTOCOL.md"
CORPUS_REPO_PATH = "experiments/E5-reclosure/corpus/tasks.jsonl"

# The three registered pairwise comparisons (PROTOCOL §6).
PAIRS = (("A", "B"), ("B", "C"), ("A", "C"))

# ---------------------------------------------------------------------------
# Frozen Arm-B instruction (PROTOCOL-draft §4, candidate C1, VERBATIM).
#
# Appended after the question and BEFORE the structured-output instruction lines. Authored once
# here, applied identically to all 60 tasks. This text is a frozen artifact — it is disclosed
# verbatim in PROTOCOL.md and must not drift from the committed protocol.
# ---------------------------------------------------------------------------

ARM_B_INSTRUCTION = (
    "A later document in the list above corrects an earlier statement. Before you answer, do all of "
    "the following: (1) Identify the specific earlier statement the final document overrides, and "
    "treat it as false from now on. (2) Find every claim and every intermediate conclusion that "
    "relied on that now-false statement, and recompute each using the corrected information instead. "
    "(3) Do not carry forward any figure, date, ranking, or verdict that was derived from the "
    "superseded statement — re-derive it from the correction or drop it. (4) Before finalizing, "
    "re-read your own claims and conclusion and confirm none still depends on the statement you "
    "retracted. Answer as if the corrected information had been true all along."
)


# ---------------------------------------------------------------------------
# Task record (the fields the run consumes).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Task:
    task_id: str
    sources: list[str]  # ordered source texts; index == source_id (A present)
    not_a_text: str  # not_A_evidence.text, appended as the final document in every arm
    question: str
    must_change: list[str]
    must_persist: list[str]


def parse_task(record: dict[str, Any]) -> Task:
    """Extract the run-relevant fields from one corpus JSON object.

    Sources are re-sorted by id so the positional index equals source_id everywhere (matching
    the pilot's parse_candidate). Provenance/covariate/depth fields are ignored here.
    """
    sources = record["sources"]
    sources_text = [s["text"] for s in sorted(sources, key=lambda s: s["id"])]
    return Task(
        task_id=record["task_id"],
        sources=sources_text,
        not_a_text=record["not_A_evidence"]["text"],
        question=record["question"],
        must_change=list(record["must_change"]),
        must_persist=list(record["must_persist"]),
    )


def load_tasks(path: Path, limit: int | None = None) -> list[Task]:
    tasks: list[Task] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            tasks.append(parse_task(json.loads(line)))
            if limit is not None and len(tasks) >= limit:
                break
    return tasks


# ---------------------------------------------------------------------------
# Arm context construction (PROTOCOL §4).
# ---------------------------------------------------------------------------


def arm_source_block(task: Task) -> list[str]:
    """The shared source block for Arms A, B, and C: the task sources verbatim (A present),
    then the ¬A correction APPENDED as an additional final numbered document.

    ¬A is appended, never substituted — the A-carrying source stays in place and ¬A is the last
    document. Claim source_ids (indices into this block) therefore line up for the contraction.
    """
    return [*task.sources, task.not_a_text]


def build_prompt_arm_a(task: Task) -> str:
    """Arm A prompt: the frozen template over the (A-present + ¬A-appended) block. No framing."""
    return _build_prompt(arm_source_block(task), task.question)


def build_prompt_arm_b(task: Task) -> str:
    """Arm B prompt: same block, with the frozen Arm-B instruction appended after the question,
    BEFORE the structured-output instruction lines (PROTOCOL §4).

    The pilot's PROMPT_TEMPLATE places the structured-output block after a blank line following
    the question. Arm B injects the instruction into that gap: the instruction sits directly after
    the question line and before the "Provide your answer as structured output" lines, exactly as
    the protocol specifies.
    """
    documents = "\n".join(f"[{i}] {text}" for i, text in enumerate(arm_source_block(task)))
    base = PROMPT_TEMPLATE.format(documents=documents, question=task.question)
    # Split the frozen template at the structured-output instruction so the Arm-B text lands
    # after the question and before those lines. The marker is stable and verbatim in the frozen
    # template; a change to it would (correctly) break this and force a protocol re-freeze.
    marker = "\nProvide your answer as structured output"
    idx = base.index(marker)
    head, tail = base[:idx], base[idx:]
    return f"{head}\n{ARM_B_INSTRUCTION}\n{tail}"


# ---------------------------------------------------------------------------
# Prune register (PROTOCOL §9b): must_change items excluded from scoring.
# ---------------------------------------------------------------------------


def load_pruned_index(path: Path) -> set[tuple[str, int]]:
    """Load pruned-items.json into a set of (task_id, item_index) keys.

    These must_change items are excluded from SCORING only (the task's sources and annotations are
    unchanged); each is a false-stale item the pilot found the model does not reliably flip even
    in the clean ¬A world.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    return {(item["task_id"], item["item_index"]) for item in data}


def pruned_register_hash(path: Path) -> str:
    """SHA-256 of the raw prune-register file bytes, logged for provenance."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply_prune(task: Task, pruned: set[tuple[str, int]]) -> list[str]:
    """The scored must_change list for a task: original items minus the pruned indices.

    Indexing is against the ORIGINAL must_change order (the item_index the register records), so
    pruning is applied before any reordering.
    """
    return [
        text
        for i, text in enumerate(task.must_change)
        if (task.task_id, i) not in pruned
    ]


# ---------------------------------------------------------------------------
# Freeze-commit gate (gate v2): the frozen design must be PUBLIC before any data.
# ---------------------------------------------------------------------------


class FreezeGateError(RuntimeError):
    """The freeze-commit gate refused the run. No generation may proceed."""


@dataclass(frozen=True)
class GitState:
    """The git facts the gate reads. Injectable so tests exercise every refusal path offline."""

    head: str
    origin_main: str
    is_clean: bool
    protocol_sha256: str | None  # sha256 of PROTOCOL.md at HEAD, or None if absent
    corpus_present: bool  # corpus/tasks.jsonl present at HEAD


def _run_git(args: list[str], repo_root: Path) -> tuple[int, str]:
    """Run a git command in repo_root, returning (returncode, stdout_stripped)."""
    proc = subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout.strip()


def read_git_state(repo_root: Path) -> GitState:
    """Read the gate's git facts from a real repository.

    Runs `git fetch origin` first so origin/main reflects the true remote tip (the freeze must be
    verified PUBLIC, not against a stale local ref). A fetch failure fails the gate closed — an
    unreachable remote means the public-freeze claim cannot be verified.
    """
    rc, _ = _run_git(["fetch", "origin"], repo_root)
    if rc != 0:
        raise FreezeGateError(
            "git fetch origin failed; the public-freeze claim cannot be verified, so the run "
            "refuses to proceed"
        )

    _, head = _run_git(["rev-parse", "HEAD"], repo_root)
    _, origin_main = _run_git(["rev-parse", "origin/main"], repo_root)

    rc_status, status_out = _run_git(["status", "--porcelain"], repo_root)
    is_clean = rc_status == 0 and status_out == ""

    # PROTOCOL.md and corpus at HEAD, read from the committed tree (not the working tree) so an
    # uncommitted local file cannot satisfy the gate.
    rc_proto, proto_blob = _run_git(["show", f"HEAD:{PROTOCOL_REPO_PATH}"], repo_root)
    protocol_sha256 = (
        hashlib.sha256(proto_blob.encode("utf-8")).hexdigest() if rc_proto == 0 else None
    )
    rc_corpus, _ = _run_git(["cat-file", "-e", f"HEAD:{CORPUS_REPO_PATH}"], repo_root)
    corpus_present = rc_corpus == 0

    return GitState(
        head=head,
        origin_main=origin_main,
        is_clean=is_clean,
        protocol_sha256=protocol_sha256,
        corpus_present=corpus_present,
    )


@dataclass(frozen=True)
class FreezeGateSnapshot:
    head: str
    origin_main: str
    committed_config_token: str
    live_config_hash: str
    protocol_path: str
    protocol_sha256: str
    corpus_path: str
    checked_at: str


def check_freeze_gate(
    committed_hash: str,
    git_state: GitState,
) -> FreezeGateSnapshot:
    """Enforce the freeze-commit gate; return the snapshot on success, else raise.

    Refusal paths (all raise FreezeGateError):
      (a) working tree is dirty, OR local HEAD != origin/main — the freeze is not pushed/public;
      (b) live config_hash() != committed config.sha256 token — the analysis plan drifted;
      (c) PROTOCOL.md absent at HEAD — the frozen protocol is not committed;
      (d) corpus/tasks.jsonl absent at HEAD — the frozen corpus is not committed.

    The public commit history is the pre-registration timestamp record: proving HEAD == origin/main
    on a clean tree is proving the design was frozen and pushed before this generation ran.
    """
    if not git_state.is_clean:
        raise FreezeGateError(
            "working tree is not clean; the freeze commit must be committed (nothing uncommitted) "
            "before any data is generated — the run refuses to proceed"
        )
    if git_state.head != git_state.origin_main:
        raise FreezeGateError(
            f"local HEAD ({git_state.head[:12]}) != origin/main ({git_state.origin_main[:12]}); "
            "the freeze commit is not pushed. The frozen design must be PUBLIC before any data — "
            "push first, then run"
        )

    live_hash = config_hash()
    if live_hash != committed_hash:
        raise FreezeGateError(
            "config hash mismatch: live config_hash() "
            f"{live_hash!r} != committed token {committed_hash!r}; the frozen analysis plan no "
            "longer matches the committed freeze token, so the run refuses to proceed"
        )

    if git_state.protocol_sha256 is None:
        raise FreezeGateError(
            f"{PROTOCOL_REPO_PATH} is not committed at HEAD; the frozen protocol must be public "
            "before any data — the run refuses to proceed"
        )
    if not git_state.corpus_present:
        raise FreezeGateError(
            f"{CORPUS_REPO_PATH} is not committed at HEAD; the frozen corpus must be public before "
            "any data — the run refuses to proceed"
        )

    return FreezeGateSnapshot(
        head=git_state.head,
        origin_main=git_state.origin_main,
        committed_config_token=committed_hash,
        live_config_hash=live_hash,
        protocol_path=PROTOCOL_REPO_PATH,
        protocol_sha256=git_state.protocol_sha256,
        corpus_path=CORPUS_REPO_PATH,
        checked_at=_utc_now(),
    )


# ---------------------------------------------------------------------------
# Log records + resumability (same pattern as pilot.py).
# ---------------------------------------------------------------------------


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
) -> set[tuple[str, str]]:
    """Keys (task_id, arm) already logged at the CURRENT config_hash.

    A record whose config_hash differs is stale (config drift invalidates it) and is re-run.
    """
    done: set[tuple[str, str]] = set()
    for rec in records:
        if rec.get("config_hash") != current_config_hash:
            continue
        done.add((rec["task_id"], rec["arm"]))
    return done


def _append_log_line(log_path: Path, record: dict[str, Any]) -> None:
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _output_to_dict(output: Output) -> dict[str, Any]:
    return {
        "claims": [
            {"id": c.id, "text": c.text, "source_ids": list(c.source_ids)}
            for c in output.claims
        ],
        "conclusion": output.conclusion,
    }


def _output_from_dict(payload: dict[str, Any]) -> Output:
    claims = tuple(
        Claim(id=c["id"], text=c["text"], source_ids=tuple(c["source_ids"]))
        for c in payload["claims"]
    )
    return Output(claims=claims, conclusion=payload["conclusion"])


# ---------------------------------------------------------------------------
# Generation for one (task, generating arm).
# ---------------------------------------------------------------------------


def run_generation(
    task: Task,
    arm: str,
    generate: Callable[[str], Any],
    current_config_hash: str,
) -> dict[str, Any]:
    """Run one (task, arm) generation and build its log record (arm in {A, B}).

    A draw that hits a provider error, refusal, truncation, or schema-parse failure is logged with
    an 'error' field and does NOT crash the run (PROTOCOL §8). The one exception is a model-identity
    mismatch (generate_row raises ModelIdentityError), which propagates and halts everything.
    """
    if arm == ARM_A:
        prompt = build_prompt_arm_a(task)
    elif arm == ARM_B:
        prompt = build_prompt_arm_b(task)
    else:
        raise ValueError(f"run_generation is only for generating arms A/B, got {arm!r}")

    base = {
        "task_id": task.task_id,
        "arm": arm,
        "config_hash": current_config_hash,
        "ts": _utc_now(),
    }

    try:
        row: GeneratedRow = generate_row(generate, prompt)
    except ModelIdentityError:
        # A spoofed/misrouted model must stop everything, per the identity guard's purpose.
        raise
    except Exception as exc:  # noqa: BLE001 — provider/schema errors become logged error draws
        base.update(
            {
                "reported_model": None,
                "output": None,
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
        return base

    base.update(
        {
            "reported_model": row.reported_model,
            "output": _output_to_dict(row.output),
            "error": None,
        }
    )
    return base


# ---------------------------------------------------------------------------
# Scoring (PROTOCOL §5) — from the completed log, with the prune register applied.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArmScore:
    task_id: str
    arm: str
    contamination: float
    completeness: float
    # Pooled-item counts for the z-test: successes = must_change items still asserted.
    change_asserted: int
    change_total: int
    persist_asserted: int
    persist_total: int


def _score_output(
    scalar: Callable[..., float],
    output: Output,
    scored_must_change: list[str],
    must_persist: list[str],
) -> tuple[Score, int, int, int, int]:
    """Score one output and also return the pooled per-item assertion counts.

    outcomes.score() gives the per-task fractions; the pooled z-test additionally needs the raw
    (asserted, total) item counts, so those are recomputed here against the SAME asserted set and
    threshold via outcomes._still_asserts (no new scoring logic).
    """
    from .outcomes import _still_asserts

    annotations = Annotations(
        must_change=tuple(scored_must_change),
        must_persist=tuple(must_persist),
    )
    s = score(scalar, output, annotations)
    t = CONFIG.outcome.assert_threshold
    change_asserted = sum(1 for c in scored_must_change if _still_asserts(scalar, output, c, t))
    persist_asserted = sum(1 for c in must_persist if _still_asserts(scalar, output, c, t))
    return s, change_asserted, len(scored_must_change), persist_asserted, len(must_persist)


def score_from_log(
    records: list[dict[str, Any]],
    tasks: list[Task],
    pruned: set[tuple[str, int]],
    scalar: Callable[..., float],
    current_config_hash: str,
) -> tuple[list[ArmScore], dict[str, int]]:
    """Score every arm of every task from the log; return per-(task, arm) scores + error counts.

    Arm C is built HERE via contraction.contract() on Arm A's parsed output against the arm source
    block — never generated, never via a direct detector call. A task whose Arm A draw errored (no
    usable output) contributes no A/C score and is counted as an error for both arms.
    """
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    error_counts = {arm: 0 for arm in ARMS}
    for rec in records:
        if rec.get("config_hash") != current_config_hash:
            continue
        arm = rec.get("arm")
        if arm not in GENERATING_ARMS:
            continue
        by_key[(rec["task_id"], arm)] = rec

    scores: list[ArmScore] = []
    for task in tasks:
        scored_change = apply_prune(task, pruned)
        # Guard: outcomes.score() raises on an empty must_change/must_persist — a construction
        # error. The pilot pruning invariant guarantees ≥1 unpruned item, but assert it here so a
        # corrupt corpus/register fails loudly rather than silently skewing the pooled counts.
        if not scored_change:
            raise ValueError(
                f"task {task.task_id}: all must_change items pruned — violates the pilot invariant"
            )

        rec_a = by_key.get((task.task_id, ARM_A))
        rec_b = by_key.get((task.task_id, ARM_B))

        # Arm A.
        output_a: Output | None = None
        if rec_a is None or rec_a.get("error") is not None or rec_a.get("output") is None:
            error_counts[ARM_A] += 1
        else:
            output_a = _output_from_dict(rec_a["output"])
            s, ca, ct, pa, pt = _score_output(scalar, output_a, scored_change, task.must_persist)
            scores.append(
                ArmScore(task.task_id, ARM_A, s.contamination, s.completeness, ca, ct, pa, pt)
            )

        # Arm B.
        if rec_b is None or rec_b.get("error") is not None or rec_b.get("output") is None:
            error_counts[ARM_B] += 1
        else:
            output_b = _output_from_dict(rec_b["output"])
            s, ca, ct, pa, pt = _score_output(scalar, output_b, scored_change, task.must_persist)
            scores.append(
                ArmScore(task.task_id, ARM_B, s.contamination, s.completeness, ca, ct, pa, pt)
            )

        # Arm C — mechanical contraction of Arm A's output (zero generation). If A errored, C
        # cannot be built, so C is counted as an error too (symmetric with the A miss).
        if output_a is None:
            error_counts[ARM_C] += 1
        else:
            output_c = contract(scalar, arm_source_block(task), output_a)
            s, ca, ct, pa, pt = _score_output(scalar, output_c, scored_change, task.must_persist)
            scores.append(
                ArmScore(task.task_id, ARM_C, s.contamination, s.completeness, ca, ct, pa, pt)
            )

    return scores, error_counts


# ---------------------------------------------------------------------------
# Statistics + verdict numbers (PROTOCOL §6).
# ---------------------------------------------------------------------------


def _pooled(scores: Sequence[ArmScore], arm: str) -> tuple[int, int]:
    """Pooled (must_change successes, trials) for an arm across tasks (PROTOCOL §6a)."""
    successes = sum(s.change_asserted for s in scores if s.arm == arm)
    trials = sum(s.change_total for s in scores if s.arm == arm)
    return successes, trials


def _by_task(scores: Sequence[ArmScore], arm: str) -> dict[str, ArmScore]:
    return {s.task_id: s for s in scores if s.arm == arm}


def compute_stats(scores: list[ArmScore]) -> dict[str, Any]:
    """Pairwise z-tests, completeness non-inferiority (C vs B), and MDE at the B baseline.

    Numbers only. No verdict interpretation is applied here — that belongs in VERDICT.md.
    """
    result: dict[str, Any] = {"pairwise_ztests": {}, "arm_rates": {}}

    # Per-arm pooled contamination rate + mean completeness.
    for arm in ARMS:
        succ, trials = _pooled(scores, arm)
        arm_scores = [s for s in scores if s.arm == arm]
        mean_completeness = (
            sum(s.completeness for s in arm_scores) / len(arm_scores) if arm_scores else None
        )
        result["arm_rates"][arm] = {
            "contamination_pooled": (succ / trials) if trials else None,
            "change_successes": succ,
            "change_trials": trials,
            "mean_completeness": mean_completeness,
            "n_tasks_scored": len(arm_scores),
        }

    # Pairwise two-proportion z-tests on pooled contamination.
    for a, b in PAIRS:
        sa, ta = _pooled(scores, a)
        sb, tb = _pooled(scores, b)
        if ta > 0 and tb > 0:
            zt = _stats.two_proportion_ztest(sa, ta, sb, tb)
            result["pairwise_ztests"][f"{a}_vs_{b}"] = {
                "p_hat_a": zt.p_hat_a,
                "p_hat_b": zt.p_hat_b,
                "z": zt.z,
                "p_value": zt.p_value,
                "p_value_corrected": zt.p_value_corrected,
                "significant": zt.significant,
            }
        else:
            result["pairwise_ztests"][f"{a}_vs_{b}"] = None

    # Completeness non-inferiority: C vs B, paired at the task level over tasks scored in BOTH.
    c_by_task = _by_task(scores, ARM_C)
    b_by_task = _by_task(scores, ARM_B)
    shared = sorted(set(c_by_task) & set(b_by_task))
    if shared:
        comp_c = [c_by_task[t].completeness for t in shared]
        comp_b = [b_by_task[t].completeness for t in shared]
        ni = _stats.completeness_non_inferiority(comp_c, comp_b)
        result["completeness_non_inferiority_c_vs_b"] = {
            "mean_c": ni.mean_c,
            "mean_b": ni.mean_b,
            "diff": ni.diff,
            "margin": ni.margin,
            "non_inferior": ni.non_inferior,
            "n_paired_tasks": len(shared),
        }
    else:
        result["completeness_non_inferiority_c_vs_b"] = None

    # MDE at the observed B baseline pooled contamination rate.
    sb, tb = _pooled(scores, ARM_B)
    if tb > 0:
        baseline = sb / tb
        result["mde_at_b_baseline"] = {
            "b_baseline_contamination": baseline,
            "mde_absolute": _stats.minimum_detectable_effect(baseline),
            "n_tasks": CONFIG.stats.n_tasks,
            "power": 0.8,
        }
    else:
        result["mde_at_b_baseline"] = None

    return result


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def verdict_numbers_md(stats_result: dict[str, Any], error_counts: dict[str, int]) -> str:
    """The VERDICT-numbers.md block: numbers only, no interpretation (S5 role split)."""
    lines = [
        "# E5 verdict numbers",
        "",
        "Numbers only. Verdict interpretation against the three pre-registered outcomes is",
        "written in VERDICT.md — not here.",
        "",
        "## Per-arm rates",
        "",
        "| arm | contamination (pooled) | change succ/trials | mean completeness | tasks scored |",
        "|---|---|---|---|---|",
    ]
    for arm in ARMS:
        r = stats_result["arm_rates"][arm]
        lines.append(
            f"| {arm} | {_fmt(r['contamination_pooled'])} | "
            f"{r['change_successes']}/{r['change_trials']} | "
            f"{_fmt(r['mean_completeness'])} | {r['n_tasks_scored']} |"
        )

    lines += [
        "",
        "## Pairwise two-proportion z-tests on pooled contamination (Bonferroni x3, alpha=0.05)",
        "",
        "| pair | p_hat_a | p_hat_b | z | p | p_corrected | significant |",
        "|---|---|---|---|---|---|---|",
    ]
    for a, b in PAIRS:
        zt = stats_result["pairwise_ztests"][f"{a}_vs_{b}"]
        if zt is None:
            lines.append(f"| {a} vs {b} | n/a | n/a | n/a | n/a | n/a | n/a |")
        else:
            lines.append(
                f"| {a} vs {b} | {_fmt(zt['p_hat_a'])} | {_fmt(zt['p_hat_b'])} | "
                f"{_fmt(zt['z'])} | {_fmt(zt['p_value'])} | {_fmt(zt['p_value_corrected'])} | "
                f"{_fmt(zt['significant'])} |"
            )

    ni = stats_result["completeness_non_inferiority_c_vs_b"]
    lines += ["", "## Completeness non-inferiority (C vs B, paired, delta=0.10)", ""]
    if ni is None:
        lines.append("n/a (no paired tasks)")
    else:
        lines += [
            f"- mean completeness C: {_fmt(ni['mean_c'])}",
            f"- mean completeness B: {_fmt(ni['mean_b'])}",
            f"- diff (C - B): {_fmt(ni['diff'])}   margin: {_fmt(ni['margin'])}",
            f"- non-inferior: {_fmt(ni['non_inferior'])}   (paired tasks: {ni['n_paired_tasks']})",
        ]

    mde = stats_result["mde_at_b_baseline"]
    lines += ["", "## MDE at the observed B baseline", ""]
    if mde is None:
        lines.append("n/a (no B trials)")
    else:
        lines += [
            f"- B baseline contamination: {_fmt(mde['b_baseline_contamination'])}",
            f"- MDE (absolute, N={mde['n_tasks']}, power={mde['power']}): {_fmt(mde['mde_absolute'])}",
        ]

    lines += [
        "",
        "## Error draws per arm",
        "",
        f"- Arm A: {error_counts.get('A', 0)}",
        f"- Arm B: {error_counts.get('B', 0)}",
        f"- Arm C (uncomputable — Arm A errored): {error_counts.get('C', 0)}",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Manifest (PROTOCOL §11 run manifest).
# ---------------------------------------------------------------------------


def _pkg_version(name: str) -> str | None:
    try:
        return _im.version(name)
    except _im.PackageNotFoundError:
        return None


def build_manifest(
    corpus_path: Path,
    pruned_path: Path,
    gate: FreezeGateSnapshot | None,
    error_counts: dict[str, int],
    started_at: str,
    ended_at: str,
) -> dict[str, Any]:
    """Full run provenance (PROTOCOL §11 + freeze-gate record)."""
    return {
        "config_hash": config_hash(),
        "committed_config_token": Path(_config_sha256_path()).read_text().strip()
        if _config_sha256_path().exists()
        else None,
        "freeze_gate": None
        if gate is None
        else {
            "head": gate.head,
            "origin_main": gate.origin_main,
            "protocol_path": gate.protocol_path,
            "protocol_sha256": gate.protocol_sha256,
            "corpus_path": gate.corpus_path,
            "checked_at": gate.checked_at,
        },
        "corpus_file": str(corpus_path),
        "corpus_sha256": hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
        "pruned_register_file": str(pruned_path),
        "pruned_register_sha256": pruned_register_hash(pruned_path),
        "model_pin": CONFIG.generation.model_pin,
        "device": CONFIG.nli.device,
        "nli_checkpoint": (
            CONFIG.nli.fallback_checkpoint if CONFIG.nli.use_fallback else CONFIG.nli.checkpoint
        ),
        "nli_revision": (
            CONFIG.nli.fallback_revision if CONFIG.nli.use_fallback else CONFIG.nli.revision
        ),
        "torch_version": _pkg_version("torch"),
        "transformers_version": _pkg_version("transformers"),
        "started_at": started_at,
        "ended_at": ended_at,
        "error_counts": error_counts,
    }


def _harness_root() -> Path:
    """harness/ directory. src/closure_harness/run_e5.py -> harness/."""
    return Path(__file__).resolve().parent.parent.parent


def _config_sha256_path() -> Path:
    """Path to the committed freeze token file (harness/config.sha256)."""
    return _harness_root() / "config.sha256"


def _repo_root() -> Path:
    """The closure repository root (harness/..): where the freeze-gate git checks run."""
    return _harness_root().parent


def read_committed_hash() -> str:
    """The committed pre-registration freeze token from config.sha256."""
    path = _config_sha256_path()
    if not path.exists():
        raise FreezeGateError(f"committed config token not found at {path}")
    return path.read_text(encoding="utf-8").strip()


# ---------------------------------------------------------------------------
# Dry-run plan + cost estimate.
# ---------------------------------------------------------------------------


def dry_run_report(tasks: list[Task]) -> str:
    """Execution plan + a tokenizer-free rough cost estimate (mirrors pilot.dry_run_report).

    Only Arms A and B generate; Arm C is deterministic and free. Estimate uses chars/3.5 input,
    a flat 400-token output per generation, $3/$15 per MTok.
    """
    n_tasks = len(tasks)
    total_generations = n_tasks * len(GENERATING_ARMS)

    est_input_tokens = 0
    for task in tasks:
        prompt_a = build_prompt_arm_a(task)
        prompt_b = build_prompt_arm_b(task)
        est_input_tokens += int(len(prompt_a) / 3.5) + int(len(prompt_b) / 3.5)

    est_output_tokens = total_generations * 400
    input_cost = est_input_tokens / 1_000_000 * 3.0
    output_cost = est_output_tokens / 1_000_000 * 15.0
    total_cost = input_cost + output_cost

    lines = [
        "E5 registered run — DRY RUN (no API calls, no NLI model loaded, no freeze gate)",
        "",
        f"config_hash:            {config_hash()}",
        f"committed token:        {read_committed_hash()}",
        f"model_pin:              {CONFIG.generation.model_pin}",
        f"sampler:                sampling={CONFIG.sampler.sampling}, thinking={CONFIG.sampler.thinking}",
        f"nli device:             {CONFIG.nli.device}",
        "",
        f"Plan: {n_tasks} tasks x {len(GENERATING_ARMS)} generating arms (A, B) = "
        f"{total_generations} generations",
        "      + Arm C: deterministic contraction of Arm A (0 generations)",
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
# Output writers.
# ---------------------------------------------------------------------------


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _scores_payload(scores: list[ArmScore]) -> list[dict[str, Any]]:
    return [
        {
            "task_id": s.task_id,
            "arm": s.arm,
            "contamination": s.contamination,
            "completeness": s.completeness,
            "change_asserted": s.change_asserted,
            "change_total": s.change_total,
            "persist_asserted": s.persist_asserted,
            "persist_total": s.persist_total,
        }
        for s in scores
    ]


# ---------------------------------------------------------------------------
# Run orchestration.
# ---------------------------------------------------------------------------


def run(
    tasks: list[Task],
    outdir: Path,
    corpus_path: Path,
    pruned_path: Path,
    generate: Callable[[str], Any],
    scalar: Callable[..., float],
    gate: FreezeGateSnapshot | None,
) -> dict[str, Any]:
    """Execute the registered run: fill missing/stale generations (A, B), then score all arms.

    Assumes the freeze-commit gate has already passed (the caller enforces it before constructing
    the provider). Resumability is keyed on (task_id, arm) at the current config_hash.
    """
    outdir.mkdir(parents=True, exist_ok=True)
    log_path = outdir / LOG_FILENAME
    current_hash = config_hash()
    started_at = _utc_now()

    existing = read_log(log_path)
    done = _existing_keys(existing, current_hash)

    for task in tasks:
        for arm in GENERATING_ARMS:
            if (task.task_id, arm) in done:
                continue
            record = run_generation(task, arm, generate, current_hash)
            _append_log_line(log_path, record)

    ended_at = _utc_now()
    return _score_and_write(
        tasks, outdir, corpus_path, pruned_path, scalar, gate, started_at, ended_at
    )


def _score_and_write(
    tasks: list[Task],
    outdir: Path,
    corpus_path: Path,
    pruned_path: Path,
    scalar: Callable[..., float],
    gate: FreezeGateSnapshot | None,
    started_at: str,
    ended_at: str,
) -> dict[str, Any]:
    """Score the (now-complete) log, compute stats, and write all artifacts."""
    log_path = outdir / LOG_FILENAME
    current_hash = config_hash()
    pruned = load_pruned_index(pruned_path)

    records = read_log(log_path)
    scores, error_counts = score_from_log(records, tasks, pruned, scalar, current_hash)
    stats_result = compute_stats(scores)

    summary = {
        "config_hash": current_hash,
        "pruned_register_sha256": pruned_register_hash(pruned_path),
        "scores": _scores_payload(scores),
        "stats": stats_result,
        "error_counts": error_counts,
    }
    write_json(outdir / SUMMARY_FILENAME, summary)
    (outdir / VERDICT_NUMBERS_FILENAME).write_text(
        verdict_numbers_md(stats_result, error_counts), encoding="utf-8"
    )

    if gate is not None:
        write_json(outdir / FREEZE_GATE_FILENAME, _gate_payload(gate))

    manifest = build_manifest(
        corpus_path, pruned_path, gate, error_counts, started_at, ended_at
    )
    write_json(outdir / MANIFEST_FILENAME, manifest)
    return summary


def _gate_payload(gate: FreezeGateSnapshot) -> dict[str, Any]:
    return {
        "head": gate.head,
        "origin_main": gate.origin_main,
        "committed_config_token": gate.committed_config_token,
        "live_config_hash": gate.live_config_hash,
        "protocol_path": gate.protocol_path,
        "protocol_sha256": gate.protocol_sha256,
        "corpus_path": gate.corpus_path,
        "checked_at": gate.checked_at,
    }


def run_score_only(
    tasks: list[Task],
    outdir: Path,
    corpus_path: Path,
    pruned_path: Path,
    scalar: Callable[..., float],
) -> dict[str, Any]:
    """Recompute scoring/stats from an existing log with NO generation and NO freeze gate.

    --score-only produces no new data (no API call), so it needs no gate. It reads run-log.jsonl,
    rebuilds all arms (Arm C via contraction), and rewrites the summary/verdict/manifest.
    """
    log_path = outdir / LOG_FILENAME
    if not log_path.exists():
        raise FileNotFoundError(
            f"--score-only needs an existing {LOG_FILENAME} in {outdir}; none found"
        )
    now = _utc_now()
    return _score_and_write(
        tasks, outdir, corpus_path, pruned_path, scalar, None, now, now
    )


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------


def _default_pruned_path() -> Path | None:
    """Best-effort default location of pruned-items.json (private notes).

    The register lives in the private _dev_notes tree, not the public repo; the runner takes an
    explicit --pruned-items path in practice. This returns None when the default isn't present so
    the CLI can demand the flag rather than silently scoring against no prune register.
    """
    candidate = (
        Path.home()
        / "repos/merchloom-2/merchloom/_dev_notes/closure-ir-research/E5-CORPUS/pruned-items.json"
    )
    return candidate if candidate.exists() else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="closure_harness.run_e5",
        description="E5 registered-run runner (PROTOCOL §2-S5).",
    )
    parser.add_argument("--corpus", required=True, type=Path, help="frozen corpus tasks JSONL")
    parser.add_argument("--outdir", required=True, type=Path, help="output directory")
    parser.add_argument(
        "--pruned-items",
        type=Path,
        default=None,
        help="pruned-items.json (must_change prune register); defaults to the private-notes path",
    )
    parser.add_argument("--limit", type=int, default=None, help="only the first N tasks")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the plan and cost estimate, then exit (no API, no NLI, no gate)",
    )
    parser.add_argument(
        "--score-only",
        action="store_true",
        help="recompute scoring/stats from an existing run-log.jsonl; no generation, no gate",
    )
    args = parser.parse_args(argv)

    tasks = load_tasks(args.corpus, limit=args.limit)

    if args.dry_run:
        print(dry_run_report(tasks))
        return 0

    pruned_path = args.pruned_items or _default_pruned_path()
    if pruned_path is None or not Path(pruned_path).exists():
        print(
            "error: prune register not found; pass --pruned-items <path to pruned-items.json>",
            file=sys.stderr,
        )
        return 2

    from .nli import NLIScorer

    if args.score_only:
        # --score-only produces no new data, so it needs no gate. It DOES need the scorer.
        scalar = NLIScorer()
        summary = run_score_only(tasks, args.outdir, args.corpus, Path(pruned_path), scalar)
        print(_summarize(summary))
        return 0

    # Freeze-commit gate — enforced FIRST, before the NLI model is loaded or any provider is
    # constructed. A gate refusal must be cheap: it must not pay the model-load cost. The git reads
    # (fetch + rev-parse + status) run in the closure repo root.
    try:
        git_state = read_git_state(_repo_root())
        gate = check_freeze_gate(read_committed_hash(), git_state)
    except FreezeGateError as exc:
        print(f"FREEZE GATE REFUSED: {exc}", file=sys.stderr)
        return 3

    args.outdir.mkdir(parents=True, exist_ok=True)
    # Persist the gate snapshot immediately as evidence, before any generation runs.
    write_json(args.outdir / FREEZE_GATE_FILENAME, _gate_payload(gate))

    from .providers import make_provider

    generate = make_provider()
    summary = run(
        tasks,
        args.outdir,
        args.corpus,
        Path(pruned_path),
        generate,
        scalar,
        gate,
    )
    print(_summarize(summary))
    return 0


def _summarize(summary: dict[str, Any]) -> str:
    stats_result = summary["stats"]
    lines = ["E5 registered run — scoring complete", ""]
    for arm in ARMS:
        r = stats_result["arm_rates"][arm]
        lines.append(
            f"  arm {arm}: contamination(pooled)={_fmt(r['contamination_pooled'])} "
            f"mean_completeness={_fmt(r['mean_completeness'])} tasks={r['n_tasks_scored']}"
        )
    lines.append("")
    for a, b in PAIRS:
        zt = stats_result["pairwise_ztests"][f"{a}_vs_{b}"]
        if zt is None:
            lines.append(f"  {a} vs {b}: n/a")
        else:
            lines.append(
                f"  {a} vs {b}: z={_fmt(zt['z'])} p_corr={_fmt(zt['p_value_corrected'])} "
                f"significant={_fmt(zt['significant'])}"
            )
    ec = summary["error_counts"]
    lines.append("")
    lines.append(f"  error draws: A={ec.get('A', 0)} B={ec.get('B', 0)} C={ec.get('C', 0)}")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
