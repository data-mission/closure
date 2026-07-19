"""E9 incremental per-turn prompt construction (BUILT; exercised by run_e9 dry-run).

Reuses the E8 axis_prompt semantics but reveals corrections ONE TURN AT A TIME and inserts the
compaction step for Arm S. An E9 task is an A3-shaped record (base sources + axis_params.corrections[]
in fixed order) rendered as a k+1-turn interaction:

  turn 0            : base sources + question framing (no correction yet)
  turn 1 .. k       : reveal corrections[t-1]; before revealing (Arm S only) COMPACT the live context
  final answer turn : append the frozen retract-and-revise (Arm-B) instruction, ask for the answer

Both arms see the IDENTICAL corrections in the IDENTICAL order (matched-turn discipline, DESIGN.md §2).
The ONLY difference: Arm S replaces the live context with a model summary before each correction turn;
Arm N retains the full transcript.

This module builds prompt STRINGS only. The multi-turn sequencing, the summarizer model call, and the
final generation are orchestrated in run_e9.py. Every individual model call still goes through the
FROZEN closure_harness.generate.generate_row (via e8-driver/generation_driver.generate_one); nothing
here re-implements an API call.

STATUS: BUILT. Source rendering + Arm-B marker insertion mirror e8-driver/axis_prompt.py; the turn
windowing, compaction slot, and Arm-N restatement path are implemented and exercised by run_e9.py's
dry-run (matched-count invariant verified). The only registration-time step is freezing the summarizer
instruction hash (SUMMARIZER-INSTRUCTION.md).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# The base document/question template is the SAME file the E8 run used (documents={documents},
# question={question}); reused so E9 prompts are constructionally comparable to E8/E5.
# Arm-B marker "\n\nProvide your answer" is the frozen insertion point (axis_prompt.build_prompt).
ARM_B_MARKER = "\n\nProvide your answer"


@dataclass(frozen=True)
class Turn:
    """One turn of an E9 interaction."""
    index: int                 # 0 = framing, 1..k = correction turns, k+1 = answer
    kind: str                  # "framing" | "correction" | "answer"
    revealed_correction: Optional[str]   # the correction text revealed at this turn (kind=="correction")
    is_answer: bool


def corrections_in_order(task: dict) -> list[str]:
    """The k correction texts, fixed order (pure supersession). Reuses the A3 structure exactly:
    axis_params.corrections[] — see e8-driver/axis_prompt.py correction_docs()."""
    ap = task.get("axis_params") or {}
    corr = ap.get("corrections") or []
    return [c["text"] for c in corr if isinstance(c, dict) and "text" in c]


def base_source_texts(task: dict) -> list[str]:
    """Base sources (pre-correction world). Corrections are revealed per-turn, NOT here."""
    return [s["text"] for s in task.get("sources", [])]


def plan_turns(task: dict, k: int) -> list[Turn]:
    """The turn sequence for dose k: 1 framing + k correction turns + 1 answer turn.
    Asserts the task actually carries >= k corrections (matched-family construction guarantee)."""
    corr = corrections_in_order(task)
    if len(corr) < k:
        raise ValueError(
            f"task {task.get('task_id')!r} has {len(corr)} corrections, needs {k} for dose k={k}; "
            "matched-family construction must instantiate every dose level (DESIGN.md §2)."
        )
    turns = [Turn(0, "framing", None, False)]
    for t in range(1, k + 1):
        turns.append(Turn(t, "correction", corr[t - 1], False))
    turns.append(Turn(k + 1, "answer", None, True))
    return turns


def render_documents(doc_texts: list[str]) -> str:
    """Numbered [i] document block, identical formatting to axis_prompt.build_prompt."""
    return "\n".join(f"[{i}] {x}" for i, x in enumerate(doc_texts))


def build_answer_prompt(
    live_context_docs: list[str],
    question: str,
    template: str,
    arm_b_instruction: str,
) -> str:
    """Final-turn prompt: render the CURRENT live context (full transcript for Arm N, or the running
    summary + latest correction for Arm S), append the frozen Arm-B retract-and-revise instruction at
    the frozen marker. Fail-loud if the marker is absent (registration-critical — never emit an
    un-instructed Arm-B answer prompt). Mirrors axis_prompt.build_prompt's Arm-B path exactly."""
    block = render_documents(live_context_docs)
    p = template.format(documents=block, question=question)
    if ARM_B_MARKER not in p:
        raise ValueError(
            f"ARM-B marker {ARM_B_MARKER!r} not in answer prompt; refusing un-instructed Arm-B "
            "(would void the axis)."
        )
    return p.replace(ARM_B_MARKER, f"\n\n{arm_b_instruction}{ARM_B_MARKER}", 1)


