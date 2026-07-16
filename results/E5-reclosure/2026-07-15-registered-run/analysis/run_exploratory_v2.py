"""E5 exploratory post-hoc analysis — CACHED rewrite (v2).

Same three jobs and same output filenames as run_exploratory.py (v1), same conventions,
same scoring semantics. The only change is a memoized directional-pair NLI cache that
collapses ~170k pair-judgments to ~15-20k unique pairs, cutting the ~24h brute-force run to
~1-3h. Nothing under /Users/vlad/repos/closure is modified; banked artifacts are read-only;
CPU-only, zero API calls.

WHY THE CACHE IS EXACT (ground-truth reading, file:line):
  nli.py:77  NLIScorer._pair_scores(pairs) -> raw model score per directional (premise,
             hypothesis). This is the lowest level where the model enters.
  nli.py:117 NLIScorer.__call__(sources, claim): for each src appends (src,claim) and
             (claim,src); bidir[i]=(fwd+bwd)/2 (line 126); returns max(bidir) (line 127).
  So the ONLY cacheable unit is the directional pair; max/avg above it is pure arithmetic.

  grounding.py:19/24  grounding()/grounding_without() just call scalar(...).
  detector.py:43-44   is_contaminated() calls grounding()/grounding_without() with the FIXED
                      document set `sources` (never the survivor set) -> a claim's flag
                      depends only on (sources, claim, config). SURVIVOR-INDEPENDENT.
  contraction.py:62-72 contract() re-runs _flagged per pass, but every _flagged call resolves
                      to the same (sources, claim) pairs -> full cache hits after cell 1.
  outcomes.py:52      _still_asserts() calls scalar(premises, conclusion).

CachedScalar is a drop-in Scalar (nli.py:20 Protocol). Because every harness function takes
the scalar as an injected dependency, we pass CachedScalar in and get identical results with
caching — no re-implementation of the max/avg/fixpoint combination logic, hence no arithmetic-
reconstruction risk. The exactness gate (job-1 cross-check + explicit sample) is the proof.

BATCHING: CachedScalar reuses the real NLIScorer._pair_scores batched loop (batch_size=16,
the same code that produced the banked scores in run_arms.py). Batched==banked by
construction. We still assert cache-vs-direct exact equality on a >=100-pair sample and abort
on any diff.
"""
import json
import hashlib
import datetime
import pathlib
import sys
import dataclasses
import random

D = pathlib.Path('/Users/vlad/repos/merchloom-2/merchloom/_dev_notes/closure-ir-research/E5-CORPUS')
REPO = pathlib.Path('/Users/vlad/repos/closure')
LOG = D / 'arms-log.jsonl'
SCORES = D / 'arms-scores.jsonl'

from closure_harness.schema import parse_output, Output          # schema.py:27
from closure_harness.contraction import contract, serialize      # contraction.py:50,80
from closure_harness.outcomes import Annotations, score, _still_asserts  # outcomes.py:29,57,52
from closure_harness.stats import two_proportion_ztest           # stats.py:34
from closure_harness.config import config_hash, CONFIG           # config.py:110

CH = config_hash()
ASSERT_T = CONFIG.outcome.assert_threshold  # 0.7 frozen (config.py:52)
TOL = 1e-9

OUT_PER_ITEM = D / 'per-item-scores.jsonl'
OUT_DEPTH = D / 'depth-table.json'
OUT_CREGEN = D / 'c-regeneration-check.json'
OUT_SWEEP = D / 'sensitivity-sweep.json'
OUT_CACHE = D / 'pair-cache.jsonl'


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def log(msg):
    print(f'[{now()}] {msg}', flush=True)


