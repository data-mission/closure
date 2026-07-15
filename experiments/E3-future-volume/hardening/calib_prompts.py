"""
DISPOSABLE calibration prompts for the E3 kind-based hardening loop.

*** EVERY PROMPT IN THIS FILE IS THROWAWAY. ***  Marked DISPOSABLE, listed in
corpus/DISPOSABLE-MANIFEST.jsonl, and MUST NEVER appear in, or seed, the real E3 corpus
(corpus/candidates.jsonl). The corpus's d4 hard items are authored SEPARATELY and disjointly; these
calibration prompts only tell us WHICH KINDS produce genuine 7B errors and at what rate.

Context (REHEARSAL.md): Qwen2.5-7B-Instruct-4bit makes ZERO genuine errors on the current corpus
material at any difficulty 1..4 -- hardening by DEGREE fails. Hardening must change KIND. This file
enumerates candidate hard KINDS, grouped, each mapping into one of the three ANSWERABLE corpus
families (arithmetic / factual / deduction). We run Qwen greedy on them (calibrate.py), score with
improved_normalizer, and keep the kinds whose accuracy lands in the 30-80% band while golds stay
single-answer-unambiguous.

Item schema (dict):
  round      : int   -- calibration round this prompt was authored in
  kind       : str   -- fine-grained hard kind (e.g. "arith_mult3x3")
  family     : str   -- corpus family it maps into (arithmetic|factual|deduction)
  prompt     : str   -- exact prompt text
  gold       : str   -- canonical single answer (verified)
  accept     : list  -- (optional) per-item enumerated equivalents (F4)
  tol        : float -- (optional) numeric tolerance (F2); default 0 = bit-exact
  expr       : str   -- (optional) python arithmetic expression; assemble/calibrate assert
                        eval(expr) == float(gold). Present for all numeric-gold items so the gold
                        is machine-recomputed, never asserted (CORPUS.md labeling protocol).
  derivation : str   -- (optional) for deduction: the unique-solution derivation, hand-verified.
  source     : str   -- (optional) for factual: the canonical fact source note.
"""

from __future__ import annotations

