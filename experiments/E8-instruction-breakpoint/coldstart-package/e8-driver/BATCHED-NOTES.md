# BATCHED-NOTES — batched MPS scorer + equivalence gate (spec-grade)

Two new files, imports-only, frozen + existing e8-driver files byte-untouched:
- `batched_scorer.py` — scores a filter-gen log by collecting ALL directional (premise,hypothesis)
  pairs across families/states/draws/items/sources into fixed-composition canonical batches.
- `batched_equiv.py` — runs batched vs per-call (gpu_probe.score_all) on the SAME inputs on the SAME
  device; PASS iff zero boolean flips. Exits nonzero on any flip or item-set mismatch.

## Core claim (and what is NOT claimed)

NOT claimed: bit-identical to the banked CPU scores. The frozen path batches PER `__call__` (one
premise-list × one conclusion), bs=16, in pair-append order; `config.py:27-31` states a pair's score
depends on its batch composition because the float path is not bit-invariant to padding, and a
replayer must batch bs=16 in the ORIGINAL request order to reproduce banked scores. The batched scorer
deliberately re-batches ACROSS items (the entire speedup), so its composition differs on purpose.

Claimed: (1) numerically identical in INTENT to the frozen path — same checkpoint/revision, tokenizer
call, entail/contradict index logic, `(entail-contradict+1)/2` scalar, bidirectional average,
max-over-sources, empty→0; only the batch grouping differs. (2) Fixed, documented, reproducible batch
composition (same numbers on same device/build). (3) Its safety for the scored run is proven
EMPIRICALLY by `batched_equiv.py` (boolean-flip gate), never assumed.

## Replicated from nli.py (file:line)

| Choice | Frozen source | Batched replica |
|---|---|---|
| scalar `(P(entail)-P(contradict)+1)/2` | `nli.py:113` | `batched_scorer.py` score_pairs_batched (`scalars = (entail - contradict + 1.0)/2.0`) |
| softmax over logits `dim=-1` | `nli.py:110` | same, `torch.softmax(logits, dim=-1)` |
| entail/contradict idx from `model.config.label2id` (lowercased) | `nli.py:73-75` | reuses `scorer._entail_idx` / `scorer._contradict_idx` (resolved by the frozen `__init__`) |
| tokenizer: `truncation=True, max_length=512, padding=True, return_tensors="pt"` | `nli.py:88-95` | identical kwargs, using the SAME `scorer.tokenizer` instance |
| fail-closed on truncation (raise if any pair > max_length) | `nli.py:99-106` | replicated verbatim per batch; re-measure via `tok(p,h)` (no truncation) |
| bidirectional average of the two directions | `nli.py:123-126` | reassemble: `(dirs[0]+dirs[1])/2.0` |
| multi-source: max over per-source bidir averages | `nli.py:127` | reassemble: max over sources |
| empty sources → 0.0 | `nli.py:119` | reassemble: `n_sources==0 → raw=0.0` |
| max_length / batch_size / checkpoint / revision / device | `config.py:16-36` | `CONFIG.nli` (device via `dataclasses.replace(..., device=...)`) |
| premises = conclusion + surviving claim texts | `outcomes.py:40-49` (`_asserted_text`) | imported and called directly |
| item = each `must_change` conclusion | `filter_stage.py:136` (`enumerate(mc)`) | same enumerate over `task["must_change"]` |
| gen selection `(task_id, filter_state, draw)` + config_hash + not-error + has filter_state | `filter_stage.py:120-123` | `index_gens` copies it exactly (also == gpu_probe.index_gens) |
| family selection = max dose_level per family | `filter_stage.py:41-56` (`top_level_per_family`) | imported and called directly |
| threshold = `CONFIG.outcome.assert_threshold` (0.7) | `config.py:57`, `outcomes.py:54` | `CONFIG.outcome.assert_threshold` |
| MPS deterministic monkeypatch (measured, restored in finally) | `gpu_probe.py:54-84` | `batched_scorer.build_scorer` mirrors it; cpu path builds frozen verbatim |

The frozen NLIScorer is REUSED, not re-implemented: `build_scorer` constructs the real `NLIScorer`
and the batched forward calls `scorer.tokenizer` / `scorer.model` / `scorer._entail_idx` /
`scorer._contradict_idx` / `scorer.config.max_length` / `scorer.device`. The only frozen line not
reused is `_pair_scores`'s per-`__call__` chunk loop (`nli.py:84`) — replaced by the cross-item
canonical chunking, which is the entire point and the exact thing `batched_equiv` measures.

## Canonical ordering (fixes batch composition = fixes reproducibility)

Full directional-pair list is sorted by:

    (family_id, state_rank, draw, item_idx, source_idx, direction)

