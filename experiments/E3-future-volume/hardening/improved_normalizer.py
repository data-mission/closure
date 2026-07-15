"""
IMPROVED correctness normalizer for the E3 hardening calibration.

This is the rehearsal normalizer (`rehearsal/normalizer.py`) with the five vagueness findings
V1-V5 (documented in REHEARSAL.md and reproduced verbatim in hardening/HARDENING.md) turned into
concrete, frozen rules. Every fix is ADDITIVE to the rehearsal contract: an answer the rehearsal
normalizer scored correct is still scored correct here; the fixes only close the channels that let
the rehearsal FAKE a negative (truncation) or MISS a legitimate equivalent (rounding, per-item
synonyms).

The five fixes (frozen spec text is in HARDENING.md):

  F1 (V1, arithmetic) - ANSWER-MARKER-AWARE final-number extraction + truncation flag.
     "extract the final number" is undefined when the reply is truncated mid-derivation or restates
     working. Fix: (a) the harness raises the answer token cap (>= 640) so a completed CoT is not
     cut; (b) extraction prefers the number that FOLLOWS the last answer marker
     ("=", "answer", "is", "equals", "so", "therefore", "total", ":") over the raw last number, so a
     restated intermediate does not masquerade as the answer; (c) if the reply did NOT hit EOS
     (i.e. it was truncated by the cap), the item is UNCONDITIONALLY returned with `truncated=True`
     and is_correct=False, so the harness EXCLUDES it from the accuracy denominator instead of
     counting it as a genuine wrong answer -- a truncated reply never emitted its final answer, and
     mid-derivation markers ("so length is 12") make any extracted number untrustworthy. A fake
     negative is thus impossible: a truncation is a flagged exclusion, never a scored error. With
     the cap at >= 640, truncation is expected to be rare; when it happens it is disclosed, not
     silently mislabeled.

  F2 (V2, arithmetic) - NUMERIC TOLERANCE. Exact float equality after stripping $ , % is kept as the
     default, and each item MAY carry a `tol` (absolute tolerance). Correct iff
     abs(got - want) <= max(1e-9, tol). Rounding items ("about 33" for 100/3) set tol accordingly.
     Integer golds keep tol=0 -> bit-exact, so hard multiplication cannot be scored right by being
     "close".

  F3 (V3, factual/deduction) - TOKEN-BOUNDARY matching, unchanged in spirit from the rehearsal
     (whole-token / contiguous-token-run match; NEVER substring, so single-letter golds are safe),
     re-stated here as a frozen rule rather than an implementation accident.

  F4 (V4, factual) - PER-ITEM ENUMERATED EQUIVALENCE TABLE. "obvious equivalents" is made explicit
     and closed: each item carries an `accept` list of alternative acceptable gold strings
     (e.g. gold "Bandar Seri Begawan" accepts nothing extra; gold "dong" accepts "Vietnamese dong";
     gold "Vatican City" accepts "Vatican" and "the Vatican"). A match against the gold OR any
     `accept` entry (each via the F3 token-run rule) is correct. Digit<->word (0..20) and article
     stripping are retained globally. The table is authored at construction and frozen; nothing is
     added after scores are seen.

  F5 (V5, deduction) - single-letter / named-entity / numeric deduction golds resolve through the
     same F3 token rule and F2 numeric path; identical to the rehearsal resolution, frozen here.

Public API:
  score(item, answer, eos_hit) -> ScoreResult(is_correct, extracted, note, truncated)
  where `item` is a dict with keys: family (arithmetic|factual|deduction), gold (str),
  optional accept (list[str]), optional tol (float).

The self-check under __main__ is a superset of the rehearsal's 12-case self-check (every rehearsal
case must still pass) plus cases exercising each new fix.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# F4b -- diacritic / native-spelling folding. The model answers factual currency/place questions in
# their native orthography ("Polish złoty", "Vietnamese đồng"); NFKD + combining-mark
# stripping plus a small non-decomposing-letter map fold these to the ASCII gold ("zloty", "dong"),
# so a CORRECT answer written with diacritics is not a fake negative. This closes the same class of
# artifact as F1 (a right answer scored wrong for a formatting reason), on the token path.
_LETTER_FOLD = str.maketrans({
    "ł": "l", "Ł": "L",  # l with stroke (Polish)
    "đ": "d", "Đ": "D",  # d with stroke (Vietnamese/Croatian)
    "ø": "o", "Ø": "O",  # o with stroke
    "ß": "ss",                # sharp s
    "ı": "i",                 # dotless i
})


def _fold(s: str) -> str:
    s = s.translate(_LETTER_FOLD)
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))


# F2b -- spelled-integer recognition (0..20) in the NUMERIC final-answer path, so a correct count
# answered in words ("appears three times", "four vowels") is parsed, not a fake negative. Scoped to
# 0..20 to avoid mis-parsing compound number words; applied to the answer only.
_SPELLED_INT = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6",
    "seven": "7", "eight": "8", "nine": "9", "ten": "10", "eleven": "11", "twelve": "12",
    "thirteen": "13", "fourteen": "14", "fifteen": "15", "sixteen": "16", "seventeen": "17",
    "eighteen": "18", "nineteen": "19", "twenty": "20",
}
_SPELLED_RE = re.compile(r"\b(" + "|".join(_SPELLED_INT) + r")\b", re.IGNORECASE)


def _digitize_words(text: str) -> str:
    return _SPELLED_RE.sub(lambda m: " " + _SPELLED_INT[m.group(1).lower()] + " ", text)


_ARTICLES = {"a", "an", "the"}
_WORD2DIGIT = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10", "eleven": "11",
    "twelve": "12", "thirteen": "13", "fourteen": "14", "fifteen": "15", "sixteen": "16",
    "seventeen": "17", "eighteen": "18", "nineteen": "19", "twenty": "20",
}
_NUM_RE = re.compile(r"[-+]?\d[\d,]*\.?\d*")
# Answer markers, longest first so multi-char markers win. Used to locate the FINAL answer number.
_MARKERS = ["therefore", "answer", "equals", "total", "so", "is", "=", ":"]


@dataclass
class ScoreResult:
    is_correct: bool
    extracted: str
    note: str
    truncated: bool = False


def _tokens(text: str) -> list[str]:
    """Lowercase [a-z0-9] tokens, articles stripped, digit-words 0..20 mapped to digits (F3).

    Text is diacritic-folded first (F4b) so native spellings match ASCII golds.
    """
    raw = re.findall(r"[a-z0-9]+", _fold(text).lower())
    out: list[str] = []
    for t in raw:
        if t in _ARTICLES:
            continue
        out.append(_WORD2DIGIT.get(t, t))
    return out


def _all_numbers(text: str) -> list[str]:
    cleaned = text.replace("$", " ").replace("%", " ")
    return [m.replace(",", "") for m in _NUM_RE.findall(cleaned)]


def _to_float(tok: str) -> float | None:
    try:
        return float(tok)
    except ValueError:
        return None


def _extract_final_number(text: str, prefer: str = "last") -> tuple[float | None, str]:
    """Answer-marker-aware number extraction, family-directional (F1 / F1c).

    prefer="last"  (ARITHMETIC): the answer CONCLUDES a chain of reasoning, so take the number after
        the LAST marker, else the LAST number overall. This is the rehearsal rule.
    prefer="first" (FACTUAL-numeric, F1c): a fact is STATED UP FRONT ("the atomic number of fermium
        is 100. It was discovered in 1952..."), so a trailing discovery-year/group number must NOT
        override it -- take the number after the FIRST marker, else the FIRST number overall. This
        closes a fake-negative channel that scored correct forward-lookup facts wrong.
    Spelled integers 0..20 are digitized first (F2b).
    """
    text = _digitize_words(text)
    low = text.lower()
    if prefer == "first":
        best_pos, best = None, None
        for mk in _MARKERS:
            pos = low.find(mk)
            if pos >= 0 and (best_pos is None or pos < best_pos):
                best_pos = pos
        if best_pos is not None:
            nums = _all_numbers(text[best_pos:])
            if nums and _to_float(nums[0]) is not None:
                return _to_float(nums[0]), "first-after-marker"
        nums_all = _all_numbers(text)
        if nums_all and _to_float(nums_all[0]) is not None:
            return _to_float(nums_all[0]), "first-number"
        return None, "no-number"
    # prefer == "last"
    best_pos = -1
    for mk in _MARKERS:
        pos = low.rfind(mk)
        if pos > best_pos:
            best_pos = pos
    if best_pos >= 0:
        tail = text[best_pos:]
        nums = _all_numbers(tail)
        if nums and _to_float(nums[0]) is not None:
            return _to_float(nums[0]), "after-marker"
    nums_all = _all_numbers(text)
    if nums_all and _to_float(nums_all[-1]) is not None:
        return _to_float(nums_all[-1]), "last-number-fallback"
    return None, "no-number"


def score_arithmetic(item: dict, answer: str, eos_hit: bool, prefer: str = "last") -> ScoreResult:
    """F1 + F2 (+ F1c direction). Numeric compare of gold vs extracted number, per-item tolerance.

    `prefer` selects extraction direction: "last" for arithmetic computation (default), "first" for
    factual-numeric golds routed here from score_token_match (F1c). Truncation guard: a non-EOS
    reply is flagged truncated and excluded, never a scored error (F1).
    """
    gold = item["gold"]
    # F1: a truncated reply never emitted its final answer -> unconditional flagged exclusion.
    if not eos_hit:
        got_t, _ = _extract_final_number(answer, prefer)
        return ScoreResult(False, "" if got_t is None else str(got_t),
                           "truncated-excluded", truncated=True)
    want = _to_float((_all_numbers(gold) or [""])[-1]) if _all_numbers(gold) else None
    got, how = _extract_final_number(answer, prefer)
    tol = float(item.get("tol", 0.0) or 0.0)
    if got is None:
        return ScoreResult(False, "", "no-number-parsed")
    if want is None:
        return ScoreResult(False, str(got), "gold-not-numeric")
    ok = abs(got - want) <= max(1e-9, tol)
    return ScoreResult(ok, str(got), f"numeric[{how}]tol={tol}")


_STANDALONE_UPPER = re.compile(r"(?<![A-Za-z])([A-Z])(?![A-Za-z])")


def _conclusion_letter(text: str) -> str | None:
    """The model's CONCLUSION letter: the first standalone uppercase A-Z after the LAST answer
    marker; if none, the last standalone uppercase A-Z overall. Returns None if the reply contains
    no standalone uppercase letter (e.g. truncated mid-reasoning)."""
    hits = list(_STANDALONE_UPPER.finditer(text))
    if not hits:
        return None
    low = text.lower()
    last_marker = -1
    for mk in _MARKERS:
        last_marker = max(last_marker, low.rfind(mk))
    if last_marker >= 0:
        after = [m for m in hits if m.start() >= last_marker]
        if after:
            return after[0].group(1)
    return hits[-1].group(1)


def _match_token_run(a_tokens: list[str], gold: str) -> bool:
    g = _tokens(gold)
    if not g:
        return False
    L = len(g)
    for i in range(len(a_tokens) - L + 1):
        if a_tokens[i:i + L] == g:
            return True
    return False


def score_token_match(item: dict, answer: str, eos_hit: bool) -> ScoreResult:
    """F3 + F4 + F5. Whole-token-run match of gold OR any per-item `accept` alternative.

    Numeric golds (e.g. deduction "20", atomic number "11") reuse the numeric path so 20==20.0.
    """
    gold = item["gold"]
    fam = item["family"]
    # numeric gold -> numeric path (F5); factual facts are stated up front so extract FIRST (F1c),
    # deduction numeric conclusions come at the end so extract LAST.
    if re.fullmatch(r"[-+]?\d+\.?\d*", str(gold).strip()):
        return score_arithmetic(item, answer, eos_hit,
                                prefer="first" if fam == "factual" else "last")
    # F5b: single-letter gold (deduction entity 'A'..'H', chemical symbol 'O'/'K'). Two hazards:
    # (i) 'A' collides with the article 'a' under article-stripping; (ii) in a long deduction CoT the
    # gold letter appears THROUGHOUT the reasoning, so "does the letter appear" is a false positive
    # (a reply that reasons about A but CONCLUDES B would score correct). Fix: extract the model's
    # CONCLUSION letter -- the standalone uppercase letter after the LAST answer marker, else the
    # last standalone uppercase letter -- and compare CASE-SENSITIVELY to the gold / accept letters.
    gclean = gold.strip()
    if len(gclean) == 1 and gclean.isalpha():
        # F1: a truncated reply never emitted its final conclusion -> excluded (any uppercase letter
        # found would be from mid-reasoning, not the answer).
        if not eos_hit:
            return ScoreResult(False, "", "truncated-excluded", truncated=True)
        concl = _conclusion_letter(answer)
        accept_letters = {gclean} | {c.strip() for c in item.get("accept", [])
                                     if len(c.strip()) == 1 and c.strip().isalpha()}
        if concl is not None and concl in accept_letters:
            return ScoreResult(True, concl, "conclusion-letter-match")
        return ScoreResult(False, concl or answer[-40:], "conclusion-letter-mismatch")
    g = _tokens(gold)
    if not g:
        return ScoreResult(False, "", "empty-gold")
    a = _tokens(answer)
    if not a:
        return ScoreResult(False, "", "empty-answer", truncated=not eos_hit)
    candidates = [gold] + list(item.get("accept", []))
    for cand in candidates:
        if _match_token_run(a, cand):
            # a match anywhere in the reply means the answer WAS emitted, even if later truncated.
            return ScoreResult(True, cand, "token-run-match")
    # no match: if the reply was cut off, the answer may never have been emitted -> exclude (F1).
    if not eos_hit:
        return ScoreResult(False, " ".join(a[-8:]), "truncated-excluded", truncated=True)
    return ScoreResult(False, " ".join(a[-8:]), "no-token-match")


def score(item: dict, answer: str, eos_hit: bool = True) -> ScoreResult:
    """Dispatch on item['family']. family in {arithmetic, factual, deduction}."""
    fam = item["family"]
    if fam == "arithmetic":
        return score_arithmetic(item, answer, eos_hit)
    if fam in ("factual", "deduction"):
        return score_token_match(item, answer, eos_hit)
    raise ValueError(f"no normalizer for family {fam!r}")


if __name__ == "__main__":
    # Superset self-check: every rehearsal case (R*) must still pass, plus one case per new fix.
    cases = [
        # ---- rehearsal parity (R) ----
        ("R", {"family": "arithmetic", "gold": "72"}, "The answer is 72.", True, True),
        ("R", {"family": "arithmetic", "gold": "68"}, "80 x 0.85 = 68 dollars", True, True),
        ("R", {"family": "arithmetic", "gold": "8"}, "It costs $8.", True, True),
        ("R", {"family": "arithmetic", "gold": "30"}, "about 33", True, False),  # no tol -> wrong
        ("R", {"family": "factual", "gold": "Rome"}, "The capital of Italy is Rome.", True, True),
        ("R", {"family": "factual", "gold": "O"}, "The symbol for oxygen is O.", True, True),
        ("R", {"family": "factual", "gold": "Vatican City"}, "It is Vatican City.", True, True),
        ("R", {"family": "factual", "gold": "Canberra"}, "The answer is Sydney.", True, False),
        ("R", {"family": "deduction", "gold": "Tom"}, "Tom is younger.", True, True),
        ("R", {"family": "deduction", "gold": "yes"}, "Yes, a robin has feathers.", True, True),
        ("R", {"family": "deduction", "gold": "C"}, "Switch C is on.", True, True),
        ("R", {"family": "deduction", "gold": "20"}, "A is 20 years old.", True, True),
        # ---- F1 truncation flag: truncated mid-derivation is EXCLUDED, not a wrong answer ----
        ("F1", {"family": "arithmetic", "gold": "72"}, "perimeter 36, width 6, so length is 12",
         False, None),  # expect truncated=True, is_correct False, excluded
        # ---- F1 marker beats trailing restatement ----
        ("F1", {"family": "arithmetic", "gold": "92996"},
         "347*268: ... therefore the answer is 92996. (that was 347 times 268)", True, True),
        # ---- F2 tolerance: rounding accepted when item declares tol ----
        ("F2", {"family": "arithmetic", "gold": "33.33", "tol": 0.5}, "about 33", True, True),
        # ---- F4 per-item accept table ----
        ("F4", {"family": "factual", "gold": "dong", "accept": ["Vietnamese dong"]},
         "The currency is the Vietnamese dong.", True, True),
        ("F4", {"family": "factual", "gold": "Vatican City", "accept": ["Vatican", "the Vatican"]},
         "It's the Vatican.", True, True),
        # ---- F4b diacritic folding: native spelling of a correct answer is not a fake negative ----
        ("F4b", {"family": "factual", "gold": "zloty", "accept": ["Polish zloty"]},
         "The official currency of Poland is the Polish złoty.", True, True),
        ("F4b", {"family": "factual", "gold": "dong", "accept": ["Vietnamese dong"]},
         "The official currency of Vietnam is the Vietnamese đồng (VND).", True, True),
        # ---- F2b spelled integer: a correct count answered in words is parsed ----
        ("F2b", {"family": "arithmetic", "gold": "3"},
         'The letter "r" appears three times.', True, True),
        ("F2b", {"family": "arithmetic", "gold": "5"}, "The word sequoia has five vowels.", True, True),
        # ---- F1c factual-numeric: fact stated up front, trailing year must not override ----
        ("F1c", {"family": "factual", "gold": "100"},
         "The atomic number of fermium is 100. It was discovered in 1952 by Seaborg.", True, True),
        ("F1c", {"family": "factual", "gold": "107"},
         "Bohrium has an atomic number of 76. It has 76 protons.", True, False),  # genuine wrong
        # ---- F5b single-letter ENTITY vs the article 'a' ----
        ("F5b", {"family": "deduction", "gold": "A"}, "Therefore, seat 4 is A.", True, True),
        ("F5b", {"family": "deduction", "gold": "A"},
         "The answer is a puzzle, so seat 3 is B.", True, False),  # article 'a' must NOT match 'A'
        ("F5b", {"family": "deduction", "gold": "A"}, "In both scenarios seat 4 is B.", True, False),
        # gold letter appears in REASONING but conclusion differs -> must be wrong (item-75 pattern)
        ("F5b", {"family": "deduction", "gold": "A"},
         "If A is first then C follows; testing shows the answer is B.", True, False),
    ]
    npass = 0
    for tag, item, ans, eos, expect in cases:
        r = score(item, ans, eos)
        if expect is None:
            ok = r.truncated and not r.is_correct
            verdict = "OK " if ok else "!! "
            print(f"{verdict}[{tag}] TRUNC-EXCLUDE gold={item['gold']!r} -> "
                  f"correct={r.is_correct} truncated={r.truncated} ({r.note})")
        else:
            ok = (r.is_correct == expect)
            verdict = "OK " if ok else "!! "
            print(f"{verdict}[{tag}] gold={item['gold']!r:18s} -> {r.is_correct} "
                  f"({r.note}) got={r.extracted!r}")
        npass += int(ok)
    print(f"\nself-check: {npass}/{len(cases)} passed")