# ROUND 1 ---------------------------------------------------------------------------------------
ROUND1 = [
    # ===== KIND arith_mult3x3 -> arithmetic family (3-digit x 3-digit multiplication) =====
    {"round": 1, "kind": "arith_mult3x3", "family": "arithmetic",
     "prompt": "What is 347 times 268?", "gold": "92996", "expr": "347*268"},
    {"round": 1, "kind": "arith_mult3x3", "family": "arithmetic",
     "prompt": "What is 583 times 476?", "gold": "277508", "expr": "583*476"},
    {"round": 1, "kind": "arith_mult3x3", "family": "arithmetic",
     "prompt": "What is 729 times 654?", "gold": "476766", "expr": "729*654"},
    {"round": 1, "kind": "arith_mult3x3", "family": "arithmetic",
     "prompt": "What is 856 times 437?", "gold": "374072", "expr": "856*437"},
    {"round": 1, "kind": "arith_mult3x3", "family": "arithmetic",
     "prompt": "What is 468 times 793?", "gold": "371124", "expr": "468*793"},
    {"round": 1, "kind": "arith_mult3x3", "family": "arithmetic",
     "prompt": "What is 624 times 379?", "gold": "236496", "expr": "624*379"},
    {"round": 1, "kind": "arith_mult3x3", "family": "arithmetic",
     "prompt": "What is 917 times 458?", "gold": "419986", "expr": "917*458"},
    {"round": 1, "kind": "arith_mult3x3", "family": "arithmetic",
     "prompt": "What is 745 times 632?", "gold": "470840", "expr": "745*632"},

    # ===== KIND arith_multistep -> arithmetic family (multi-step word problems with traps) =====
    {"round": 1, "kind": "arith_multistep", "family": "arithmetic",
     "prompt": "A shirt costs 60 dollars. It is first marked up by 25 percent, and then that new "
               "price is discounted by 20 percent. What is the final price in dollars?",
     "gold": "60", "expr": "60*1.25*0.8"},
    {"round": 1, "kind": "arith_multistep", "family": "arithmetic",
     "prompt": "What is 17 percent of 350?", "gold": "59.5", "expr": "0.17*350"},
    {"round": 1, "kind": "arith_multistep", "family": "arithmetic",
     "prompt": "A number increased by 30 percent equals 195. What is the original number?",
     "gold": "150", "expr": "195/1.3"},
    {"round": 1, "kind": "arith_multistep", "family": "arithmetic",
     "prompt": "Compute 144 divided by 12, then add 8, then multiply the result by 7.",
     "gold": "140", "expr": "(144/12+8)*7"},
    {"round": 1, "kind": "arith_multistep", "family": "arithmetic",
     "prompt": "A tank is 40 percent full and holds 500 liters when full. After 120 liters are "
               "added, how many liters are in the tank?", "gold": "320", "expr": "0.4*500+120"},
    {"round": 1, "kind": "arith_multistep", "family": "arithmetic",
     "prompt": "Three friends split a bill of 87 dollars equally, and then each adds a 4 dollar "
               "tip. How much does each friend pay in dollars?", "gold": "33", "expr": "87/3+4"},
    {"round": 1, "kind": "arith_multistep", "family": "arithmetic",
     "prompt": "A car travels at 72 kilometers per hour. How many kilometers does it travel in "
               "25 minutes?", "gold": "30", "expr": "72*25/60"},
    {"round": 1, "kind": "arith_multistep", "family": "arithmetic",
     "prompt": "If 5 machines make 5 widgets in 5 minutes, how many minutes do 100 machines take "
               "to make 100 widgets?", "gold": "5", "expr": "5"},

    # ===== KIND letter_count -> arithmetic family (character counting; numeric gold) =====
    {"round": 1, "kind": "letter_count", "family": "arithmetic",
     "prompt": "How many times does the letter r appear in the word strawberry?",
     "gold": "3", "expr": "'strawberry'.count('r')"},
    {"round": 1, "kind": "letter_count", "family": "arithmetic",
     "prompt": "How many times does the letter s appear in the word mississippi?",
     "gold": "4", "expr": "'mississippi'.count('s')"},
    {"round": 1, "kind": "letter_count", "family": "arithmetic",
     "prompt": "How many times does the letter e appear in the word beekeeper?",
     "gold": "5", "expr": "'beekeeper'.count('e')"},
    {"round": 1, "kind": "letter_count", "family": "arithmetic",
     "prompt": "How many times does the letter e appear in the word bookkeeper?",
     "gold": "3", "expr": "'bookkeeper'.count('e')"},
    {"round": 1, "kind": "letter_count", "family": "arithmetic",
     "prompt": "How many times does the letter l appear in the word parallel?",
     "gold": "3", "expr": "'parallel'.count('l')"},
    {"round": 1, "kind": "letter_count", "family": "arithmetic",
     "prompt": "How many letters are in the word onomatopoeia?",
     "gold": "12", "expr": "len('onomatopoeia')"},
    {"round": 1, "kind": "letter_count", "family": "arithmetic",
     "prompt": "How many times does the letter i appear in the word indivisibility?",
     "gold": "6", "expr": "'indivisibility'.count('i')"},
    {"round": 1, "kind": "letter_count", "family": "arithmetic",
     "prompt": "How many vowels are in the word sequoia?",
     "gold": "5", "expr": "sum('sequoia'.count(v) for v in 'aeiou')"},

    # ===== KIND unit_convert -> arithmetic family (unit conversions with traps) =====
    {"round": 1, "kind": "unit_convert", "family": "arithmetic",
     "prompt": "How many square feet are in a square yard?", "gold": "9", "expr": "3**2"},
    {"round": 1, "kind": "unit_convert", "family": "arithmetic",
     "prompt": "How many cubic inches are in a cubic foot?", "gold": "1728", "expr": "12**3"},
    {"round": 1, "kind": "unit_convert", "family": "arithmetic",
     "prompt": "How many ounces are in 3 pounds?", "gold": "48", "expr": "3*16"},
    {"round": 1, "kind": "unit_convert", "family": "arithmetic",
     "prompt": "How many minutes are there in 3.5 hours?", "gold": "210", "expr": "3.5*60"},
    {"round": 1, "kind": "unit_convert", "family": "arithmetic",
     "prompt": "How many seconds are in 2 hours?", "gold": "7200", "expr": "2*3600"},
    {"round": 1, "kind": "unit_convert", "family": "arithmetic",
     "prompt": "How many millimeters are in 4.2 centimeters?", "gold": "42", "expr": "4.2*10"},

    # ===== KIND fact_obscure -> factual family (obscure-tail single-answer facts) =====
    {"round": 1, "kind": "fact_obscure", "family": "factual",
     "prompt": "What is the capital of Bhutan?", "gold": "Thimphu",
     "source": "Bhutan capital = Thimphu"},
    {"round": 1, "kind": "fact_obscure", "family": "factual",
     "prompt": "What is the capital of Suriname?", "gold": "Paramaribo",
     "source": "Suriname capital = Paramaribo"},
    {"round": 1, "kind": "fact_obscure", "family": "factual",
     "prompt": "What is the capital of Kyrgyzstan?", "gold": "Bishkek",
     "source": "Kyrgyzstan capital = Bishkek"},
    {"round": 1, "kind": "fact_obscure", "family": "factual",
     "prompt": "What is the capital of Eritrea?", "gold": "Asmara",
     "source": "Eritrea capital = Asmara"},
    {"round": 1, "kind": "fact_obscure", "family": "factual",
     "prompt": "What is the capital of Brunei?", "gold": "Bandar Seri Begawan",
     "source": "Brunei capital = Bandar Seri Begawan"},
    {"round": 1, "kind": "fact_obscure", "family": "factual",
     "prompt": "What is the capital of Vanuatu?", "gold": "Port Vila", "accept": ["Port-Vila"],
     "source": "Vanuatu capital = Port Vila"},
    {"round": 1, "kind": "fact_obscure", "family": "factual",
     "prompt": "What is the capital of Mongolia?", "gold": "Ulaanbaatar",
     "accept": ["Ulan Bator", "Ulan-Bator"], "source": "Mongolia capital = Ulaanbaatar"},
    {"round": 1, "kind": "fact_obscure", "family": "factual",
     "prompt": "What is the capital of Laos?", "gold": "Vientiane",
     "source": "Laos capital = Vientiane"},
    {"round": 1, "kind": "fact_obscure", "family": "factual",
     "prompt": "What is the capital of Palau?", "gold": "Ngerulmud",
     "source": "Palau capital = Ngerulmud (since 2006, moved from Koror)"},
    {"round": 1, "kind": "fact_obscure", "family": "factual",
     "prompt": "What is the capital of Montenegro?", "gold": "Podgorica",
     "source": "Montenegro capital = Podgorica"},
    {"round": 1, "kind": "fact_obscure", "family": "factual",
     "prompt": "What is the official currency of Vietnam?", "gold": "dong",
     "accept": ["Vietnamese dong"], "source": "Vietnam currency = Vietnamese dong (VND)"},
    {"round": 1, "kind": "fact_obscure", "family": "factual",
     "prompt": "What is the official currency of Poland?", "gold": "zloty",
     "accept": ["Polish zloty"], "source": "Poland currency = zloty (PLN)"},
    {"round": 1, "kind": "fact_obscure", "family": "factual",
     "prompt": "What is the official currency of Thailand?", "gold": "baht",
     "accept": ["Thai baht"], "source": "Thailand currency = baht (THB)"},
    {"round": 1, "kind": "fact_obscure", "family": "factual",
     "prompt": "What is the atomic number of sodium?", "gold": "11", "expr": "11",
     "source": "Sodium (Na) atomic number = 11"},
    {"round": 1, "kind": "fact_obscure", "family": "factual",
     "prompt": "What is the atomic number of gold?", "gold": "79", "expr": "79",
     "source": "Gold (Au) atomic number = 79"},

    # ===== KIND ded_trap -> deduction family (negation traps / 5+ constraints) =====
    {"round": 1, "kind": "ded_trap", "family": "deduction",
     "prompt": "Four friends -- Mia, Noah, Owen, and Pia -- each have a different pet: a cat, a "
               "dog, a fish, or a bird. Mia does not have the cat or the dog. Noah has neither the "
               "fish nor the bird. Owen does not have the cat. Pia has the bird. Who has the cat?",
     "gold": "Noah",
     "derivation": "Pia=bird. Mia not cat/dog, bird taken -> Mia=fish. Noah not fish/bird, fish/"
                   "bird taken -> Noah in {cat,dog}. Owen not cat -> Owen=dog. So Noah=cat. UNIQUE."},
    {"round": 1, "kind": "ded_trap", "family": "deduction",
     "prompt": "Five sprinters A, B, C, D, E finished a race. C finished last. B finished "
               "immediately before A. E finished immediately after A. D finished before B. "
               "Who finished first?",
     "gold": "D",
     "derivation": "C=5. Triple B,A,E consecutive (B=A-1,E=A+1). A in {2,3} (E<=4). A=2->D<1 "
                   "impossible. A=3->B=2,E=4,D<2->D=1. Order D,B,A,E,C. first=D. UNIQUE."},
    {"round": 1, "kind": "ded_trap", "family": "deduction",
     "prompt": "On an island, knights always tell the truth and knaves always lie. You meet two "
               "people, X and Y. X says, 'Y is a knave.' Y says, 'X and I are both knights.' "
               "Is Y a knight or a knave?",
     "gold": "knave",
     "derivation": "If Y knight, Y's claim true -> both knights -> X knight -> X's claim true -> Y "
                   "knave, contradiction. So Y knave; then X's claim (Y knave) true -> X knight. "
                   "Consistent, UNIQUE: Y=knave."},
    {"round": 1, "kind": "ded_trap", "family": "deduction",
     "prompt": "In a row of five houses numbered 1 to 5 from left to right live five people. Ana "
               "is not in house 1. Ben is in house 4. Cara is immediately to the left of Ben. Dan "
               "is in house 1. Who lives in house 3?",
     "gold": "Cara",
     "derivation": "Ben=4, Cara=3 (immediately left of Ben), Dan=1. House 3=Cara regardless of "
                   "Ana/Eve placement in {2,5}. UNIQUE."},
    {"round": 1, "kind": "ded_trap", "family": "deduction",
     "prompt": "Among four boxes -- red, blue, green, and yellow -- exactly one contains a prize. "
               "The prize is not in the red box. The prize is not in the green box. The blue box "
               "is empty. Which box contains the prize?",
     "gold": "yellow",
     "derivation": "Not red, not green, blue empty -> yellow. UNIQUE by elimination."},
    {"round": 1, "kind": "ded_trap", "family": "deduction",
     "prompt": "Four workers -- Tom, Uma, Vic, and Wes -- have different salaries. Tom earns more "
               "than Uma. Vic earns less than Uma. Wes earns more than Tom. Uma does not earn the "
               "least. Who earns the most?",
     "gold": "Wes",
     "derivation": "Wes>Tom>Uma>Vic (Tom>Uma, Vic<Uma, Wes>Tom). Most=Wes. 'Uma not least' is a "
                   "consistent distractor (Vic is least). UNIQUE."},
    {"round": 1, "kind": "ded_trap", "family": "deduction",
     "prompt": "If the day before yesterday was Wednesday, what day will it be the day after "
               "tomorrow?",
     "gold": "Sunday",
     "derivation": "day-before-yesterday=Wed -> today=Fri -> day-after-tomorrow=Sun. UNIQUE."},
    {"round": 1, "kind": "ded_trap", "family": "deduction",
     "prompt": "Five students -- F, G, H, I, J -- sit in seats numbered 1 to 5. J sits in seat 1. "
               "G sits in seat 5. H sits immediately to the right of I. F does not sit in seat 2 "
               "or seat 3. Who sits in seat 3?",
     "gold": "H",
     "derivation": "J=1,G=5. {F,H,I} in {2,3,4}. F not 2/3 -> F=4. (I,H) consecutive in remaining "
                   "{2,3} -> I=2,H=3. Seat 3=H. UNIQUE."},
]