# ============================================================================
# CachedScalar — memoized directional-pair NLI cache
# ============================================================================
class CachedScalar:
    """Drop-in Scalar (nli.py:20) that memoizes directional (premise, hypothesis) pairs.

    __call__ reproduces NLIScorer.__call__ EXACTLY (nli.py:117-127): for each source it uses
    the (src, claim) and (claim, src) directional pairs, averages the two directions, and
    returns the max over sources. The only difference from the base scorer is that raw
    directional scores are served from / stored in a dict keyed by the exact (premise,
    hypothesis) text pair; on a miss all missing pairs for the call are scored in one batched
    _pair_scores() invocation (identical inference path to the base scorer).
    """

    def __init__(self, base):
        self._base = base
        self._cache = {}          # (premise, hypothesis) -> float
        self.n_lookups = 0        # directional-pair lookups requested (naive pair count)
        self.n_misses = 0         # directional pairs actually sent to the model

    def _score_pairs(self, pairs):
        """Return scores for a list of directional (premise, hypothesis) pairs, cached."""
        self.n_lookups += len(pairs)
        missing = []
        seen_missing = set()
        for pr in pairs:
            if pr not in self._cache and pr not in seen_missing:
                missing.append(pr)
                seen_missing.add(pr)
        if missing:
            scored = self._base._pair_scores(missing)
            self.n_misses += len(missing)
            for pr, sc in zip(missing, scored):
                self._cache[pr] = sc
        return [self._cache[pr] for pr in pairs]

    def __call__(self, sources, claim):
        # Identical semantics to NLIScorer.__call__ (nli.py:117-127).
        if not sources:
            return 0.0
        pairs = []
        for src in sources:
            pairs.append((src, claim))   # premise = source, hypothesis = claim
            pairs.append((claim, src))   # swapped direction
        scored = self._score_pairs(pairs)
        bidir = [(scored[i] + scored[i + 1]) / 2.0 for i in range(0, len(scored), 2)]
        return max(bidir)

    def dump(self, path):
        with open(path, 'w') as f:
            for (p, h), v in self._cache.items():
                f.write(json.dumps({'premise': p, 'hypothesis': h, 'score': v},
                                    ensure_ascii=True) + '\n')


# ============================================================================
# EXACTNESS GATE — cache path must equal direct NLIScorer on a random sample
# ============================================================================
def exactness_gate(cached, base, sample_pairs, label, min_n):
    """Assert CachedScalar._score_pairs == base._pair_scores EXACTLY on sample_pairs.

    sample_pairs: list of directional (premise, hypothesis) tuples. Compares the value the
    cache returns (whether hit or freshly computed) against a fresh direct base call, ==.
    """
    if len(sample_pairs) < min_n:
        log(f'  GATE {label}: only {len(sample_pairs)} unique pairs available (< {min_n} '
            f'requested) — checking all of them')
    direct = base._pair_scores(sample_pairs)
    via_cache = cached._score_pairs(sample_pairs)
    diffs = [(i, sample_pairs[i], direct[i], via_cache[i])
             for i in range(len(sample_pairs)) if direct[i] != via_cache[i]]
    log(f'  GATE {label}: {len(sample_pairs)} pairs checked, {len(diffs)} diffs (exact ==)')
    if diffs:
        for i, pr, d, c in diffs[:20]:
            log(f'    DIFF idx={i} direct={d!r} cache={c!r} pair={pr!r}')
        log(f'  GATE {label} FAILED — aborting, cache is NOT exact.')
        sys.exit(2)
    return len(sample_pairs)


# --- inputs (identical to run_arms.py) ---
tasks = [json.loads(l) for l in open(REPO / 'experiments/E5-reclosure/corpus/tasks.jsonl')]
pruned = {}
for it in json.load(open(D / 'pruned-items.json')):
    pruned.setdefault(it['task_id'], set()).add(it['item_index'])


def docs_for(t):
    # identical to run_arms.py:48
    return [s['text'] for s in t['sources']] + [t['not_A_evidence']['text']]


SANITATION = {}


def sanitize(out_dict, ndocs, task_id, arm):
    # identical to run_arms.py:66
    good = [c for c in out_dict['claims'] if all(0 <= i < ndocs for i in c['source_ids'])]
    n_bad = len(out_dict['claims']) - len(good)
    if n_bad:
        SANITATION[(task_id, arm)] = n_bad
    return {'claims': good, 'conclusion': out_dict['conclusion']}


def load_gen():
    """Latest clean row per (task_id, arm), matching config_hash, no error (run_arms.py:104)."""
    gen = {}
    for l in open(LOG):
        r = json.loads(l)
        if r.get('config_hash') == CH and not r.get('error'):
            gen[(r['task_id'], r['arm'])] = r['output']
    return gen


