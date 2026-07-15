"""
Disjointness check: the ~40 rehearsal prompts vs the spike-20, the pilot-30, and the corpus-200.

Reports, per reference set: any EXACT overlap (must be zero), and the maximum token-set (Jaccard)
similarity between any rehearsal prompt and any prompt in that set, with the argmax pair - the same
contamination metric CORPUS.md § Anti-contamination guarantee uses (a high Jaccard on a shared
generic question-frame with zero shared content words is expected and benign; an exact or
near-exact topical duplicate is not).

Reads the rehearsal prompts from run_rehearsal.PROMPTS, the corpus from ../corpus/candidates.jsonl,
the spike-20 and pilot-30 from their hardcoded lists (mirrored here so this check needs no import
of the pilot/spike modules). Prints a table and writes results/disjointness.json.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from run_rehearsal import PROMPTS

HERE = Path(__file__).resolve().parent
CORPUS_JSONL = HERE.parent / "corpus" / "candidates.jsonl"

# spike-20 (spike/run_spike.py) — mirrored verbatim
SPIKE_20 = [
    "What is the capital of France?",
    "How many continents are there on Earth?",
    "What year did the Apollo 11 mission land on the Moon?",
    "What is the chemical symbol for gold?",
    "Who wrote the play 'Romeo and Juliet'?",
    "What is 17 multiplied by 23?",
    "If a train travels 60 km in 45 minutes, what is its average speed in km/h?",
    "What is the derivative of x^3 with respect to x?",
    "Compute the sum of the first 10 positive integers.",
    "List three primary colors, separated by commas.",
    "Rewrite this sentence in the past tense: 'She walks to the store.'",
    "Translate the word 'hello' into Spanish.",
    "Give a one-word antonym for 'hot'.",
    "Is it going to rain tomorrow?",
    "What should I have for dinner?",
    "Which is better?",
    "What does this mean?",
    "Write the opening line of a mystery novel.",
    "Describe an imaginary color that does not exist.",
    "Invent a name for a new planet and say one thing about it.",
]

# pilot-30 (pilot/run_pilot.py) — mirrored verbatim
PILOT_30 = [
    "What is the capital of Japan?",
    "What is the largest planet in our solar system?",
    "In what year did World War II end?",
    "What is the chemical symbol for sodium?",
    "Who painted the Mona Lisa?",
    "What is the tallest mountain on Earth?",
    "What is 48 divided by 6?",
    "What is the square root of 144?",
    "If a rectangle is 8 cm long and 5 cm wide, what is its area?",
    "What is 15 percent of 200?",
    "What is the next number in the sequence 2, 4, 8, 16?",
    "Solve for x: 3x + 9 = 24.",
    "List the two days of the weekend, separated by commas.",
    "Convert the word 'run' to its past tense.",
    "Write the number forty-two in Roman numerals.",
    "Give the plural form of the word 'child'.",
    "Capitalize every word in this phrase: the quick brown fox.",
    "State the opposite of the direction 'north'.",
    "Should I take the job?",
    "How long will it take?",
    "Where should we go?",
    "Is this a good idea?",
    "What time works for you?",
    "Can you fix it?",
    "Write the first sentence of a science fiction story.",
    "Invent a name for a cozy coffee shop and describe its vibe.",
    "Describe the taste of a fruit that has never existed.",
    "Compose a two-line poem about the ocean at night.",
    "Imagine a new holiday and explain how people celebrate it.",
    "Design a creature that lives in the clouds and describe it.",
]


def tokenset(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def jaccard(a: str, b: str) -> float:
    ta, tb = tokenset(a), tokenset(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def max_similarity(rehearsal: list[str], reference: list[str]) -> dict:
    best = {"jaccard": -1.0, "rehearsal": None, "reference": None}
    exact = []
    ref_set = set(reference)
    for rp in rehearsal:
        if rp in ref_set:
            exact.append(rp)
        for ref in reference:
            j = jaccard(rp, ref)
            if j > best["jaccard"]:
                best = {"jaccard": j, "rehearsal": rp, "reference": ref}
    best["exact_overlaps"] = exact
    best["n_exact_overlaps"] = len(exact)
    return best


def main():
    rehearsal = [p for _, _, p, _ in PROMPTS]
    assert len(set(rehearsal)) == len(rehearsal), "rehearsal set has internal duplicates"

    corpus = [json.loads(l)["prompt"] for l in CORPUS_JSONL.read_text().splitlines() if l.strip()]

    report = {
        "n_rehearsal": len(rehearsal),
        "n_spike": len(SPIKE_20),
        "n_pilot": len(PILOT_30),
        "n_corpus": len(corpus),
        "vs_spike20": max_similarity(rehearsal, SPIKE_20),
        "vs_pilot30": max_similarity(rehearsal, PILOT_30),
        "vs_corpus200": max_similarity(rehearsal, corpus),
    }
    (HERE / "results" / "disjointness.json").write_text(json.dumps(report, indent=2))

    print("=" * 80)
    print(f"DISJOINTNESS — {len(rehearsal)} rehearsal prompts vs spike-20 / pilot-30 / corpus-200")
    print("=" * 80)
    for name, key in [("spike-20", "vs_spike20"), ("pilot-30", "vs_pilot30"),
                      ("corpus-200", "vs_corpus200")]:
        r = report[key]
        print(f"\n{name}:  exact overlaps = {r['n_exact_overlaps']}  "
              f"max Jaccard = {r['jaccard']:.3f}")
        print(f"    rehearsal: {r['rehearsal']!r}")
        print(f"    {name:9s}: {r['reference']!r}")
        if r["exact_overlaps"]:
            print(f"    !!! EXACT OVERLAP: {r['exact_overlaps']}")
    print("\nwrote", HERE / "results" / "disjointness.json")


if __name__ == "__main__":
    main()
