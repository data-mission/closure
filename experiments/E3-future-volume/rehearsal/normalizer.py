"""
Family-appropriate correctness normalizers — a CONCRETE implementation of the CORPUS.md
§ Labeling protocol scoring rule, written so the rehearsal can actually score greedy answers
against golds and so the places where that spec is too vague to implement can be reported as
findings (the rehearsal's job is to make reality ask the questions).

CORPUS.md § Labeling protocol, verbatim on scoring:

  "A model answer is correct iff it matches `gold` under a family-appropriate normalization:
   `arithmetic` - extract the final number, compare numerically (so `30`, `30.0`, `$30`,
   `37.5`/`37.50` all match their gold); `factual` - case-insensitive match against the gold
   plus obvious equivalents (digit/word forms `8`~`eight`; articles ignored, so `the Sun`~`Sun`);
   `deduction` - normalized match of the answer token (`yes`/`no`/the named entity)."

The three families here map to CORPUS families: kind=="arithmetic" -> numeric; kind=="factual" ->
case/article-insensitive token match; kind=="deduction" -> answer-token match. Each function
returns (is_correct: bool, extracted: str, note: str).

VAGUENESS FINDINGS (surfaced by implementing, reported in REHEARSAL.md § normalizer vagueness):

  V1 (arithmetic) - "extract the final number" is under-specified when the answer restates the
     problem's numbers or shows working ("80 x 0.85 = 68"). Implemented as THE LAST numeric token
     in the response, which is the convention that matches "the final number" but is a choice the
     spec does not pin. A model that appends a unit-year or a second restated quantity after the
     answer would be mis-scored.

  V2 (arithmetic) - numeric tolerance is unstated. `30`==`30.0` is exact; but `37.5`/`37.50` and
     rounding ("about 33") have no tolerance rule. Implemented as exact float equality after
     stripping $ , % and commas; an answer that legitimately rounds is scored wrong. Flagged.

  V3 (factual) - "case-insensitive match ... plus obvious equivalents" does not say token vs
     substring, and "obvious equivalents" is not enumerable. Substring matching is unsafe for
     SINGLE-LETTER golds (chemical symbols O, C, K, W): the letter "o" occurs in almost any
     sentence, so substring match yields false positives. Implemented as WHOLE-TOKEN match (the
     gold, normalized, must equal one answer token, or be a contiguous run of tokens for
     multi-word golds like "Vatican City"). NOTE: the real corpus removed all chemical-symbol
     items, so the real factual family never exercises single-letter golds - this rehearsal does,
     on purpose, to prove the failure mode the spec would otherwise hide.

  V4 (factual) - "obvious equivalents" is open-ended. Implemented: digit<->word for 0..20 and
     articles (a/an/the) stripped. Any equivalence beyond that (synonyms, "USA"=="United States")
     is NOT covered and would need a frozen table the spec does not supply.

  V5 (deduction) - "normalized match of the answer token" is fine for yes/no and single named
     entities, but single-letter entity golds (P, C) collide with the same substring hazard as V3;
     resolved the same way (whole-token match). For numeric deduction golds (e.g. "20") the numeric
     path is reused.
"""

from __future__ import annotations

import re

_ARTICLES = {"a", "an", "the"}
_WORD2DIGIT = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10", "eleven": "11",
    "twelve": "12", "thirteen": "13", "fourteen": "14", "fifteen": "15", "sixteen": "16",
    "seventeen": "17", "eighteen": "18", "nineteen": "19", "twenty": "20",
}
_NUM_RE = re.compile(r"[-+]?\d[\d,]*\.?\d*")


def _tokens(text: str) -> list[str]:
    """Lowercase word tokens with articles stripped and digit-words mapped to digits.

    Punctuation is a delimiter; a token is a maximal run of [a-z0-9]. This is the whole-token
    view both factual and deduction matching use (V3/V5).
    """
    raw = re.findall(r"[a-z0-9]+", text.lower())
    out: list[str] = []
    for t in raw:
        if t in _ARTICLES:
            continue
        out.append(_WORD2DIGIT.get(t, t))
    return out


def _extract_last_number(text: str) -> float | None:
    """The last numeric literal in `text`, $ , % and thousands-commas stripped (V1/V2)."""
    cleaned = text.replace("$", " ").replace("%", " ")
    matches = _NUM_RE.findall(cleaned)
    if not matches:
        return None
    last = matches[-1].replace(",", "")
    try:
        return float(last)
    except ValueError:
        return None


def score_arithmetic(answer: str, gold: str) -> tuple[bool, str, str]:
    """Numeric: last number in the answer vs gold, exact float equality (V1, V2)."""
    got = _extract_last_number(answer)
    want = _extract_last_number(gold)
    if got is None or want is None:
        return False, "" if got is None else str(got), "no-number-parsed"
    return (got == want), str(got), "numeric-exact"


def _gold_tokens(gold: str) -> list[str]:
    return _tokens(gold)


def score_token_match(answer: str, gold: str) -> tuple[bool, str, str]:
    """Whole-token / contiguous-token-run match of gold against the answer (V3, V4, V5).

    If the gold is a single numeric literal, the numeric path is reused so `20`==`20.0` works.
    """
    g = _gold_tokens(gold)
    if not g:
        return False, "", "empty-gold"
    # numeric gold (e.g. deduction "20") -> numeric compare on the answer's last number
    if len(g) == 1 and re.fullmatch(r"[-+]?\d+\.?\d*", g[0]):
        return score_arithmetic(answer, gold)
    a = _tokens(answer)
    if not a:
        return False, "", "empty-answer"
    L = len(g)
    for i in range(len(a) - L + 1):
        if a[i:i + L] == g:
            return True, " ".join(a[i:i + L]), "token-run-match"
    return False, " ".join(a), "no-token-match"


def score(kind: str, answer: str, gold: str) -> tuple[bool, str, str]:
    """Dispatch to the family-appropriate normalizer. `kind` in {arithmetic,factual,deduction}."""
    if kind == "arithmetic":
        return score_arithmetic(answer, gold)
    if kind in ("factual", "deduction"):
        return score_token_match(answer, gold)
    raise ValueError(f"no normalizer for kind {kind!r} (rehearsal families are labeled only)")


if __name__ == "__main__":
    # quick self-check of the golds' normalizers on ideal answers (not a test of the model)
    cases = [
        ("arithmetic", "The answer is 72.", "72", True),
        ("arithmetic", "80 x 0.85 = 68 dollars", "68", True),
        ("arithmetic", "It costs $8.", "8", True),
        ("arithmetic", "about 33", "30", False),
        ("factual", "The capital of Italy is Rome.", "Rome", True),
        ("factual", "The symbol for oxygen is O.", "O", True),
        ("factual", "It is Vatican City.", "Vatican City", True),
        ("factual", "The answer is Sydney.", "Canberra", False),
        ("deduction", "Tom is younger.", "Tom", True),
        ("deduction", "Yes, a robin has feathers.", "yes", True),
        ("deduction", "Switch C is on.", "C", True),
        ("deduction", "A is 20 years old.", "20", True),
    ]
    for kind, ans, gold, expect in cases:
        ok, got, note = score(kind, ans, gold)
        flag = "OK " if ok == expect else "!! "
        print(f"{flag}{kind:11s} gold={gold!r:16s} -> {ok} ({note}) got={got!r}")