def load_c_sha():
    """Latest logged serialized_sha256 per task for Arm C (last matching row wins)."""
    sha = {}
    for l in open(LOG):
        r = json.loads(l)
        if r.get('arm') == 'C' and r.get('config_hash') == CH and not r.get('error'):
            sha[r['task_id']] = r.get('serialized_sha256')
    return sha


def load_scores_index():
    """Latest arms-scores.jsonl row per (task_id, arm) (last matching wins)."""
    idx = {}
    for l in open(SCORES):
        r = json.loads(l)
        if r.get('config_hash') == CH:
            idx[(r['task_id'], r['arm'])] = r
    return idx


def annotations_for(t):
    """Pruned annotation set exactly as run_arms.py phase 3 (run_arms.py:141)."""
    keep = [i for i in range(len(t['must_change'])) if i not in pruned.get(t['task_id'], set())]
    ann = Annotations(
        must_change=tuple(t['must_change'][i] for i in keep),
        must_persist=tuple(t['must_persist']),
    )
    return ann, keep


def sanitized_gen():
    """load_gen() with A/B sanitized (run_arms.py:118-121); C used as logged."""
    gen = load_gen()
    for t in tasks:
        nd = len(docs_for(t))
        for arm in ('A', 'B'):
            gen[(t['task_id'], arm)] = sanitize(gen[(t['task_id'], arm)], nd, t['task_id'], arm)
    return gen


# ============================================================================
# JOB 1 — per-item rescore -> per-item-scores.jsonl + depth-table.json
# ============================================================================
def job1(scalar, gen):
    log('JOB 1 START — per-item rescore')
    scores_idx = load_scores_index()

    per_item_rows = []
    mismatches = []
    depth_agg = {'direct': {a: [0, 0] for a in 'ABC'},
                 'second_order': {a: [0, 0] for a in 'ABC'}}

    for t in tasks:
        tid = t['task_id']
        ann, keep = annotations_for(t)
        depths_kept = [t['must_change_depth'][i] for i in keep]

        for arm in ('A', 'B', 'C'):
            o = parse_output(gen[(tid, arm)])

            n_change_asserted = 0
            for local_i, (concl, depth) in enumerate(zip(ann.must_change, depths_kept)):
                asserted = _still_asserts(scalar, o, concl, ASSERT_T)
                per_item_rows.append({
                    'task_id': tid, 'arm': arm, 'set': 'must_change',
                    'item_index': keep[local_i], 'depth': depth, 'asserted': bool(asserted),
                })
                if asserted:
                    n_change_asserted += 1
                    depth_agg[depth][arm][0] += 1
                depth_agg[depth][arm][1] += 1

            n_persist_asserted = 0
            for local_i, concl in enumerate(ann.must_persist):
                asserted = _still_asserts(scalar, o, concl, ASSERT_T)
                per_item_rows.append({
                    'task_id': tid, 'arm': arm, 'set': 'must_persist',
                    'item_index': local_i, 'depth': None, 'asserted': bool(asserted),
                })
                if asserted:
                    n_persist_asserted += 1

            # CROSS-CHECK against arms-scores.jsonl
            n_change = len(ann.must_change)
            n_persist = len(ann.must_persist)
            my_contam = n_change_asserted / n_change
            my_complete = n_persist_asserted / n_persist
            ref = scores_idx.get((tid, arm))
            if ref is None:
                mismatches.append(f'{tid}/{arm}: no arms-scores.jsonl row found')
                continue
            if abs(my_contam - ref['contamination']) > TOL:
                mismatches.append(
                    f'{tid}/{arm}: contamination mine={my_contam!r} ref={ref["contamination"]!r} '
                    f'(asserted {n_change_asserted}/{n_change})')
            if abs(my_complete - ref['completeness']) > TOL:
                mismatches.append(
                    f'{tid}/{arm}: completeness mine={my_complete!r} ref={ref["completeness"]!r} '
                    f'(asserted {n_persist_asserted}/{n_persist})')
            if round(my_contam * n_change) != ref['contaminated_items']:
                mismatches.append(
                    f'{tid}/{arm}: contaminated_items mine={round(my_contam*n_change)} '
                    f'ref={ref["contaminated_items"]}')
        log(f'  job1 rescored {tid}')

    if mismatches:
        log('JOB 1 ABORT — cross-check mismatches (%d):' % len(mismatches))
        for m in mismatches:
            log('  MISMATCH ' + m)
        log('JOB 1 FAILED — refusing to write per-item / depth artifacts; halting all jobs.')
        sys.exit(2)

    with open(OUT_PER_ITEM, 'w') as f:
        for row in per_item_rows:
            f.write(json.dumps(row, ensure_ascii=True) + '\n')

    depth_table = {'note': ('per-item must_change contamination pooled across families by '
                            'depth tag (must_change_depth); must_persist excluded (no depth).'),
                   'assert_threshold': ASSERT_T, 'config_hash': CH, 'ts': now(),
                   'depths': {}}
    for depth in ('direct', 'second_order'):
        depth_table['depths'][depth] = {}
        for arm in 'ABC':
            contam, trials = depth_agg[depth][arm]
            depth_table['depths'][depth][arm] = {
                'contaminated': contam, 'trials': trials,
                'rate': (contam / trials) if trials else None,
            }
    json.dump(depth_table, open(OUT_DEPTH, 'w'), indent=2)
    log(f'JOB 1 DONE — {len(per_item_rows)} per-item rows, cross-check PASSED (0 mismatches)')
    log(f'  wrote {OUT_PER_ITEM.name}, {OUT_DEPTH.name}')