# ROUND 2 ---------------------------------------------------------------------------------------
# Round 1 showed factual (fact_obscure 15/15) and deduction (ded_trap 8/8) at CEILING even at their
# hardest single-answer degree. Round 2 changes the KIND within each family to genuinely break the
# model while golds stay unambiguous:
#   factual  -> fact_reverse : REVERSE element lookup (number -> element) + SI units of tail
#               quantities (weber/henry/siemens/becquerel/katal/gray) -- recall directions and units
#               the model has weaker coverage of than forward capital/currency recall.
#   deduction-> ded_hard     : 5-7 entity seating/ordering puzzles with immediate-adjacency, several
#               left-of relations and negations. Golds MACHINE-DERIVED and uniqueness PROVEN by
#               ded_verify (brute force over all N! assignments) -- see DED2_SPECS below.
#   arithmetic-> more arith_multistep to firm the round-1 rate (n 8 -> 15).

# structured deduction specs: (id, entities, constraint-spec tuples, ask_position, NL prompt).
# gold is computed by ded_verify.verify_spec at import -> never hand-asserted.
DED2_SPECS = [
    ("D1", list("ABCDEF"),
     [("at", "A", 1), ("imm", "B", "C"), ("lt", "D", "B"), ("imm", "E", "F"), ("nat", "D", 2)], 3,
     "Six people -- A, B, C, D, E, and F -- sit in seats numbered 1 to 6 from left to right. A is "
     "in seat 1. B sits immediately to the left of C. D sits somewhere to the left of B. E sits "
     "immediately to the left of F. D is not in seat 2. Who sits in seat 3?"),
    ("D3", list("ABCDEF"),
     [("at", "F", 6), ("imm", "A", "B"), ("nat", "C", 1), ("lt", "D", "A"), ("imm", "C", "D"),
      ("nat", "E", 3)], 4,
     "Six people -- A, B, C, D, E, and F -- sit in seats numbered 1 to 6 from left to right. F is "
     "in seat 6. A sits immediately to the left of B. C is not in seat 1. D sits somewhere to the "
     "left of A. C sits immediately to the left of D. E is not in seat 3. Who sits in seat 4?"),
    ("D4", list("ABCDEF"),
     [("at", "B", 2), ("imm", "D", "E"), ("lt", "A", "D"), ("nat", "C", 6), ("lt", "C", "A"),
      ("imm", "A", "F")], 4,
     "Six people -- A, B, C, D, E, and F -- sit in seats numbered 1 to 6 from left to right. B is "
     "in seat 2. D sits immediately to the left of E. A sits somewhere to the left of D. C is not "
     "in seat 6. C sits somewhere to the left of A. A sits immediately to the left of F. Who sits "
     "in seat 4?"),
    ("D5", list("ABCDE"),
     [("imm", "A", "B"), ("imm", "B", "C"), ("lt", "D", "A"), ("at", "E", 5)], 1,
     "Five people -- A, B, C, D, and E -- sit in seats numbered 1 to 5 from left to right. A sits "
     "immediately to the left of B. B sits immediately to the left of C. D sits somewhere to the "
     "left of A. E is in seat 5. Who sits in seat 1?"),
    ("D7", list("ABCDEFG"),
     [("at", "A", 1), ("imm", "B", "C"), ("lt", "D", "B"), ("imm", "E", "F"), ("lt", "C", "E"),
      ("nat", "G", 7), ("nat", "D", 2)], 4,
     "Seven people -- A, B, C, D, E, F, and G -- sit in seats numbered 1 to 7 from left to right. "
     "A is in seat 1. B sits immediately to the left of C. D sits somewhere to the left of B. E "
     "sits immediately to the left of F. C sits somewhere to the left of E. G is not in seat 7. D "
     "is not in seat 2. Who sits in seat 4?"),
    ("D8", list("ABCDEF"),
     [("at", "A", 3), ("imm", "B", "A"), ("lt", "C", "B"), ("imm", "D", "E"), ("lt", "A", "D"),
      ("nat", "F", 6)], 5,
     "Six people -- A, B, C, D, E, and F -- sit in seats numbered 1 to 6 from left to right. A is "
     "in seat 3. B sits immediately to the left of A. C sits somewhere to the left of B. D sits "
     "immediately to the left of E. A sits somewhere to the left of D. F is not in seat 6. Who "
     "sits in seat 5?"),
    ("D9", list("ABCDE"),
     [("at", "E", 5), ("imm", "A", "B"), ("lt", "C", "A"), ("imm", "D", "C"), ("nat", "C", 1)], 2,
     "Five people -- A, B, C, D, and E -- sit in seats numbered 1 to 5 from left to right. E is in "
     "seat 5. A sits immediately to the left of B. C sits somewhere to the left of A. D sits "
     "immediately to the left of C. C is not in seat 1. Who sits in seat 2?"),
    ("D10", list("ABCDEF"),
     [("at", "A", 1), ("imm", "C", "B"), ("lt", "B", "D"), ("imm", "F", "E"), ("lt", "D", "E"),
      ("nat", "C", 3)], 3,
     "Six people -- A, B, C, D, E, and F -- sit in seats numbered 1 to 6 from left to right. A is "
     "in seat 1. C sits immediately to the left of B. B sits somewhere to the left of D. F sits "
     "immediately to the left of E. D sits somewhere to the left of E. C is not in seat 3. Who "
     "sits in seat 3?"),
]


