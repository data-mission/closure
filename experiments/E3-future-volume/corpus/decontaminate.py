"""
Decontamination audit: every corpus prompt vs every DISPOSABLE-MANIFEST prompt.

CONTAMINATION STANDARD (calibrated to REHEARSAL.md's own disjointness stance, which ACCEPTED
Jaccard 0.80 for 'What is 9 times 8?' vs 'What is 9 times 9?' because "every pair differs in content
and gold"). Item-level leakage -- not frame-sharing -- is what disqualifies a corpus item:

  (E) EXACT match after normalization (case/whitespace/punctuation-insensitive) -- byte-exact or
      case-variant duplicate (e.g. corpus 'What is 15 percent of 200?' == pilot's, corpus
      'largest planet in our Solar System' == pilot's case-variant). ALWAYS contamination.
  (S) SAME-SCENARIO near-dup in an OPEN family (gold is null: enumeration/creative). Because these
      items carry NO gold and the E3 target IS the continuation distribution, reusing the same
      scenario leaks the target even under a verb swap. Flag if content-Jaccard >= 0.55 AND full
      Jaccard >= 0.70 (e.g. corpus 'Imagine a creature that lives in the clouds and describe it'
      vs pilot 'Design a creature that lives in the clouds and describe it').
  (G) SAME-GOLD near-clone in an ANSWERABLE family: full Jaccard >= 0.85 (NEAR-IDENTICAL prose) AND
      the corpus item's gold equals a disposable item's gold (a reworded copy of the same probed
      item). The 0.85 bar is deliberately ABOVE the shared-boilerplate ceiling of structured items
      (e.g. two DIFFERENT 6-entity seating puzzles share the 'N people sit in seats numbered 1..N /
      immediately to the left of / Who sits in seat K' frame at J ~= 0.77 with a colliding single-
      letter gold -- that is the accepted frame effect, NOT contamination, exactly as REHEARSAL
      accepted J=0.80 for '9 times 8' vs '9 times 9'). Different operands/entities with a DIFFERENT
      gold are never flagged.

The generic short-question FRAME alone (function words of 'What is the <X> of <Y>?', or the seating-
puzzle boilerplate) never flags: (E) needs an exact match, (S) needs shared content in an open
family, (G) needs an identical gold AND near-identical prose (>= 0.85).

Returns a list of hits: (corpus_id, corpus_prompt, rule, jaccard, content_jaccard, disp_source,
disp_prompt). Also returns the global max Jaccard for the disjointness report. Imported by
assemble_verify.py; runnable standalone for the audit table.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "DISPOSABLE-MANIFEST.jsonl"
CANDIDATES = HERE / "candidates.jsonl"

# function words that carry the generic-question frame but no topic
_STOP = {
    "a", "an", "the", "is", "are", "was", "were", "of", "in", "on", "to", "and", "or", "what",
    "which", "who", "whom", "how", "many", "much", "does", "do", "did", "there", "it", "its",
    "this", "that", "for", "by", "with", "from", "as", "at", "be", "you", "your", "i", "we",
    "they", "he", "she", "if", "then", "than", "will", "would", "can", "could", "not", "no",
    "yes", "one", "two", "some", "any", "each", "give", "state", "write", "name", "list",
    "compute", "find", "answer",
}


def _norm_exact(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _tokset(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def _content(s: str) -> set[str]:
    return {t for t in _tokset(s) if t not in _STOP}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def load_disposable():
    return [json.loads(l) for l in MANIFEST.read_text().splitlines() if l.strip()]


def load_corpus(rows=None):
    if rows is not None:
        return rows
    return [json.loads(l) for l in CANDIDATES.read_text().splitlines() if l.strip()]


def _norm_gold(g):
    if g is None:
        return None
    return re.sub(r"[^a-z0-9]+", "", str(g).lower())


def audit(corpus_rows=None):
    disp = load_disposable()
    disp_pre = [(_norm_exact(d["prompt"]), _tokset(d["prompt"]), _content(d["prompt"]),
                 _norm_gold(d.get("gold")), d) for d in disp]
    corpus = load_corpus(corpus_rows)
    hits = []
    global_max_j = 0.0
    global_max_pair = None
    for c in corpus:
        cp = c["prompt"]
        cn, ct, cc = _norm_exact(cp), _tokset(cp), _content(cp)
        cgold = _norm_gold(c.get("gold"))
        is_open = c.get("gold") is None
        for dn, dt, dc, dgold, d in disp_pre:
            j = _jaccard(ct, dt)
            if j > global_max_j:
                global_max_j = j
                global_max_pair = (c["id"], cp, d["source"], d["prompt"], j)
            cj = _jaccard(cc, dc)
            rule = None
            if cn == dn:
                rule = "E-exact"
            elif is_open and cj >= 0.55 and j >= 0.70:
                rule = "S-same-scenario"
            elif (not is_open) and j >= 0.85 and cgold is not None and cgold == dgold:
                rule = "G-same-gold"
            if rule:
                hits.append((c["id"], cp, rule, round(j, 3), round(cj, 3), d["source"], d["prompt"]))
    return hits, (global_max_j, global_max_pair)


if __name__ == "__main__":
    hits, (gmax, gpair) = audit()
    print(f"global max token-Jaccard corpus-vs-disposable = {gmax:.3f}")
    if gpair:
        print(f"  argmax: {gpair[0]} {gpair[1]!r}  vs  [{gpair[2]}] {gpair[3]!r}")
    print(f"\n{len(hits)} contamination hit(s) (threshold: exact | J>=0.70 | topic+template):")
    for cid, cp, rule, j, cj, src, dp in sorted(hits):
        print(f"  [{rule:16s} J={j:.2f} cJ={cj:.2f}] {cid}: {cp!r}")
        print(f"        <- [{src}] {dp!r}")
    # unique corpus ids flagged
    ids = sorted({h[0] for h in hits})
    print(f"\n{len(ids)} unique corpus ids flagged: {ids}")
