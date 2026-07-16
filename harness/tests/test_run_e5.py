"""E5 registered-run runner tests (PROTOCOL §2-S5).

No API, no model download: a stub provider returns canned structured outputs and a stub scalar
returns programmable NLI values, so arms construction, the registration gate, Arm-C-via-contract,
prune-register application, resumability, and --score-only are exercised on synthetic,
hand-computed cases.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from closure_harness.config import CONFIG, config_hash
from closure_harness import run_e5
from closure_harness.generate import ModelIdentityError
from closure_harness.run_e5 import (
    ARM_A,
    ARM_B,
    ARM_B_INSTRUCTION,
    CORPUS_REPO_PATH,
    PROTOCOL_REPO_PATH,
    FreezeGateError,
    GitState,
    Task,
    apply_prune,
    arm_source_block,
    build_prompt_arm_a,
    build_prompt_arm_b,
    check_freeze_gate,
    load_pruned_index,
    load_tasks,
    parse_task,
    read_log,
    run,
    run_score_only,
    score_from_log,
)

PIN = CONFIG.generation.model_pin


# ---------------------------------------------------------------------------
# Fixtures: a task, a stub provider, a stub scalar.
# ---------------------------------------------------------------------------


def make_task(task_id: str = "F1-0001") -> Task:
    return Task(
        task_id=task_id,
        sources=["S0 text", "A-carrying source text", "S2 text"],
        not_a_text="NOT-A correction text",
        question="Can it be done?",
        must_change=["The plan is infeasible.", "A second trip is required."],
        must_persist=["The deadline is 17:00.", "The drive is 40 minutes."],
    )


TASK_RECORD = {
    "task_id": "F1-0001",
    "family": "F1",
    "dependency_depth": "direct",
    "sources": [
        {"id": 0, "text": "S0 text"},
        {"id": 1, "text": "A-carrying source text"},
        {"id": 2, "text": "S2 text"},
    ],
    "assumption_A": {"source_id": 1, "text": "A-carrying source text"},
    "not_A_evidence": {"text": "NOT-A correction text", "supersedes_source_id": 1},
    "question": "Can it be done?",
    "must_change": ["The plan is infeasible.", "A second trip is required."],
    "must_persist": ["The deadline is 17:00.", "The drive is 40 minutes."],
    "covariates": {"source_count": 3},
}


@dataclass
class StubResponse:
    output: dict
    model: str


class StubProvider:
    """Programmable provider callable, same shape as the pilot's stub.

    Script entries are dict (returned wrapped with the pin id unless `_model` overrides), or an
    Exception instance (raised — an error draw or, for ModelIdentityError, a halt).
    """

    def __init__(self, script):
        self.script = list(script)
        self.calls = 0
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> StubResponse:
        self.prompts.append(prompt)
        item = self.script[self.calls]
        self.calls += 1
        if isinstance(item, Exception):
            raise item
        model = item.pop("_model", PIN) if isinstance(item, dict) else PIN
        return StubResponse(output=item, model=model)


def out(*, conclusion="c", claims=None) -> dict:
    return {
        "claims": claims if claims is not None else [{"id": 1, "text": "a claim", "source_ids": [0]}],
        "conclusion": conclusion,
    }


class StubScalar:
    """Programmable scalar keyed on (tuple(sorted(sources)), claim) -> float, default otherwise."""

    def __init__(self, table: dict | None = None, default: float = 0.0):
        self.table = dict(table or {})
        self.default = default

    def __call__(self, sources, claim) -> float:
        return self.table.get((tuple(sorted(sources)), claim), self.default)


def write_corpus(path: Path, records) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


def write_pruned(path: Path, items) -> Path:
    path.write_text(json.dumps(items), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Arms construction (PROTOCOL §4).
# ---------------------------------------------------------------------------


def test_arm_source_block_appends_not_a_without_substituting_a():
    task = make_task()
    block = arm_source_block(task)
    # ¬A is appended as the FINAL document, and A is still present in place.
    assert block[-1] == task.not_a_text
    assert task.sources[1] in block  # the A-carrying source is NOT removed
    assert block[:3] == task.sources  # original sources verbatim, order preserved
    assert len(block) == len(task.sources) + 1


def test_arm_a_prompt_has_a_and_not_a_and_no_instruction():
    task = make_task()
    prompt = build_prompt_arm_a(task)
    assert "[1] A-carrying source text" in prompt  # A still present
    assert "[3] NOT-A correction text" in prompt  # ¬A appended last
    assert ARM_B_INSTRUCTION not in prompt  # Arm A carries no revision framing
    assert "Can it be done?" in prompt


def test_arm_b_prompt_injects_instruction_after_question_before_schema():
    task = make_task()
    prompt = build_prompt_arm_b(task)
    assert "[1] A-carrying source text" in prompt  # A present
    assert "[3] NOT-A correction text" in prompt  # ¬A appended last
    assert ARM_B_INSTRUCTION in prompt
    # Instruction sits after the question and before the structured-output block.
    q_idx = prompt.index("Question: Can it be done?")
    instr_idx = prompt.index(ARM_B_INSTRUCTION)
    schema_idx = prompt.index("Provide your answer as structured output")
    assert q_idx < instr_idx < schema_idx


def test_arm_b_instruction_first_words_anchor():
    # Verification anchor: the frozen Arm-B constant is the verbatim candidate C1 text.
    first_20 = " ".join(ARM_B_INSTRUCTION.split()[:20])
    assert first_20 == (
        "A later document in the list above corrects an earlier statement. Before you answer, "
        "do all of the following: (1)"
    )


# ---------------------------------------------------------------------------
# Task parsing.
# ---------------------------------------------------------------------------


def test_parse_task_extracts_fields_and_orders_sources():
    record = json.loads(json.dumps(TASK_RECORD))
    record["sources"] = list(reversed(record["sources"]))  # shuffle
    task = parse_task(record)
    assert task.task_id == "F1-0001"
    assert task.sources == ["S0 text", "A-carrying source text", "S2 text"]
    assert task.not_a_text == "NOT-A correction text"
    assert len(task.must_change) == 2


# ---------------------------------------------------------------------------
# Freeze-commit gate (gate v2). The git facts are injected via a GitState so every refusal path
# is exercised offline (no real repo, no network).
# ---------------------------------------------------------------------------


def good_git_state(head="abc123", protocol_sha="deadbeef") -> GitState:
    """A GitState that passes every non-config check: clean, HEAD==origin/main, files present."""
    return GitState(
        head=head,
        origin_main=head,  # local == remote
        is_clean=True,
        protocol_sha256=protocol_sha,
        corpus_present=True,
    )


def test_gate_refuses_on_dirty_tree():
    gs = GitState(head="a", origin_main="a", is_clean=False, protocol_sha256="x", corpus_present=True)
    with pytest.raises(FreezeGateError, match="working tree is not clean"):
        check_freeze_gate(config_hash(), gs)


def test_gate_refuses_when_head_ne_origin():
    gs = GitState(
        head="localsha", origin_main="remotesha", is_clean=True, protocol_sha256="x", corpus_present=True
    )
    with pytest.raises(FreezeGateError, match="not pushed"):
        check_freeze_gate(config_hash(), gs)


def test_gate_refuses_on_hash_mismatch():
    with pytest.raises(FreezeGateError, match="config hash mismatch"):
        check_freeze_gate("deadbeef-not-the-token", good_git_state())


def test_gate_refuses_when_protocol_absent():
    gs = GitState(head="a", origin_main="a", is_clean=True, protocol_sha256=None, corpus_present=True)
    with pytest.raises(FreezeGateError, match=PROTOCOL_REPO_PATH):
        check_freeze_gate(config_hash(), gs)


def test_gate_refuses_when_corpus_absent():
    gs = GitState(
        head="a", origin_main="a", is_clean=True, protocol_sha256="x", corpus_present=False
    )
    with pytest.raises(FreezeGateError, match=CORPUS_REPO_PATH):
        check_freeze_gate(config_hash(), gs)


def test_gate_passes_and_records_snapshot():
    snap = check_freeze_gate(config_hash(), good_git_state(head="feedface", protocol_sha="cafe"))
    assert snap.head == "feedface"
    assert snap.origin_main == "feedface"
    assert snap.committed_config_token == config_hash()
    assert snap.live_config_hash == config_hash()
    assert snap.protocol_sha256 == "cafe"
    assert snap.protocol_path == PROTOCOL_REPO_PATH
    assert snap.corpus_path == CORPUS_REPO_PATH


def test_no_skip_gate_flag_exists():
    # The module source must contain no gate-skipping flag in any form.
    src = Path(run_e5.__file__).read_text()
    assert "--skip-gate" not in src
    assert "skip_gate" not in src
    assert "skip-gate" not in src


# ---------------------------------------------------------------------------
# Import hygiene: run_e5 must not import the detector directly (Arm C via contract only).
# ---------------------------------------------------------------------------


def test_run_e5_does_not_import_detector():
    src = Path(run_e5.__file__).read_text()
    # No import of the detector module anywhere.
    assert "import detector" not in src
    assert "from .detector" not in src
    assert "closure_harness.detector" not in src
    # And no direct is_contaminated call — the contamination seam lives inside contract().
    assert "is_contaminated" not in src


# ---------------------------------------------------------------------------
# Prune register (PROTOCOL §9b).
# ---------------------------------------------------------------------------


def test_load_pruned_index_and_apply(tmp_path):
    pruned_path = write_pruned(
        tmp_path / "pruned.json",
        [{"task_id": "F1-0001", "item_index": 1, "text": "A second trip is required."}],
    )
    pruned = load_pruned_index(pruned_path)
    assert ("F1-0001", 1) in pruned

    task = make_task("F1-0001")
    scored = apply_prune(task, pruned)
    # Item index 1 is pruned; index 0 survives.
    assert scored == ["The plan is infeasible."]


def test_apply_prune_indexes_original_order():
    task = make_task("F1-0001")
    # Prune index 0; index 1 must survive even though it was second.
    scored = apply_prune(task, {("F1-0001", 0)})
    assert scored == ["A second trip is required."]


# ---------------------------------------------------------------------------
# Scoring + Arm C via contract() only.
# ---------------------------------------------------------------------------


def _log_gen(task_id, arm, output_dict, error=None):
    return {
        "task_id": task_id,
        "arm": arm,
        "config_hash": config_hash(),
        "ts": "2026-07-15T00:00:00Z",
        "reported_model": None if error else PIN,
        "output": None if error else output_dict,
        "error": error,
    }


def test_score_from_log_builds_arm_c_via_contraction():
    """Arm C is the contraction of Arm A's output. A decorative claim (source_ids []) is dropped
    by contract(), so Arm C's asserted set differs from Arm A's — proving C is built, not copied.
    """
    task = make_task("F1-0001")
    # Arm A output: one grounded claim + one decorative claim asserting a must_change item.
    a_output = {
        "claims": [
            {"id": 1, "text": "The deadline is 17:00.", "source_ids": [0]},
            {"id": 2, "text": "The plan is infeasible.", "source_ids": []},  # decorative -> dropped
        ],
        "conclusion": "Overall summary.",
    }
    b_output = out(conclusion="B conclusion", claims=[{"id": 1, "text": "b claim", "source_ids": [0]}])

    # Scalar: make "The plan is infeasible." (a must_change item) entailed by the decorative claim
    # text so Arm A asserts it, but Arm C drops that claim so C no longer asserts it.
    scalar = StubScalar(default=0.0)
    # Arm A asserted set includes the decorative claim text -> entails must_change[0].
    scalar.table[(tuple(sorted(["Overall summary.", "The deadline is 17:00.", "The plan is infeasible."])), "The plan is infeasible.")] = 1.0
    # must_persist[0] "The deadline is 17:00." is asserted by both A and C (grounded claim survives).
    for premset in (
        ["Overall summary.", "The deadline is 17:00.", "The plan is infeasible."],
        # Arm C asserted set (decorative dropped, conclusion re-derived from survivor).
        ["Therefore, The deadline is 17:00.", "The deadline is 17:00."],
    ):
        scalar.table[(tuple(sorted(premset)), "The deadline is 17:00.")] = 1.0

    records = [
        _log_gen("F1-0001", ARM_A, a_output),
        _log_gen("F1-0001", ARM_B, b_output),
    ]
    scores, errors = score_from_log(records, [task], set(), scalar, config_hash())
    by_arm = {s.arm: s for s in scores}
    assert set(by_arm) == {"A", "B", "C"}
    # Arm A asserts must_change[0] (contamination 0.5 over 2 items); Arm C dropped it (0.0).
    assert by_arm["A"].contamination == pytest.approx(0.5)
    assert by_arm["C"].contamination == pytest.approx(0.0)
    # completeness: the grounded persist item survives in both A and C.
    assert by_arm["A"].completeness == pytest.approx(0.5)
    assert by_arm["C"].completeness == pytest.approx(0.5)
    assert errors == {"A": 0, "B": 0, "C": 0}


def test_score_from_log_counts_errors_and_skips_arm_c_when_a_errored():
    task = make_task("F1-0001")
    records = [
        _log_gen("F1-0001", ARM_A, None, error="ProviderError: down"),
        _log_gen("F1-0001", ARM_B, out()),
    ]
    scalar = StubScalar(default=0.0)
    scores, errors = score_from_log(records, [task], set(), scalar, config_hash())
    arms = {s.arm for s in scores}
    assert "A" not in arms  # errored
    assert "C" not in arms  # cannot build C without A
    assert "B" in arms
    assert errors == {"A": 1, "B": 0, "C": 1}


def test_score_from_log_prune_applied_to_scoring():
    """A pruned must_change item is excluded from the scored set, changing contamination."""
    task = make_task("F1-0001")
    # Arm A asserts BOTH must_change items.
    a_output = {
        "claims": [{"id": 1, "text": "The plan is infeasible.", "source_ids": [0]}],
        "conclusion": "A second trip is required.",
    }
    scalar = StubScalar(default=0.0)
    asserted = tuple(sorted(["A second trip is required.", "The plan is infeasible."]))
    scalar.table[(asserted, "The plan is infeasible.")] = 1.0
    scalar.table[(asserted, "A second trip is required.")] = 1.0
    # persist entailed too so score() does not choke on empty completeness numerator handling.
    records = [_log_gen("F1-0001", ARM_A, a_output), _log_gen("F1-0001", ARM_B, out())]

    # Without pruning: contamination = 2/2 = 1.0.
    scores, _ = score_from_log(records, [task], set(), scalar, config_hash())
    assert {s.arm: s for s in scores}["A"].contamination == pytest.approx(1.0)

    # Prune item_index 1 -> only 1 scored item, still asserted -> contamination = 1/1 = 1.0 but
    # the pooled trial count drops from 2 to 1 (the register was applied).
    scores2, _ = score_from_log(records, [task], {("F1-0001", 1)}, scalar, config_hash())
    a2 = {s.arm: s for s in scores2}["A"]
    assert a2.change_total == 1  # one item pruned out of scoring
    assert a2.change_asserted == 1


def test_score_from_log_raises_if_all_change_items_pruned():
    task = make_task("F1-0001")
    records = [_log_gen("F1-0001", ARM_A, out()), _log_gen("F1-0001", ARM_B, out())]
    scalar = StubScalar(default=0.0)
    with pytest.raises(ValueError, match="all must_change items pruned"):
        score_from_log(records, [task], {("F1-0001", 0), ("F1-0001", 1)}, scalar, config_hash())


# ---------------------------------------------------------------------------
# Full run: generation + resumability.
# ---------------------------------------------------------------------------


def _snapshot():
    from closure_harness.run_e5 import FreezeGateSnapshot

    return FreezeGateSnapshot(
        head="feedface",
        origin_main="feedface",
        committed_config_token=config_hash(),
        live_config_hash=config_hash(),
        protocol_path=PROTOCOL_REPO_PATH,
        protocol_sha256="cafe",
        corpus_path=CORPUS_REPO_PATH,
        checked_at="2026-07-15T00:00:00Z",
    )


def test_run_generates_both_arms_and_writes_artifacts(tmp_path):
    task = make_task("F1-0001")
    corpus = tmp_path / "corpus.jsonl"
    write_corpus(corpus, [TASK_RECORD])
    pruned = write_pruned(tmp_path / "pruned.json", [])
    outdir = tmp_path / "out"

    # Two generations expected: (F1-0001, A) then (F1-0001, B).
    provider = StubProvider([out(conclusion="A"), out(conclusion="B")])
    scalar = StubScalar(default=1.0)  # everything entailed -> deterministic scores

    tasks = load_tasks(corpus)
    run(tasks, outdir, corpus, pruned, provider, scalar, _snapshot())

    assert provider.calls == 2
    log = read_log(outdir / "run-log.jsonl")
    assert {(r["task_id"], r["arm"]) for r in log} == {("F1-0001", "A"), ("F1-0001", "B")}
    assert (outdir / "results-summary.json").exists()
    assert (outdir / "VERDICT-numbers.md").exists()
    assert (outdir / "manifest.json").exists()
    assert (outdir / "freeze-gate.json").exists()  # gate snapshot recorded as evidence
    gate_json = json.loads((outdir / "freeze-gate.json").read_text())
    assert gate_json["head"] == "feedface"
    assert gate_json["protocol_sha256"] == "cafe"
    manifest = json.loads((outdir / "manifest.json").read_text())
    assert manifest["config_hash"] == config_hash()
    assert manifest["corpus_sha256"]
    assert manifest["pruned_register_sha256"]
    assert manifest["freeze_gate"]["head"] == "feedface"


def test_run_is_resumable_and_skips_completed(tmp_path):
    task = make_task("F1-0001")
    corpus = tmp_path / "corpus.jsonl"
    write_corpus(corpus, [TASK_RECORD])
    pruned = write_pruned(tmp_path / "pruned.json", [])
    outdir = tmp_path / "out"
    tasks = load_tasks(corpus)
    scalar = StubScalar(default=1.0)

    # First run completes both arms.
    provider1 = StubProvider([out(conclusion="A"), out(conclusion="B")])
    run(tasks, outdir, corpus, pruned, provider1, scalar, _snapshot())
    assert provider1.calls == 2

    # Second run: both (task, arm) keys already present at this config_hash -> zero new calls.
    provider2 = StubProvider([])  # would IndexError if any call were made
    run(tasks, outdir, corpus, pruned, provider2, scalar, _snapshot())
    assert provider2.calls == 0


def test_run_halts_on_model_identity_mismatch(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    write_corpus(corpus, [TASK_RECORD])
    pruned = write_pruned(tmp_path / "pruned.json", [])
    outdir = tmp_path / "out"
    tasks = load_tasks(corpus)
    scalar = StubScalar(default=1.0)

    # Arm A returns a spoofed model id -> generate_row raises ModelIdentityError -> run halts.
    provider = StubProvider([{**out(), "_model": "some-other-model"}])
    with pytest.raises(ModelIdentityError):
        run(tasks, outdir, corpus, pruned, provider, scalar, _snapshot())


# ---------------------------------------------------------------------------
# --score-only.
# ---------------------------------------------------------------------------


def test_score_only_recomputes_without_generation(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    write_corpus(corpus, [TASK_RECORD])
    pruned = write_pruned(tmp_path / "pruned.json", [])
    outdir = tmp_path / "out"
    tasks = load_tasks(corpus)
    scalar = StubScalar(default=1.0)

    # Seed a completed log via a normal run.
    provider = StubProvider([out(conclusion="A"), out(conclusion="B")])
    run(tasks, outdir, corpus, pruned, provider, scalar, _snapshot())

    # Delete derived artifacts; score-only must rebuild them from the log with no provider.
    (outdir / "results-summary.json").unlink()
    (outdir / "VERDICT-numbers.md").unlink()
    summary = run_score_only(tasks, outdir, corpus, pruned, scalar)
    assert (outdir / "results-summary.json").exists()
    assert (outdir / "VERDICT-numbers.md").exists()
    assert summary["config_hash"] == config_hash()


def test_score_only_raises_without_log(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    write_corpus(corpus, [TASK_RECORD])
    pruned = write_pruned(tmp_path / "pruned.json", [])
    tasks = load_tasks(corpus)
    scalar = StubScalar(default=1.0)
    with pytest.raises(FileNotFoundError, match="score-only needs an existing"):
        run_score_only(tasks, tmp_path / "empty", corpus, pruned, scalar)
