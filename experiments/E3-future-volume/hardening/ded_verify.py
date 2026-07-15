"""
Brute-force uniqueness verifier for structured deduction puzzles.

A puzzle assigns N named entities to N distinct positions (1..N) -- an ordering / seating / ranking.
Constraints are predicates over the position map `pos: entity -> position`. The verifier enumerates
ALL N! assignments, keeps those satisfying every constraint, and asserts EXACTLY ONE remains (the
gold is otherwise not single-answer-unambiguous). The gold answer is extracted from that unique
assignment by the puzzle's `answer` function. This is the machine re-derivation the corpus labeling
protocol requires for deduction golds -- no deduction gold is asserted; every one is solved and its
uniqueness proven here (and again in assemble_verify.py for the items that enter the corpus).
"""

from __future__ import annotations

from itertools import permutations


def solve(entities, constraints):
    """Return the list of position-maps (entity->1..N) satisfying all constraints."""
    n = len(entities)
    sols = []
    for perm in permutations(range(1, n + 1)):
        pos = dict(zip(entities, perm))
        if all(c(pos) for c in constraints):
            sols.append(pos)
    return sols


def verify_unique(entities, constraints, answer):
    """Assert a unique solution and return (gold_answer, solution_pos_map)."""
    sols = solve(entities, constraints)
    if len(sols) != 1:
        raise AssertionError(f"non-unique ({len(sols)} solutions) for {entities}")
    pos = sols[0]
    return answer(pos), pos


# helper predicate builders (readability at the puzzle sites)
def left_of(a, b):      # a is somewhere left of (smaller position than) b
    return lambda p: p[a] < p[b]


def imm_left(a, b):     # a is immediately left of b
    return lambda p: p[a] + 1 == p[b]


def at(a, k):           # a is at position k
    return lambda p: p[a] == k


def not_at(a, k):       # a is not at position k
    return lambda p: p[a] != k


def adjacent(a, b):     # a and b are next to each other
    return lambda p: abs(p[a] - p[b]) == 1


def who_at(k):          # answer: which entity is at position k
    return lambda p: next(e for e, v in p.items() if v == k)


# --- serializable DSL (for storing constraint specs in JSON, e.g. corpus deduction d4 items) ---
def build_constraints(spec):
    """spec: list of tuples. ('at',e,k) ('nat',e,k) ('imm',a,b) ('lt',a,b) ('adj',a,b)."""
    fns = []
    for t in spec:
        op = t[0]
        if op == "at":
            fns.append(at(t[1], t[2]))
        elif op == "nat":
            fns.append(not_at(t[1], t[2]))
        elif op == "imm":
            fns.append(imm_left(t[1], t[2]))
        elif op == "lt":
            fns.append(left_of(t[1], t[2]))
        elif op == "adj":
            fns.append(adjacent(t[1], t[2]))
        else:
            raise ValueError(f"unknown constraint op {op!r}")
    return fns


def verify_spec(entities, spec, ask_pos):
    """Verify a serialized puzzle: unique solution, return (gold_entity_at_ask_pos, solution)."""
    return verify_unique(entities, build_constraints(spec), who_at(ask_pos))


if __name__ == "__main__":
    # sanity: the round-1 seat puzzle (F,G,H,I,J), gold H at seat 3
    ents = ["F", "G", "H", "I", "J"]
    cons = [at("J", 1), at("G", 5), imm_left("I", "H"), not_at("F", 2), not_at("F", 3)]
    gold, pos = verify_unique(ents, cons, who_at(3))
    print("round-1 seat puzzle -> seat3 =", gold, "| solution", pos)
    assert gold == "H"
    print("ded_verify self-check OK")
