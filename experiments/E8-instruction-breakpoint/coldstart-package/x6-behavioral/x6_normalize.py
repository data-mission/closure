"""X6 canonical scalar normalizer + hand oracle suite (X6-PROTOTYPE-SPEC §C, guard B).

The anti-template-collision primitive: A_correct/A_wrong are numeric-equality predicates AFTER this
frozen normalizer, never string/shape matches (the repair for A3's "{number} {verdict} {threshold}"
scaffold that cleared NLI 0.7). The normalizer RAISES on an unparseable / word-valued action rather
than guessing — that RAISE is what surfaces the (F,F) diagnostic honestly instead of miscounting it as
a break. Frozen: any change here changes scored booleans, so it is unit-tested with a hand oracle suite
that must stay green (the stats.py oracle-suite discipline, PHASE0 §6a).

No model, no network, pure function. Decimal to avoid float ULP noise at equality.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation


class Unparseable(ValueError):
    """Raised when an emitted action is not a canonicalizable scalar (words, empty, ambiguous).
    A predicate that catches this returns False and the case lands in the (F,F) diagnostic cell —
    never silently True/False as if the action had been understood."""


# words that are allowed to surround a number and are stripped (currency / units, frozen list)
_STRIP_TOKENS = (
    "usd", "dollars", "dollar", "$", "us$", "eur", "€", "gbp", "£",
    "per", "month", "monthly", "/mo", "/month", "year", "annual", "annually", "/yr",
)
_NUM_RE = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?")


def _canon_decimal(d: Decimal) -> Decimal:
    """Drop trailing fractional zeros WITHOUT switching to scientific notation.

    Decimal('12000').normalize() -> Decimal('1.2E+4'), which is value-equal but stringifies
    differently — bad for a canonical form we also print/hash. Instead: if the value is integral,
    quantize to an integer Decimal; else strip only the fractional trailing zeros. Value is
    preserved exactly; the string form is stable ('12000', '12000.5')."""
    if d == d.to_integral_value():
        return d.quantize(Decimal(1))          # -> Decimal('12000')
    return d.normalize()                        # non-integral: '12000.50' -> '12000.5'


def canonical_scalar(s) -> Decimal:
    """Parse an emitted field value to a canonical Decimal.

    Rules (frozen; each covered by the oracle suite):
      - already numeric (int/float/Decimal) -> canonical Decimal, trailing-zero-normalized.
      - string: lowercase, strip the frozen currency/unit tokens and surrounding whitespace,
        then require EXACTLY ONE numeric token; parse it (drop thousands commas). Trailing
        ".00"/".0" normalize away.
      - zero numeric tokens (a word-value like "twelve thousand", or empty) -> RAISE Unparseable.
      - two or more numeric tokens (ambiguous, e.g. a sentence with two numbers) -> RAISE
        Unparseable. NEVER guess which number was meant — ambiguity is the (F,F) signal.
    """
    if isinstance(s, bool):  # bool is an int subclass; a boolean is never a scalar deductible
        raise Unparseable(f"boolean is not a scalar value: {s!r}")
    if isinstance(s, (int, float, Decimal)):
        try:
            return _canon_decimal(Decimal(str(s)))
        except InvalidOperation as e:
            raise Unparseable(f"non-finite numeric: {s!r}") from e
    if not isinstance(s, str):
        raise Unparseable(f"unsupported type {type(s).__name__}: {s!r}")

    t = s.strip().lower()
    for tok in _STRIP_TOKENS:
        t = t.replace(tok, " ")
    nums = _NUM_RE.findall(t)
    if len(nums) == 0:
        raise Unparseable(f"no numeric token in {s!r} (word-value or empty)")
    if len(nums) > 1:
        raise Unparseable(f"ambiguous: {len(nums)} numeric tokens in {s!r} -> {nums}")
    raw = nums[0].replace(",", "")
    try:
        return _canon_decimal(Decimal(raw))
    except InvalidOperation as e:
        raise Unparseable(f"unparseable numeric {raw!r} from {s!r}") from e


def canonical_eq(emitted, target) -> bool:
    """True iff emitted canonicalizes to the same scalar as target. An Unparseable emitted action
    yields False (and, at the harness level, routes the case to the (F,F) diagnostic — see
    x6_verdict). target is authored/derived and MUST canonicalize; if it cannot, that is a
    construction bug and we raise (fail closed, not a silent False)."""
    ct = canonical_scalar(target)  # authored side must parse; raise loudly if not (construction bug)
    try:
        ce = canonical_scalar(emitted)
    except Unparseable:
        return False
    return ce == ct


# ---------------------------------------------------------------- hand oracle suite (must stay green)
_ORACLE = [
    # (input, expected canonical str) OR (input, "RAISE")
    ("$12,000", "12000"),
    ("12000.00", "12000"),
    ("12000.0", "12000"),
    ("USD 12,000", "12000"),
    ("$2,000", "2000"),
    ("$0", "0"),
    ("$12,000 per month", "12000"),
    ("  $12,000.00  ", "12000"),
    (12000, "12000"),
    (12000.0, "12000"),
    (Decimal("12000.00"), "12000"),
    ("$360", "360"),
    ("$1,615", "1615"),
    ("twelve thousand", "RAISE"),       # word-value -> (F,F), never scored
    ("", "RAISE"),                       # empty
    ("the deductible is $12,000 or $2,000", "RAISE"),  # two numbers -> ambiguous
    ("n/a", "RAISE"),
    (True, "RAISE"),                     # boolean is not a scalar
    (None, "RAISE"),
]

_EQ_ORACLE = [
    # (emitted, target, expected canonical_eq)
    ("$12,000", 12000, True),
    ("12000.00", 12000, True),
    ("$2,000", 12000, False),
    ("USD 12,000", "$12,000.00", True),
    ("twelve thousand", 12000, False),   # unparseable emitted -> False (not a crash)
    ("$0", 0, True),
]


def run_oracle_suite() -> dict:
    results = {"scalar": [], "eq": [], "passed": True}
    for inp, exp in _ORACLE:
        try:
            got = str(canonical_scalar(inp))
            ok = (exp != "RAISE") and (got == exp)
            results["scalar"].append({"input": repr(inp), "expected": exp, "got": got, "ok": ok})
        except Unparseable:
            ok = (exp == "RAISE")
            results["scalar"].append({"input": repr(inp), "expected": exp, "got": "RAISE", "ok": ok})
        results["passed"] &= ok
    for emitted, target, exp in _EQ_ORACLE:
        try:
            got = canonical_eq(emitted, target)
            ok = (got == exp)
        except Exception as e:  # noqa: BLE001
            got, ok = f"ERROR:{type(e).__name__}", False
        results["eq"].append({"emitted": repr(emitted), "target": repr(target),
                              "expected": exp, "got": got, "ok": ok})
        results["passed"] &= ok
    return results


if __name__ == "__main__":
    import json
    import sys
    r = run_oracle_suite()
    print(json.dumps(r, indent=2))
    print("ORACLE SUITE:", "PASS" if r["passed"] else "FAIL")
    sys.exit(0 if r["passed"] else 1)
