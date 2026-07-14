"""Pilot runner fixtures (corpus spec §5).

No API, no model download: a stub provider returns canned structured outputs and a stub scalar
returns programmable NLI values, so the flip logic, majority rule, verdict computation,
resumability, and error handling are all exercised on synthetic, hand-computed cases.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from closure_harness.config import CONFIG, config_hash
from closure_harness import pilot
from closure_harness.generate import ModelIdentityError
from closure_harness.pilot import (
    Candidate,
    STATE_WITH_A,
    STATE_WITH_NOT_A,
    _build_prompt,
    _majority_true,
    _state_sources,
    compute_verdicts,
    dry_run_report,
    parse_candidate,
    read_log,
    run_pilot,
)

PIN = CONFIG.generation.model_pin


# ---------------------------------------------------------------------------
# Fixtures: a candidate, a stub provider, a stub scalar.
# ---------------------------------------------------------------------------


def make_candidate(task_id: str = "F1-0001") -> Candidate:
    return Candidate(
        task_id=task_id,
        sources=["S0 text", "A-carrying source text", "S2 text"],
        a_source_id=1,
        not_a_text="NOT-A correction text",
        question="Can it be done?",
        must_change=["The plan is infeasible.", "A second trip is required."],
        must_persist=["The deadline is 17:00.", "The drive is 40 minutes."],
    )


CANDIDATE_RECORD = {
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
}


@dataclass
class StubResponse:
    output: dict
    model: str


class StubProvider:
    """A programmable provider callable.

    Configured with a script: a list of (output_dict | Exception | ModelIdentityError). Each
    call pops the next entry. An Exception entry is raised (simulating a provider/API/parse
    failure that the pilot should log as an error draw); a ModelIdentityError entry is raised to
    verify the pin-mismatch halt. A dict entry is returned wrapped with the pin model id (so the
    identity guard passes) unless a `_model` key overrides it.
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
    """Build a valid 0001 output dict."""
    return {
        "claims": claims or [{"id": 1, "text": "a claim", "source_ids": [0]}],
        "conclusion": conclusion,
    }


# ---------------------------------------------------------------------------
# Prompt construction (spec §5a).
# ---------------------------------------------------------------------------


def test_state_sources_witha_is_verbatim():
    cand = make_candidate()
    assert _state_sources(cand, STATE_WITH_A) == cand.sources


def test_state_sources_withnota_replaces_exactly_the_a_source():
    cand = make_candidate()
    swapped = _state_sources(cand, STATE_WITH_NOT_A)
    # The A source (index 1) is replaced by the ¬A text; every other source is unchanged.
    assert swapped[1] == cand.not_a_text
    assert swapped[0] == cand.sources[0]
    assert swapped[2] == cand.sources[2]
    assert len(swapped) == len(cand.sources)
    # The original A text no longer appears anywhere in the source list.
    assert cand.sources[1] not in swapped


def test_prompt_numbers_documents_and_includes_question():
    cand = make_candidate()
    prompt = _build_prompt(_state_sources(cand, STATE_WITH_A), cand.question)
    assert "[0] S0 text" in prompt
    assert "[1] A-carrying source text" in prompt
    assert "[2] S2 text" in prompt
    assert "Can it be done?" in prompt


def test_prompt_withnota_shows_correction_not_original_a():
    cand = make_candidate()
    prompt = _build_prompt(_state_sources(cand, STATE_WITH_NOT_A), cand.question)
    assert "[1] NOT-A correction text" in prompt
    assert "A-carrying source text" not in prompt


# ---------------------------------------------------------------------------
# parse_candidate.
# ---------------------------------------------------------------------------


def test_parse_candidate_extracts_pilot_fields():
    cand = parse_candidate(CANDIDATE_RECORD)
    assert cand.task_id == "F1-0001"
    assert cand.a_source_id == 1
    assert cand.not_a_text == "NOT-A correction text"
    assert cand.sources == ["S0 text", "A-carrying source text", "S2 text"]
    assert len(cand.must_change) == 2
    assert len(cand.must_persist) == 2