# ============================================================================
# JOB 2 — Arm-C regeneration check -> c-regeneration-check.json
# ============================================================================
def job2(scalar, gen):
    log('JOB 2 START — Arm-C regeneration check')
    logged_sha = load_c_sha()
    result = {}
    n_match = 0
    mismatched = []
    for t in tasks:
        tid = t['task_id']
        a_out = parse_output(gen[(tid, 'A')])  # sanitized A (run_arms.py:128)
        c_out = contract(scalar, docs_for(t), a_out)  # frozen detector config
        my_sha = hashlib.sha256(serialize(c_out).encode()).hexdigest()
        match = (my_sha == logged_sha.get(tid))
        result[tid] = match
        if match:
            n_match += 1
        else:
            mismatched.append({'task_id': tid, 'logged': logged_sha.get(tid), 'rederived': my_sha})
        log(f'  job2 {tid} {"match" if match else "MISMATCH"}')
    out = {
        'note': 'Re-derived Arm C from sanitized A via contract()+serialize() at frozen '
                'thresholds; sha256 compared to logged serialized_sha256. 60/60 expected.',
        'config_hash': CH, 'ts': now(),
        'n_tasks': len(tasks), 'n_match': n_match,
        'n_mismatch': len(mismatched), 'all_match': n_match == len(tasks),
        'mismatched': mismatched, 'per_task': result,
    }
    json.dump(out, open(OUT_CREGEN, 'w'), indent=2)
    log(f'JOB 2 DONE — {n_match}/{len(tasks)} match; wrote {OUT_CREGEN.name}')


# ============================================================================
# JOB 3 — sensitivity sweep -> sensitivity-sweep.json
# ============================================================================
def _pybool(x):
    # numpy bool -> python bool (json.dump crashes on numpy bool). The v1 main run died here.
    return bool(x)


def _pyfloat(x):
    return float(x)