def _build_ded2():
    from ded_verify import verify_spec
    out = []
    for pid, ents, spec, ask, prompt in DED2_SPECS:
        gold, _sol = verify_spec(ents, spec, ask)  # asserts uniqueness, derives gold
        out.append({"round": 2, "kind": "ded_hard", "family": "deduction", "prompt": prompt,
                    "gold": gold, "ded_spec": {"entities": ents, "spec": spec, "ask": ask},
                    "derivation": f"brute-force unique solution (ded_verify); seat {ask} = {gold}"})
    return out


ROUND2 = [
    # ===== KIND fact_reverse -> factual family (reverse element lookup + tail SI units) =====
    {"round": 2, "kind": "fact_reverse", "family": "factual",
     "prompt": "Which chemical element has atomic number 42?", "gold": "Molybdenum",
     "source": "Z=42 -> Molybdenum (Mo)"},
    {"round": 2, "kind": "fact_reverse", "family": "factual",
     "prompt": "Which chemical element has atomic number 74?", "gold": "Tungsten",
     "accept": ["Wolfram"], "source": "Z=74 -> Tungsten (W)"},
    {"round": 2, "kind": "fact_reverse", "family": "factual",
     "prompt": "Which chemical element has atomic number 33?", "gold": "Arsenic",
     "source": "Z=33 -> Arsenic (As)"},
    {"round": 2, "kind": "fact_reverse", "family": "factual",
     "prompt": "Which chemical element has atomic number 56?", "gold": "Barium",
     "source": "Z=56 -> Barium (Ba)"},
    {"round": 2, "kind": "fact_reverse", "family": "factual",
     "prompt": "Which chemical element has atomic number 47?", "gold": "Silver",
     "source": "Z=47 -> Silver (Ag)"},
    {"round": 2, "kind": "fact_reverse", "family": "factual",
     "prompt": "Which chemical element has atomic number 30?", "gold": "Zinc",
     "source": "Z=30 -> Zinc (Zn)"},
    {"round": 2, "kind": "fact_reverse", "family": "factual",
     "prompt": "What is the SI unit of magnetic flux?", "gold": "weber", "accept": ["Wb"],
     "source": "SI unit of magnetic flux = weber (Wb)"},
    {"round": 2, "kind": "fact_reverse", "family": "factual",
     "prompt": "What is the SI unit of inductance?", "gold": "henry",
     "source": "SI unit of inductance = henry (H)"},
    {"round": 2, "kind": "fact_reverse", "family": "factual",
     "prompt": "What is the SI unit of electrical conductance?", "gold": "siemens",
     "source": "SI unit of conductance = siemens (S)"},
    {"round": 2, "kind": "fact_reverse", "family": "factual",
     "prompt": "What is the SI unit of radioactivity?", "gold": "becquerel", "accept": ["Bq"],
     "source": "SI unit of radioactivity (activity) = becquerel (Bq)"},
    {"round": 2, "kind": "fact_reverse", "family": "factual",
     "prompt": "What is the SI unit of catalytic activity?", "gold": "katal", "accept": ["kat"],
     "source": "SI unit of catalytic activity = katal (kat)"},
    {"round": 2, "kind": "fact_reverse", "family": "factual",
     "prompt": "What is the SI unit of absorbed radiation dose?", "gold": "gray", "accept": ["Gy"],
     "source": "SI unit of absorbed dose = gray (Gy)"},
    {"round": 2, "kind": "fact_reverse", "family": "factual",
     "prompt": "What is the SI unit of capacitance?", "gold": "farad",
     "source": "SI unit of capacitance = farad (F)"},
    {"round": 2, "kind": "fact_reverse", "family": "factual",
     "prompt": "What is the SI unit of pressure?", "gold": "pascal", "accept": ["Pa"],
     "source": "SI unit of pressure = pascal (Pa)"},

    # ===== KIND arith_multistep (round-2 additions -> firm the arithmetic rate) =====
    {"round": 2, "kind": "arith_multistep", "family": "arithmetic",
     "prompt": "A book originally costs 45 dollars. Its price is reduced by 20 percent, and then a "
               "5 dollar coupon is applied. What is the final price in dollars?",
     "gold": "31", "expr": "45*0.8-5"},
    {"round": 2, "kind": "arith_multistep", "family": "arithmetic",
     "prompt": "A worker is paid 18 dollars per hour for the first 40 hours and 27 dollars per hour "
               "for each additional hour. What is the pay for a 46-hour week in dollars?",
     "gold": "882", "expr": "18*40+27*6"},
    {"round": 2, "kind": "arith_multistep", "family": "arithmetic",
     "prompt": "What is 35 percent of 140?", "gold": "49", "expr": "0.35*140"},
    {"round": 2, "kind": "arith_multistep", "family": "arithmetic",
     "prompt": "A rectangle has a perimeter of 46 cm and a length of 14 cm. What is its area in "
               "square centimeters?", "gold": "126", "expr": "(46/2-14)*14"},
    {"round": 2, "kind": "arith_multistep", "family": "arithmetic",
     "prompt": "Sarah buys 3 notebooks at 4 dollars each and 2 pens at 3 dollars each, and pays "
               "with a 20 dollar bill. How much change does she receive in dollars?",
     "gold": "2", "expr": "20-(3*4+2*3)"},
    {"round": 2, "kind": "arith_multistep", "family": "arithmetic",
     "prompt": "A train departs at 9:45 and arrives at 13:20 on the same day. How many minutes "
               "long is the journey?", "gold": "215", "expr": "(13*60+20)-(9*60+45)"},
    {"round": 2, "kind": "arith_multistep", "family": "arithmetic",
     "prompt": "If 8 workers build a wall in 6 days, how many days do 12 workers take to build the "
               "same wall at the same rate?", "gold": "4", "expr": "8*6/12"},
] + _build_ded2()