def test_parse_candidate_orders_sources_by_id():
    record = json.loads(json.dumps(CANDIDATE_RECORD))
    # Shuffle the source order; parse must re-sort by id so index == source_id.
    record["sources"] = list(reversed(record["sources"]))
    cand = parse_candidate(record)
    assert cand.sources == ["S0 text", "A-carrying source text", "S2 text"]


# ---------------------------------------------------------------------------
# Majority rule boundary cases (spec §5b).
# ---------------------------------------------------------------------------


def test_majority_true_boundaries():
    assert _majority_true([True, True, True]) is True
    assert _majority_true([True, True, False]) is True  # 2/3 asserted
    assert _majority_true([True, False, False]) is False  # 1/3 asserted
    assert _majority_true([False, False, False]) is False


# ---------------------------------------------------------------------------
# Verdict computation from a synthetic log (spec §5b/§5c).
# ---------------------------------------------------------------------------


def _log_record(task_id, state, draw_index, change_flags, persist_flags, error=None):
    return {
        "task_id": task_id,
        "state": state,
        "draw_index": draw_index,
        "reported_model": None if error else PIN,
        "output": None if error else {"claims": [], "conclusion": "c"},
        "asserted_must_change": None if error else change_flags,
        "asserted_must_persist": None if error else persist_flags,
        "config_hash": config_hash(),
        "ts": "2026-07-14T00:00:00Z",
        "error": error,
    }


def _draws(task_id, state, change_matrix, persist_matrix):
    """Build 3 draws for one state from per-draw flag rows."""
    return [
        _log_record(task_id, state, i, change_matrix[i], persist_matrix[i])
        for i in range(3)
    ]


def test_verdict_pass_when_one_change_item_flips():
    cand = make_candidate()
    # must_change item 0 asserted under A (3/3) and dropped under ¬A (0/3) => flips.
    # item 1 asserted in both (no flip). persist stable in both states.
    records = _draws(
        cand.task_id,
        STATE_WITH_A,
        change_matrix=[[True, True], [True, True], [True, True]],
        persist_matrix=[[True, True]] * 3,
    ) + _draws(
        cand.task_id,
        STATE_WITH_NOT_A,
        change_matrix=[[False, True], [False, True], [False, True]],
        persist_matrix=[[True, True]] * 3,
    )
    verdicts = compute_verdicts(records, {cand.task_id: cand}, config_hash())
    assert len(verdicts) == 1
    v = verdicts[0]
    assert v.verdict == "PASS"
    assert v.n_flipped == 1
    assert v.n_change == 2
    assert v.persist_stability == 1.0
    assert v.flagged_for_qa is False


def test_verdict_exclude_when_nothing_flips():
    cand = make_candidate()
    # Both change items asserted in both states => no flip => EXCLUDE.
    records = _draws(
        cand.task_id,
        STATE_WITH_A,
        change_matrix=[[True, True]] * 3,
        persist_matrix=[[True, True]] * 3,
    ) + _draws(
        cand.task_id,
        STATE_WITH_NOT_A,
        change_matrix=[[True, True]] * 3,
        persist_matrix=[[True, True]] * 3,
    )
    (v,) = compute_verdicts(records, {cand.task_id: cand}, config_hash())
    assert v.verdict == "EXCLUDE"
    assert v.n_flipped == 0
    assert v.exclude_reason == "no must_change item flipped"


def test_verdict_majority_boundary_2of3_vs_1of3():
    cand = make_candidate()
    # Item 0: withA asserted 2/3 (majority yes), withNotA asserted 1/3 (majority no) => flips.
    change_A = [[True, False], [True, False], [False, False]]  # item0: 2/3, item1: 0/3
    change_NotA = [[True, False], [False, False], [False, False]]  # item0: 1/3
    records = _draws(
        cand.task_id, STATE_WITH_A, change_A, [[True, True]] * 3
    ) + _draws(cand.task_id, STATE_WITH_NOT_A, change_NotA, [[True, True]] * 3)
    (v,) = compute_verdicts(records, {cand.task_id: cand}, config_hash())
    assert v.verdict == "PASS"
    assert v.n_flipped == 1


