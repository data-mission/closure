"""Per-axis prompt construction: CORRECTION state vs ASSUMPTION (A) state.

The A-dependency filter (task #24 prep) needs, per family top-level record, two prompt states:
  - CORRECTION state = the normal registered prompt (all correction documents present);
  - ASSUMPTION (A) state = the same prompt with the CORRECTION documents WITHHELD, so the model
    reasons in the pre-correction world.

"Correction documents" are identified per axis from the corpus structure (confirmed against the
real corpora; the withhold rules are recorded in the filter report's ruling_confirmations block):

  A1 (depth):            the appended `not_A_evidence` document (E5 mirror). A-state withholds it.
  A3 (corrections):      ALL of `axis_params.corrections[]`, appended as documents. `not_A_evidence`
                         mirrors corrections[0] for E5 compat at C1, but at C2/C3 there are MORE
                         corrections that are NOT in `sources` and NOT all in `not_A_evidence` —
                         so the CORRECTION prompt must append every corrections[] text, and the
                         A-state withholds all of them. (This also fixes a latent bug: appending
                         only not_A_evidence under-specifies A3 at dose>1.)
  A2 (scoped-exception): the SOURCE documents whose ids are in
                         `axis_params.scoped_exceptions[].source_id` — these are the case-specific
                         endorsements. A-state DROPS those sources (rule-without-exception world);
                         the CORRECTION state includes all sources (nothing appended — A2 has no
                         not_A_evidence).

Fallback for an E5-shaped record (no axis field): treat `not_A_evidence` (if present) as the sole
correction document — verbatim run_arms.py.
"""
from __future__ import annotations

from typing import Optional


def _axis(task: dict) -> Optional[str]:
    return task.get("axis")


def correction_docs(task: dict) -> list[str]:
    """The correction-document TEXTS appended after the base sources in the CORRECTION state.

    (For A2 these are empty — A2 withholds by dropping sources, not by appending; see
    assumption_state_sources.)
    """
    ax = _axis(task)
    if ax == "A2":
        return []  # A2 has no appended correction docs; endorsement is a withheld source
    ap = task.get("axis_params") if isinstance(task.get("axis_params"), dict) else {}
    if ax == "A3":
        corr = ap.get("corrections") if isinstance(ap, dict) else None
        if isinstance(corr, list) and corr:
            return [c["text"] for c in corr if isinstance(c, dict) and "text" in c]
        # fall through to not_A_evidence if corrections[] absent
    # A1, E5-shaped, or A3 fallback: the single not_A_evidence document.
    na = task.get("not_A_evidence")
    if isinstance(na, dict) and "text" in na:
        return [na["text"]]
    return []


def _withheld_source_ids(task: dict) -> set:
    """Source ids to DROP in the A-state (A2 scoped-exception endorsements)."""
    if _axis(task) != "A2":
        return set()
    ap = task.get("axis_params") if isinstance(task.get("axis_params"), dict) else {}
    se = ap.get("scoped_exceptions") if isinstance(ap, dict) else None
    ids = set()
    if isinstance(se, list):
        for e in se:
            if isinstance(e, dict) and e.get("source_id") is not None:
                ids.add(e["source_id"])
    return ids


def _source_texts(task: dict, drop_ids: set) -> list[str]:
    out = []
    for s in task.get("sources", []):
        if s.get("id") in drop_ids:
            continue
        out.append(s["text"])
    return out


def documents_for_state(task: dict, state: str) -> list[str]:
    """The ordered document list (source texts + appended correction texts) for a prompt state.

    state == "correction": all sources + all correction docs (the registered prompt).
    state == "assumption": A2 → sources minus endorsement sources, no appended corrections;
                           A1/A3/E5 → all sources, correction docs WITHHELD.
    """
    if state not in ("correction", "assumption"):
        raise ValueError(f"unknown state {state!r}")
    if state == "assumption":
        drop = _withheld_source_ids(task)          # A2 drops endorsement sources
        return _source_texts(task, drop)            # no correction docs appended
    # correction state: all sources + all correction docs
    return _source_texts(task, set()) + correction_docs(task)


def build_prompt(task: dict, arm: str, arm_b_instruction: str, template: str,
                 state: str = "correction") -> str:
    """Build the prompt for a given axis + state. Fail-loud on the Arm-B marker (instruction is
    appended for EVERY axis, identically — registration-critical; never silently dropped)."""
    docs = documents_for_state(task, state)
    block = "\n".join(f"[{i}] {x}" for i, x in enumerate(docs))
    p = template.format(documents=block, question=task["question"])
    if arm == "B":
        marker = "\n\nProvide your answer"
        if marker not in p:
            raise ValueError(
                f"ARM-B marker {marker!r} not found in prompt for task {task.get('task_id')!r}; "
                "refusing to emit an un-instructed Arm-B prompt (would void the axis)."
            )
        p = p.replace(marker, f"\n\n{arm_b_instruction}{marker}", 1)
    return p