def job3(scalar, gen):
    log('JOB 3 START — sensitivity sweep')
    floors = CONFIG.detector.grounding_floor_sweep   # (0.65, 0.70, 0.75)
    ceilings = CONFIG.detector.drop_ceiling_sweep     # (0.05, 0.10, 0.15)

    # Fixed B pooled numbers (threshold-independent), matching run_arms.py phase 3.
    b_succ = 0
    b_trials = 0
    b_complete = []
    for t in tasks:
        ann, _ = annotations_for(t)
        o = parse_output(gen[(t['task_id'], 'B')])
        s = score(scalar, o, ann)
        nc = len(ann.must_change)
        b_succ += round(s.contamination * nc)
        b_trials += nc
        b_complete.append(s.completeness)
    b_mean_complete = sum(b_complete) / len(b_complete)
    log(f'  B pooled contamination = {b_succ}/{b_trials}, mean completeness = {b_mean_complete:.6f}')

    cells = {}
    for f in floors:
        for c in ceilings:
            key = f'{f}/{c}'
            det_cfg = dataclasses.replace(CONFIG.detector, grounding_floor=f, drop_ceiling=c)
            c_succ = 0
            c_trials = 0
            c_complete = []
            for t in tasks:
                ann, _ = annotations_for(t)
                a_out = parse_output(gen[(t['task_id'], 'A')])  # sanitized A
                c_out = contract(scalar, docs_for(t), a_out, config=det_cfg)
                s = score(scalar, c_out, ann)  # score with frozen outcome config
                nc = len(ann.must_change)
                c_succ += round(s.contamination * nc)
                c_trials += nc
                c_complete.append(s.completeness)
            c_mean_complete = sum(c_complete) / len(c_complete)
            z = two_proportion_ztest(b_succ, b_trials, c_succ, c_trials)
            cell = {
                'grounding_floor': _pyfloat(f), 'drop_ceiling': _pyfloat(c),
                'c_contaminated': int(c_succ), 'c_trials': int(c_trials),
                'c_contamination_rate': _pyfloat(c_succ / c_trials),
                'c_mean_completeness': _pyfloat(c_mean_complete),
                'b_vs_c_z': _pyfloat(z.z), 'b_vs_c_p_value': _pyfloat(z.p_value),
                'b_vs_c_p_corrected': _pyfloat(z.p_value_corrected),
                'b_vs_c_significant': _pybool(z.significant),
                'is_frozen_point': _pybool(f == 0.70 and c == 0.10),
            }
            # round-trip to catch any residual non-JSON-native type before the real write
            cells[key] = json.loads(json.dumps(cell))
            log(f'  cell {key}: C={c_succ}/{c_trials} '
                f'rate={c_succ/c_trials:.4f} complete={c_mean_complete:.4f} z={z.z:.3f}')

    out = {
        'note': 'Pre-registered grid grounding_floor x drop_ceiling. Frozen point 0.70/0.10 '
                'must reproduce C = 11/107. B pooled numbers fixed (1/107) and threshold-'
                'independent. B-vs-C two-proportion z-test, successes pooled over must_change '
                'items with the pruning register applied.',
        'config_hash': CH, 'ts': now(),
        'assert_threshold': _pyfloat(ASSERT_T),
        'b_pooled': {'contaminated': int(b_succ), 'trials': int(b_trials),
                     'rate': _pyfloat(b_succ / b_trials),
                     'mean_completeness': _pyfloat(b_mean_complete)},
        'cells': cells,
    }
    out = json.loads(json.dumps(out))  # full round-trip guard before writing
    json.dump(out, open(OUT_SWEEP, 'w'), indent=2)
    frozen = cells.get('0.7/0.1')
    log(f'  frozen-point cell 0.7/0.1: C = {frozen["c_contaminated"]}/{frozen["c_trials"]} '
        f'(expected 11/107)')
    log(f'JOB 3 DONE — wrote {OUT_SWEEP.name}')


# ============================================================================
# Cache warm + exactness gate helpers
# ============================================================================
def _collect_all_directional_pairs(gen):
    """Every directional (premise, hypothesis) pair the three jobs will ever request, as a
    de-duplicated list. Used to (a) size naive-vs-unique and (b) draw the gate sample.

    Mirrors the exact call sites:
      - _still_asserts (job1, job3-score): premises = [conclusion, *claim_texts] vs each
        annotated conclusion -> pairs (prem, concl) and (concl, prem).
      - is_contaminated via contract (job2, job3): grounding(full sources) and
        grounding_without(sources minus source_ids) for each claim -> pairs (src, claim.text)
        and (claim.text, src).
    Enumerating the superset is safe: extra pairs only widen the sample, never change results.
    """
    pairs = set()

    def add_call(sources, claim):
        for src in sources:
            pairs.add((src, claim))
            pairs.add((claim, src))

    # outcome-scoring pairs (must_change + must_persist against A/B/C asserted text)
    for t in tasks:
        ann, keep = annotations_for(t)
        for arm in ('A', 'B', 'C'):
            o = parse_output(gen[(t['task_id'], arm)])
            premises = [o.conclusion, *(c.text for c in o.claims)]
            for concl in list(ann.must_change) + list(ann.must_persist):
                add_call(premises, concl)

    # detector pairs (contract over A at every sweep cell; sources fixed, so cell-independent)
    for t in tasks:
        srcs = docs_for(t)
        a_out = parse_output(gen[(t['task_id'], 'A')])
        for c in a_out.claims:
            if not c.source_ids:
                continue
            add_call(list(srcs), c.text)                                   # grounding (full)
            kept = [s for i, s in enumerate(srcs) if i not in set(c.source_ids)]
            add_call(kept, c.text)                                         # grounding_without
    return list(pairs)