def build_summarizer_prompt(
    live_context_docs: list[str],
    summarizer_instruction: str,
    summarizer_template: str,
) -> str:
    """Arm-S compaction prompt: hand the summarizer the CURRENT live context and the pinned summarizer
    instruction. The returned summary REPLACES live_context_docs for the next turn (run_e9.py enforces
    the compression band on the result; an out-of-band summary is re-drawn — DESIGN.md §10)."""
    block = render_documents(live_context_docs)
    return summarizer_template.format(documents=block, instruction=summarizer_instruction)


# ------------------------------------------------------------------ live-context evolution per arm
# Arm N: live context = base sources + every correction revealed so far (full transcript). No compaction.
# Arm S: live context = [running summary] + [the single correction revealed this turn]. The summary is
#        produced by the summarizer from the PREVIOUS live context BEFORE this turn's correction is added.
#
# run_e9.py drives the loop; these two helpers name the exact document list each arm holds at the answer
# turn so the contract is unambiguous.

def arm_n_answer_docs(task: dict, k: int) -> list[str]:
    """Arm N holds everything at answer time: base sources + all k corrections, in order."""
    return base_source_texts(task) + corrections_in_order(task)[:k]


def arm_s_answer_docs(running_summary: str, last_correction: str) -> list[str]:
    """Arm S holds ONLY the running summary (all prior compactions folded in) + the final correction.
    running_summary is produced iteratively by run_e9.py across the k compaction cycles."""
    return [running_summary, last_correction]


# ------------------------------------------------------------------ Arm-N restatement variant (§10 fix)
# The tightest control: Arm N does k+1 generations too (matching Arm S's generation COUNT), but its
# intermediate turns RESTATE the running answer WITHOUT compacting — full transcript retained. This
# isolates the compaction operator from the mere generation-count difference (DESIGN.md §10 second-order
# caveat, adopted by the lead). At each intermediate turn t, the model is asked to restate its current
# running answer given the full transcript so far (sources + corrections[:t]); the final turn answers
# under the Arm-B instruction as usual. The restatement outputs are NOT scored — only the final answer
# is — so the arm's DV is identical to plain Arm N; only the generation count is matched.

def build_restatement_prompt(live_docs: list[str], question: str, template: str) -> str:
    """Intermediate Arm-N turn: full transcript retained, model restates the running answer. No Arm-B
    retract-instruction here (that is appended only at the final answer turn) and no compaction."""
    block = render_documents(live_docs)
    p = template.format(documents=block, question=question)
    # A restatement cue appended at the frozen marker, parallel to build_answer_prompt but non-final.
    if ARM_B_MARKER in p:
        p = p.replace(
            ARM_B_MARKER,
            "\n\nGiven the documents so far, state your current best answer to the question."
            + ARM_B_MARKER,
            1,
        )
    return p


def arm_n_restatement_docs(task: dict, t: int) -> list[str]:
    """Arm-N intermediate turn t: base sources + the first t corrections (full transcript, no compaction)."""
    return base_source_texts(task) + corrections_in_order(task)[:t]