# ROUND 3 ---------------------------------------------------------------------------------------
# Round 2 showed fact_reverse ALSO near-ceiling (13/14): the model nails reverse element lookup
# (Mo=42, W=74, Ag=47) and tail SI units (weber/becquerel/siemens/gray). The last untested factual
# kind that might break single-answer recall: TRANSURANIC / superheavy element atomic numbers
# (Z=100..118), both directions -- genuinely tail parametric knowledge, still EXACTLY canonical
# (IUPAC-official names; atomic numbers are integers). If even this stays >0.8, factual is
# empirically unbreakable within the unambiguous-single-answer constraint for this model.
ROUND3 = [
    # forward: atomic number of <transuranic element>
    {"round": 3, "kind": "fact_numeric_tail", "family": "factual",
     "prompt": "What is the atomic number of fermium?", "gold": "100", "expr": "100",
     "source": "Fermium (Fm) Z=100"},
    {"round": 3, "kind": "fact_numeric_tail", "family": "factual",
     "prompt": "What is the atomic number of nobelium?", "gold": "102", "expr": "102",
     "source": "Nobelium (No) Z=102"},
    {"round": 3, "kind": "fact_numeric_tail", "family": "factual",
     "prompt": "What is the atomic number of rutherfordium?", "gold": "104", "expr": "104",
     "source": "Rutherfordium (Rf) Z=104"},
    {"round": 3, "kind": "fact_numeric_tail", "family": "factual",
     "prompt": "What is the atomic number of seaborgium?", "gold": "106", "expr": "106",
     "source": "Seaborgium (Sg) Z=106"},
    {"round": 3, "kind": "fact_numeric_tail", "family": "factual",
     "prompt": "What is the atomic number of bohrium?", "gold": "107", "expr": "107",
     "source": "Bohrium (Bh) Z=107"},
    {"round": 3, "kind": "fact_numeric_tail", "family": "factual",
     "prompt": "What is the atomic number of meitnerium?", "gold": "109", "expr": "109",
     "source": "Meitnerium (Mt) Z=109"},
    {"round": 3, "kind": "fact_numeric_tail", "family": "factual",
     "prompt": "What is the atomic number of darmstadtium?", "gold": "110", "expr": "110",
     "source": "Darmstadtium (Ds) Z=110"},
    # reverse: which element has atomic number <N> (superheavy)
    {"round": 3, "kind": "fact_numeric_tail", "family": "factual",
     "prompt": "Which chemical element has atomic number 101?", "gold": "Mendelevium",
     "source": "Z=101 -> Mendelevium (Md)"},
    {"round": 3, "kind": "fact_numeric_tail", "family": "factual",
     "prompt": "Which chemical element has atomic number 103?", "gold": "Lawrencium",
     "source": "Z=103 -> Lawrencium (Lr)"},
    {"round": 3, "kind": "fact_numeric_tail", "family": "factual",
     "prompt": "Which chemical element has atomic number 105?", "gold": "Dubnium",
     "source": "Z=105 -> Dubnium (Db)"},
    {"round": 3, "kind": "fact_numeric_tail", "family": "factual",
     "prompt": "Which chemical element has atomic number 111?", "gold": "Roentgenium",
     "source": "Z=111 -> Roentgenium (Rg)"},
    {"round": 3, "kind": "fact_numeric_tail", "family": "factual",
     "prompt": "Which chemical element has atomic number 113?", "gold": "Nihonium",
     "source": "Z=113 -> Nihonium (Nh)"},
    {"round": 3, "kind": "fact_numeric_tail", "family": "factual",
     "prompt": "Which chemical element has atomic number 115?", "gold": "Moscovium",
     "source": "Z=115 -> Moscovium (Mc)"},
    {"round": 3, "kind": "fact_numeric_tail", "family": "factual",
     "prompt": "Which chemical element has atomic number 118?", "gold": "Oganesson",
     "source": "Z=118 -> Oganesson (Og)"},
]