def run_smoke(base):
    """First task only, all three job slices, cross-checked + cache-exactness gate."""
    log('SMOKE SLICE — first task, all three jobs, cache-exactness gate')
    gen = sanitized_gen()
    cached = CachedScalar(base)
    t = tasks[0]
    tid = t['task_id']
    ann, keep = annotations_for(t)
    scores_idx = load_scores_index()
    logged_sha = load_c_sha()

    # --- gate: cache path vs direct on a >=100-pair sample drawn from THIS task's pairs ---
    fp = set()

    def add_call(sources, claim):
        for src in sources:
            fp.add((src, claim)); fp.add((claim, src))
    for arm in ('A', 'B', 'C'):
        o = parse_output(gen[(tid, arm)])
        premises = [o.conclusion, *(c.text for c in o.claims)]
        for concl in list(ann.must_change) + list(ann.must_persist):
            add_call(premises, concl)
    srcs = docs_for(t)
    a_out = parse_output(gen[(tid, 'A')])
    for c in a_out.claims:
        if not c.source_ids:
            continue
        add_call(list(srcs), c.text)
        kept = [s for i, s in enumerate(srcs) if i not in set(c.source_ids)]
        add_call(kept, c.text)
    fp = list(fp)
    random.Random(0).shuffle(fp)
    sample = fp[:100]  # gate on up to 100 unique first-task pairs (all of them if fewer)
    n_checked = exactness_gate(cached, base, sample, 'smoke-first-task', 100)

    # --- job slices for the first task, cross-checked against banked values ---
    result = {'task_id': tid, 'depths_kept': [t['must_change_depth'][i] for i in keep],
              'pruned_indices': sorted(pruned.get(tid, set())),
              'gate_pairs_checked': n_checked, 'arms': {}}
    for arm in ('A', 'B', 'C'):
        o = parse_output(gen[(tid, arm)])
        change = [bool(_still_asserts(cached, o, cc, ASSERT_T)) for cc in ann.must_change]
        persist = [bool(_still_asserts(cached, o, cc, ASSERT_T)) for cc in ann.must_persist]
        my_contam = sum(change) / len(change)
        my_complete = sum(persist) / len(persist)
        ref = scores_idx[(tid, arm)]
        result['arms'][arm] = {
            'must_change_asserted': change, 'must_persist_asserted': persist,
            'my_contamination': my_contam, 'ref_contamination': ref['contamination'],
            'contam_match': abs(my_contam - ref['contamination']) <= TOL,
            'my_completeness': my_complete, 'ref_completeness': ref['completeness'],
            'complete_match': abs(my_complete - ref['completeness']) <= TOL,
        }
    a_out = parse_output(gen[(tid, 'A')])
    c_out = contract(cached, docs_for(t), a_out)
    my_sha = hashlib.sha256(serialize(c_out).encode()).hexdigest()
    result['c_regen'] = {'rederived_sha': my_sha, 'logged_sha': logged_sha.get(tid),
                         'match': my_sha == logged_sha.get(tid)}
    det_cfg = dataclasses.replace(CONFIG.detector, grounding_floor=0.70, drop_ceiling=0.10)
    c_out2 = contract(cached, docs_for(t), a_out, config=det_cfg)
    s = score(cached, c_out2, ann)
    result['sweep_frozen_cell'] = {
        'c_contamination': s.contamination, 'c_completeness': s.completeness}
    result['cache_stats'] = {'lookups': cached.n_lookups, 'misses': cached.n_misses,
                             'unique_cached': len(cached._cache)}

    # hard asserts so a broken smoke exits non-zero
    bad = []
    for arm in ('A', 'B', 'C'):
        if not result['arms'][arm]['contam_match']:
            bad.append(f'{arm} contamination')
        if not result['arms'][arm]['complete_match']:
            bad.append(f'{arm} completeness')
    if not result['c_regen']['match']:
        bad.append('c_regen sha')
    print('SMOKE_RESULT ' + json.dumps(result, indent=2), flush=True)
    if bad:
        log('SMOKE FAILED — mismatches: ' + ', '.join(bad))
        sys.exit(2)
    log('SMOKE SLICE DONE — all cross-checks + gate passed')