- `state_rank`: assumption=0, correction=1 (state-name-independent, stable).
- `source_idx`: enumerate index over `_asserted_text(output)` premises (0-based).
- `direction`: 0 = `(source, claim)` (premise=source, hypothesis=claim, `nli.py:123`); 1 = `(claim,
  source)` (swapped, `nli.py:124`).

The sorted list is chunked into fixed `batch_size` (default = frozen `NLIConfig.batch_size` = 16)
batches. Fixed composition ⇒ fixed fp reduction order ⇒ `batched-scores.json` reproduces bit-for-bit
on the same device/build. This is NOT the frozen per-call composition; see above.

## Known numerics caveats

- Padding-induced reduction-order differences between batched and per-call are EXPECTED and are
  exactly what `batched_equiv`'s delta distribution measures. A nonzero max|Δ| is normal; a boolean
  FLIP is the failure condition.
- `--batch-size` other than 16 changes the fixed composition and hence the exact floats; the default
  is the frozen 16. `batched_equiv` should be re-run for any batch_size actually used for scoring.
- `--fp16` (batched_scorer only) defaults OFF and prints a loud warning: fp16 autocast changes
  softmax/reduction precision and is NOT the frozen path; for throughput experiments only.
- Tokenizer padding/truncation SIDE is never set by this code — it inherits whatever the frozen
  `scorer.tokenizer` loaded (checkpoint tokenizer_config). By construction it cannot diverge from the
  frozen path.
- The truncation guard re-measures with `tok(p, h)` (no truncation arg → true length incl. special
  tokens), identical to `nli.py:100`. It fires on genuine over-length only, composition-independent,
  so batched and per-call raise on the SAME pairs.

## Edge cases defended against (hostile self-review)

- Missing gen (hole): `collect_pairs` skips `g is None` exactly as `filter_stage.py:133-135` /
  `gpu_probe.score_all`; item never enters `items`, so no phantom key.
- Deletion trap / empty premises: item recorded with `n_sources=0`, emits no pairs, reassembles to
  `0.0` → `False` (never crosses 0.7), matching `nli.py:119`.
- Chunk off-by-one: `range(0, n, bs)` + `pairs[start:start+bs]`; last chunk `pairs[n-(n%bs):n]`;
  `n_batches=(n+bs-1)//bs` equals the range length.
- Key-set alignment: `collect_pairs` and `gpu_probe.score_all` walk the identical
  `sorted(fams) × (assumption,correction) × range(n_draws) × enumerate(mc)` nesting with the same
  `g is None` skip, so `batched_equiv`'s intersection is the full set; a `key_set_mismatch` is
  surfaced and treated as a hard FAIL.
- Incomplete direction set: `reassemble` raises if a source is missing direction 0 or 1 (never
  silently averages one direction).
- Missing item after scoring: `reassemble` reads `per_item_best[item_key]` for `n_sources>0`; a
  KeyError (a pair went missing) fails loud rather than emitting a wrong scalar.
- JSON key encoding: `(fam,state,draw,item)` joined with `||` (family ids / states contain no `||`),
  round-trips uniquely.

## How to run (on the Mini)

Both tools run from the harness venv so the frozen package imports:

    cd ~/repos/closure/harness && HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
      uv run python -u ~/e8-driver/batched_equiv.py \
        --tasks <tasks.jsonl> --gen-log ~/e8-run/A3-filter/filter-gen.jsonl \
        --out ~/e8-run/A3-filter/batched-equiv.json --n-draws 3 --device mps
    echo "exit=$?"   # nonzero => a boolean flipped => batched scorer NOT safe on this device/corpus

Cheap shard gate first (4 smoke families), then full:

    ... batched_equiv.py ... --families <fam1,fam2,fam3,fam4> --out .../batched-equiv-smoke.json

Only after `batched_equiv` PASSes (zero flips) run the scored pass:

    cd ~/repos/closure/harness && HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
      uv run python -u ~/e8-driver/batched_scorer.py \
        --tasks <tasks.jsonl> --gen-log ~/e8-run/A3-filter/filter-gen.jsonl \
        --out ~/e8-run/A3-filter/batched-scores.json --n-draws 3 --device mps

Output `batched-scores.json`: `scores["<fam>||<state>||<draw>||<item>"] = {raw, assert}` plus a `meta`
block (config_hash, device, batch_size, pair_count, canonical-ordering description, elapsed, pairs/s).

## Discipline note

`batched_equiv` compares batched vs per-call on the SAME device — it isolates BATCH COMPOSITION as the
only variable. It does NOT re-certify device equivalence (batched-MPS vs frozen-CPU): that is
`gpu_probe.py`'s job (the CPU-vs-MPS flip gate, Step Zero of §3a). The full certification chain is:
(1) `gpu_probe` proves per-call MPS == frozen CPU (device gate) → (2) `batched_equiv` proves batched
MPS == per-call MPS (composition gate) → transitively batched MPS == frozen CPU at the boolean level.
Both gates must PASS before the batched scorer's output is used for the registered analysis.