# ded_harder: 8-entity seating puzzles (7 constraints each) -- longer forced chains than ded_hard,
# to push the model's tracking past its ceiling. Golds machine-derived + uniqueness proven.
_E = list("ABCDEFGH")


def _nl8(spec, ask):
    lines = []
    for t in spec:
        if t[0] == "at":
            lines.append(f"{t[1]} is in seat {t[2]}.")
        elif t[0] == "nat":
            lines.append(f"{t[1]} is not in seat {t[2]}.")
        elif t[0] == "imm":
            lines.append(f"{t[1]} sits immediately to the left of {t[2]}.")
        elif t[0] == "lt":
            lines.append(f"{t[1]} sits somewhere to the left of {t[2]}.")
    return ("Eight people -- A, B, C, D, E, F, G, and H -- sit in seats numbered 1 to 8 from left "
            "to right. " + " ".join(lines) + f" Who sits in seat {ask}?")


DED3_SPECS = [
    (_E, [("at", "A", 1), ("imm", "B", "C"), ("lt", "D", "B"), ("imm", "E", "F"), ("lt", "C", "E"),
          ("nat", "G", 8), ("nat", "D", 2), ("imm", "H", "G")], 4),
    (_E, [("at", "H", 8), ("imm", "A", "B"), ("lt", "C", "A"), ("imm", "D", "E"), ("lt", "B", "D"),
          ("imm", "G", "F"), ("lt", "E", "G"), ("nat", "C", 3)], 5),
    (_E, [("at", "D", 4), ("imm", "A", "B"), ("lt", "C", "A"), ("imm", "E", "F"), ("lt", "F", "G"),
          ("nat", "H", 1), ("lt", "B", "E"), ("imm", "G", "H")], 6),
    (_E, [("at", "C", 1), ("imm", "D", "E"), ("lt", "A", "D"), ("imm", "F", "G"), ("lt", "E", "F"),
          ("imm", "H", "A"), ("lt", "G", "B")], 3),
    (_E, [("at", "B", 1), ("imm", "C", "D"), ("lt", "A", "C"), ("imm", "E", "F"), ("lt", "D", "E"),
          ("imm", "G", "H"), ("lt", "F", "G")], 7),
    (_E, [("at", "A", 8), ("imm", "C", "B"), ("lt", "B", "D"), ("imm", "E", "F"), ("lt", "D", "E"),
          ("imm", "G", "H"), ("lt", "F", "G")], 4),
]