def test_verdict_persist_leak_flags_for_qa():
    cand = make_candidate()
    # A change item flips (PASS), but a persist item changes between states => flagged_for_qa.
    records = _draws(
        cand.task_id,
        STATE_WITH_A,
        change_matrix=[[True, False]] * 3,
        persist_matrix=[[True, True]] * 3,  # both persist asserted under A
    ) + _draws(
        cand.task_id,
        STATE_WITH_NOT_A,
        change_matrix=[[False, False]] * 3,  # item0 dropped => flips
        persist_matrix=[[True, False]] * 3,  # persist item1 dropped under ¬A => leak
    )
    (v,) = compute_verdicts(records, {cand.task_id: cand}, config_hash())
    assert v.verdict == "PASS"
    assert v.n_flipped == 1
    assert v.persist_stability == 0.5
    assert v.flagged_for_qa is True


def test_verdict_ignores_stale_config_hash_records():
    cand = make_candidate()
    stale = _draws(
        cand.task_id, STATE_WITH_A, [[True, True]] * 3, [[True, True]] * 3
    )
    for rec in stale:
        rec["config_hash"] = "STALE"
    # Only stale withA present, no current withNotA => insufficient draws => EXCLUDE.
    (v,) = compute_verdicts(stale, {cand.task_id: cand}, config_hash())
    assert v.verdict == "EXCLUDE"
    assert "insufficient draws" in v.exclude_reason


def test_verdict_error_draws_excluded_from_scoring():
    cand = make_candidate()
    # withA: 2 good draws that assert item0 + 1 error draw. withNotA: item0 dropped.
    withA = [
        _log_record(cand.task_id, STATE_WITH_A, 0, [True, False], [True, True]),
        _log_record(cand.task_id, STATE_WITH_A, 1, [True, False], [True, True]),
        _log_record(cand.task_id, STATE_WITH_A, 2, None, None, error="boom"),
    ]
    withNotA = [
        _log_record(cand.task_id, STATE_WITH_NOT_A, i, [False, False], [True, True])
        for i in range(3)
    ]
    (v,) = compute_verdicts(withA + withNotA, {cand.task_id: cand}, config_hash())
    # item0 asserted 2/2 non-error withA draws (majority yes), dropped withNotA => flips.
    assert v.verdict == "PASS"
    assert v.n_flipped == 1


# ---------------------------------------------------------------------------
# End-to-end run_pilot with stubs (resumability + error handling).
# ---------------------------------------------------------------------------


def _pass_script():
    """6 draws (3 withA + 3 withNotA). withA asserts must_change[0]; withNotA drops it."""
    # Order of draws in run_pilot: state loop (withA, withNotA), draw loop 0..2.
    withA = [out(conclusion="INFEASIBLE") for _ in range(3)]
    withNotA = [out(conclusion="feasible now") for _ in range(3)]
    return withA + withNotA


def _scalar_for_flip():
    # Premise-aware scalar: an "INFEASIBLE" conclusion (withA draws) asserts must_change[0];
    # a "feasible now" conclusion (withNotA draws) asserts neither change item. Both persist
    # items always assert (stable across states), so the flip is clean and no persist leak fires.
    def scalar(premises, claim):
        joined = " ".join(premises)
        if claim == "The plan is infeasible.":
            return 0.9 if "INFEASIBLE" in joined else 0.0
        if claim in ("The deadline is 17:00.", "The drive is 40 minutes."):
            return 0.9  # persist stable in both states
        return 0.0

    return scalar


def test_run_pilot_end_to_end_pass(tmp_path: Path):
    cand = make_candidate()
    provider = StubProvider(_pass_script())
    scalar = _scalar_for_flip()
    verdicts = run_pilot([cand], tmp_path, provider, scalar)
    assert len(verdicts) == 1
    assert verdicts[0].verdict == "PASS"
    # 6 generations happened; log has 6 lines; verdicts file exists.
    log = read_log(tmp_path / "pilot-log.jsonl")
    assert len(log) == 6
    assert provider.calls == 6
    assert (tmp_path / "pilot-verdicts.jsonl").exists()