def main():
    smoke = '--smoke' in sys.argv
    log(f'exploratory-v2 START (config_hash={CH}, assert_threshold={ASSERT_T}, smoke={smoke})')
    log('loading NLI scorer (CPU, frozen config)...')
    from closure_harness.nli import NLIScorer
    base = NLIScorer()
    log(f'NLI scorer loaded (device={base.device}, batch_size={base.config.batch_size})')

    if smoke:
        run_smoke(base)
        return

    gen = sanitized_gen()
    cached = CachedScalar(base)

    # Full-run exactness gate: draw >=200 unique pairs across the WHOLE corpus and prove the
    # cache path equals direct inference before relying on it for any banked cross-check.
    all_pairs = _collect_all_directional_pairs(gen)
    naive_count = _naive_pair_count(gen)
    log(f'  unique directional pairs across all jobs = {len(all_pairs)} '
        f'(naive re-judged count = {naive_count})')
    rng = random.Random(0)
    rng.shuffle(all_pairs)
    sample = all_pairs[:min(len(all_pairs), 200)]
    exactness_gate(cached, base, sample, 'full-run', 200)

    job1(cached, gen)   # aborts on any banked cross-check mismatch (this is the exactness proof)
    job2(cached, gen)
    job3(cached, gen)
    cached.dump(OUT_CACHE)
    log(f'  wrote {OUT_CACHE.name} ({len(cached._cache)} unique pairs)')
    log(f'CACHE STATS — lookups={cached.n_lookups} misses={cached.n_misses} '
        f'unique={len(cached._cache)}')
    log('ALL JOBS DONE')


def _naive_pair_count(gen):
    """How many directional pair-judgments a NON-cached run would make (for the report).

    job1: for each task, each arm, each (must_change + must_persist) conclusion, one
          _still_asserts -> scalar(premises, concl) -> 2*len(premises) directional pairs.
    job2: contract over A once -> per fixpoint pass, per surviving sourced claim, grounding
          (2*nsrc) + grounding_without (2*(nsrc-|src_ids|)). Counted by actually walking the
          contraction with a counting stub is overkill; we count the SINGLE-PASS lower bound
          plus job3's 9x re-contraction, which dominates.
    job3: B scoring (same shape as job1's B slice) + 9 cells each re-contracting A and
          re-scoring C. The 9x C re-contraction + re-score is the bulk of the naive cost.

    We count exactly by running the three jobs' call sites against a counting scalar — cheap,
    no model. This gives the honest naive number to compare against unique pairs.
    """
    counter = {'n': 0}

    class Counter:
        def __call__(self, sources, claim):
            counter['n'] += 2 * len(sources)
            # return a mid value so contract()'s fixpoint behaves plausibly; the COUNT is what
            # we want, and contraction's flag branch still exercises grounding_without calls.
            return 0.5
    cnt = Counter()
    # job1 shape
    for t in tasks:
        ann, keep = annotations_for(t)
        for arm in ('A', 'B', 'C'):
            o = parse_output(gen[(t['task_id'], arm)])
            for concl in list(ann.must_change) + list(ann.must_persist):
                _still_asserts(cnt, o, concl, ASSERT_T)
    # job2 shape
    for t in tasks:
        a_out = parse_output(gen[(t['task_id'], 'A')])
        contract(cnt, docs_for(t), a_out)
    # job3 shape: B scoring + 9 cells
    for t in tasks:
        ann, _ = annotations_for(t)
        o = parse_output(gen[(t['task_id'], 'B')])
        score(cnt, o, ann)
    for f in CONFIG.detector.grounding_floor_sweep:
        for c in CONFIG.detector.drop_ceiling_sweep:
            det_cfg = dataclasses.replace(CONFIG.detector, grounding_floor=f, drop_ceiling=c)
            for t in tasks:
                ann, _ = annotations_for(t)
                a_out = parse_output(gen[(t['task_id'], 'A')])
                c_out = contract(cnt, docs_for(t), a_out, config=det_cfg)
                score(cnt, c_out, ann)
    return counter['n']


if __name__ == '__main__':
    main()