def _build_ded3():
    from ded_verify import verify_spec
    out = []
    for ents, spec, ask in DED3_SPECS:
        gold, _sol = verify_spec(ents, spec, ask)
        out.append({"round": 3, "kind": "ded_harder", "family": "deduction",
                    "prompt": _nl8(spec, ask), "gold": gold,
                    "ded_spec": {"entities": ents, "spec": spec, "ask": ask},
                    "derivation": f"brute-force unique (ded_verify); seat {ask} = {gold}"})
    return out


ROUND3 = ROUND3 + _build_ded3()

ALL_ROUNDS = {1: ROUND1, 2: ROUND2, 3: ROUND3}


def collect(rounds):
    out = []
    for r in rounds:
        out.extend(ALL_ROUNDS[r])
    return out


if __name__ == "__main__":
    # Author-side verification that runs with NO model: recompute every numeric gold from its expr,
    # and assert prompt uniqueness. (Deduction uniqueness is hand-derived in `derivation`.)
    import re
    items = collect(sorted(ALL_ROUNDS))
    seen = set()
    nbad = 0
    for it in items:
        p = it["prompt"]
        assert p not in seen, f"duplicate prompt: {p!r}"
        seen.add(p)
        if "expr" in it:
            got = eval(it["expr"])  # noqa: S307 - author-controlled expressions only
            want = float(re.sub(r"[^0-9.\-]", "", it["gold"]))
            if abs(float(got) - want) > 1e-9:
                print(f"!! GOLD MISMATCH {it['kind']}: expr={it['expr']} -> {got} gold={it['gold']}")
                nbad += 1
    from collections import Counter
    kinds = Counter(it["kind"] for it in items)
    fams = Counter(it["family"] for it in items)
    print(f"round1: {len(items)} disposable prompts, {nbad} gold mismatches")
    print("kinds:", dict(kinds))
    print("families:", dict(fams))