def test_run_pilot_resumes_and_skips_matching_triples(tmp_path: Path):
    cand = make_candidate()
    # First run: complete.
    run_pilot([cand], tmp_path, StubProvider(_pass_script()), _scalar_for_flip())
    log_before = read_log(tmp_path / "pilot-log.jsonl")
    assert len(log_before) == 6

    # Second run with a provider that raises if called — every triple is already done at the
    # current config_hash, so no draw should execute.
    class ExplodeProvider:
        def __call__(self, prompt):
            raise AssertionError("provider should not be called on a fully-resumed run")

    verdicts = run_pilot([cand], tmp_path, ExplodeProvider(), _scalar_for_flip())
    # Log unchanged (no new draws), verdicts recomputed identically.
    log_after = read_log(tmp_path / "pilot-log.jsonl")
    assert len(log_after) == 6
    assert verdicts[0].verdict == "PASS"


def test_run_pilot_reruns_stale_config_hash(tmp_path: Path):
    cand = make_candidate()
    log_path = tmp_path / "pilot-log.jsonl"
    tmp_path.mkdir(exist_ok=True)
    # Pre-seed the log with 6 draws under a STALE config hash.
    with log_path.open("w", encoding="utf-8") as fh:
        for state in (STATE_WITH_A, STATE_WITH_NOT_A):
            for i in range(3):
                rec = _log_record(cand.task_id, state, i, [True, False], [True, True])
                rec["config_hash"] = "STALE-HASH"
                fh.write(json.dumps(rec) + "\n")

    provider = StubProvider(_pass_script())
    run_pilot([cand], tmp_path, provider, _scalar_for_flip())
    # All 6 stale triples must be re-run (provider called 6 times), appending 6 fresh lines.
    assert provider.calls == 6
    log = read_log(log_path)
    assert len(log) == 12  # 6 stale + 6 fresh
    current = [r for r in log if r["config_hash"] == config_hash()]
    assert len(current) == 6


def test_run_pilot_logs_error_draw_without_crashing(tmp_path: Path):
    cand = make_candidate()
    # First withA draw raises a provider error; the rest succeed.
    script = [RuntimeError("api down")] + [out(conclusion="INFEASIBLE") for _ in range(2)]
    script += [out(conclusion="feasible now") for _ in range(3)]
    provider = StubProvider(script)
    verdicts = run_pilot([cand], tmp_path, provider, _scalar_for_flip())
    log = read_log(tmp_path / "pilot-log.jsonl")
    error_lines = [r for r in log if r["error"] is not None]
    assert len(error_lines) == 1
    assert "api down" in error_lines[0]["error"]
    assert error_lines[0]["asserted_must_change"] is None
    # Two good withA draws assert must_change[0] (majority yes over non-error), withNotA drops it.
    assert verdicts[0].verdict == "PASS"


def test_run_pilot_halts_on_model_identity_mismatch(tmp_path: Path):
    cand = make_candidate()
    # A response reporting a different model triggers the identity guard in generate_row.
    script = [{"claims": [], "conclusion": "c", "_model": "some-other-model"}]
    provider = StubProvider(script)
    with pytest.raises(ModelIdentityError):
        run_pilot([cand], tmp_path, provider, _scalar_for_flip())


# ---------------------------------------------------------------------------
# Dry-run output.
# ---------------------------------------------------------------------------


def test_dry_run_report_reports_plan_and_cost():
    cands = [make_candidate("F1-0001"), make_candidate("F2-0002")]
    report = dry_run_report(cands)
    # 2 tasks x 2 states x 3 draws = 12 generations.
    assert "2 tasks x 2 states x 3 draws = 12 generations" in report
    assert "est TOTAL cost:" in report
    assert config_hash() in report
    assert PIN in report
