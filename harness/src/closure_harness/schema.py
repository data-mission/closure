"""0001 structured-output schema, as dataclasses.

{claims: [{id, text, source_ids: [int]}], conclusion: str}

source_ids index into the task's provided source list (0-based). An empty source_ids marks
a structurally decorative claim (0002).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Claim:
    id: int
    text: str
    source_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class Output:
    claims: tuple[Claim, ...]
    conclusion: str


def parse_output(raw: dict) -> Output:
    """Validate a provider dict against the 0001 schema and build an Output.

    Raises ValueError on any schema violation. No coercion beyond int/str typing — a
    malformed row must fail loudly, not be silently repaired.
    """
    if not isinstance(raw, dict):
        raise ValueError("output must be an object")
    if set(raw.keys()) - {"claims", "conclusion"}:
        raise ValueError(f"unexpected keys: {sorted(set(raw.keys()) - {'claims', 'conclusion'})}")
    if "claims" not in raw or "conclusion" not in raw:
        raise ValueError("output requires 'claims' and 'conclusion'")
    conclusion = raw["conclusion"]
    if not isinstance(conclusion, str):
        raise ValueError("conclusion must be a string")
    raw_claims = raw["claims"]
    if not isinstance(raw_claims, list):
        raise ValueError("claims must be a list")
    claims: list[Claim] = []
    seen_ids: set[int] = set()
    for c in raw_claims:
        if not isinstance(c, dict):
            raise ValueError("each claim must be an object")
        if set(c.keys()) - {"id", "text", "source_ids"}:
            raise ValueError(f"unexpected claim keys in {c!r}")
        cid = c.get("id")
        text = c.get("text")
        sids = c.get("source_ids", [])
        if not isinstance(cid, int) or isinstance(cid, bool):
            raise ValueError(f"claim id must be int: {c!r}")
        if cid in seen_ids:
            raise ValueError(f"duplicate claim id: {cid}")
        seen_ids.add(cid)
        if not isinstance(text, str):
            raise ValueError(f"claim text must be str: {c!r}")
        if not isinstance(sids, list) or not all(
            isinstance(s, int) and not isinstance(s, bool) for s in sids
        ):
            raise ValueError(f"source_ids must be a list of ints: {c!r}")
        claims.append(Claim(id=cid, text=text, source_ids=tuple(sids)))
    return Output(claims=tuple(claims), conclusion=conclusion)
