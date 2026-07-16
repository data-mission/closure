"""E5 arms — lean end-to-end driver (run of 2026-07-15).

GATE NOTE: this driver contains no in-code registration gate. The
freeze-before-data gate was executed MANUALLY for this run and is verifiable in
GATE-RECORD.md (freeze commits public at 15:11/15:25Z; first generation 15:28:29Z).
The in-code gated runner is harness run_e5.py (commit 2acfeb5), not used in this run.
Do not reuse this driver without either the manual gate procedure or run_e5.py's
checks.

Phases: (1) generate arms A and B (resumable), (2) derive arm C by contraction,
(3) score all arms against annotations with the pruning register applied,
(4) statistics + results summary. All artifacts land in E5-CORPUS; no pushes.
"""
import json, hashlib, datetime, pathlib, sys, traceback

D = pathlib.Path('/Users/vlad/repos/merchloom-2/merchloom/_dev_notes/closure-ir-research/E5-CORPUS')
REPO = pathlib.Path('/Users/vlad/repos/closure')
LOG = D / 'arms-log.jsonl'
SCORES = D / 'arms-scores.jsonl'
SUMMARY = D / 'results-summary.json'

from closure_harness.pilot import PROMPT_TEMPLATE
from closure_harness.providers import make_provider, ProviderError
from closure_harness.generate import generate_row
from closure_harness.schema import parse_output, Output, Claim
from closure_harness.contraction import contract, serialize
from closure_harness.outcomes import Annotations, score
from closure_harness.stats import two_proportion_ztest, completeness_non_inferiority
from closure_harness.config import config_hash

CH = config_hash()

def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()

# --- inputs (all from the public repo = the frozen state) ---
tasks = [json.loads(l) for l in open(REPO / 'experiments/E5-reclosure/corpus/tasks.jsonl')]
armb_lines = [l for l in open(REPO / 'experiments/E5-reclosure/ARM-B-INSTRUCTION.md') if l.startswith('> ')]
ARMB = ' '.join(l[2:].strip() for l in armb_lines)
assert 600 < len(ARMB) < 900, f'Arm-B text length suspicious: {len(ARMB)}'
pruned = {}
for it in json.load(open(D / 'pruned-items.json')):
    pruned.setdefault(it['task_id'], set()).add(it['item_index'])

def docs_for(t):
    return [s['text'] for s in t['sources']] + [t['not_A_evidence']['text']]

def prompt_for(t, arm):
    docs = docs_for(t)
    block = '\n'.join(f'[{i}] {x}' for i, x in enumerate(docs))
    p = PROMPT_TEMPLATE.format(documents=block, question=t['question'])
    if arm == 'B':
        marker = '\n\nProvide your answer'
        assert marker in p
        p = p.replace(marker, f'\n\n{ARMB}{marker}', 1)
    return p

def out_to_dict(o: Output):
    return {'claims': [{'id': c.id, 'text': c.text, 'source_ids': list(c.source_ids)} for c in o.claims],
            'conclusion': o.conclusion}

SANITATION = {}  # (task_id, arm) -> n stripped
def sanitize(out_dict, ndocs, task_id, arm):
    """Pre-scoring repair (2026-07-15, applied before ANY outcome was computed, disclosed in
    PROTOCOL): a claim citing a nonexistent source index has no valid support — treated as
    unsupported and stripped, identically in every arm, before contraction and scoring."""
    good = [c for c in out_dict['claims'] if all(0 <= i < ndocs for i in c['source_ids'])]
    n_bad = len(out_dict['claims']) - len(good)
    if n_bad:
        SANITATION[(task_id, arm)] = n_bad
    return {'claims': good, 'conclusion': out_dict['conclusion']}

def log_row(r):
    with open(LOG, 'a') as f:
        f.write(json.dumps(r, ensure_ascii=True) + '\n')

# --- phase 1: generations (A, B) ---
done = set()
if LOG.exists():
    for l in open(LOG):
        r = json.loads(l)
        if r.get('config_hash') == CH and not r.get('error'):
            done.add((r['task_id'], r['arm']))
provider = make_provider()
todo = [(t, a) for t in tasks for a in ('A', 'B') if (t['task_id'], a) not in done]
print(f'[phase1] {len(todo)} generations to do ({len(done)} banked)', flush=True)
for t, arm in todo:
    p = prompt_for(t, arm)
    try:
        row = generate_row(provider, p)
        log_row({'task_id': t['task_id'], 'arm': arm, 'prompt_sha256': hashlib.sha256(p.encode()).hexdigest(),
                 'output': out_to_dict(row.output), 'reported_model': row.reported_model,
                 'config_hash': CH, 'ts': now()})
        print(f'[gen] {t["task_id"]} {arm} ok', flush=True)
    except ProviderError as e:
        log_row({'task_id': t['task_id'], 'arm': arm, 'error': str(e)[:300], 'config_hash': CH, 'ts': now()})
        print(f'[gen] {t["task_id"]} {arm} ERROR {str(e)[:80]}', flush=True)

# reload clean generations
gen = {}
for l in open(LOG):
    r = json.loads(l)
    if r.get('config_hash') == CH and not r.get('error'):
        gen[(r['task_id'], r['arm'])] = r['output']
missing = [(t['task_id'], a) for t in tasks for a in ('A', 'B') if (t['task_id'], a) not in gen]
if missing:
    print(f'[phase1] STILL MISSING after pass: {missing} — watchdog will relaunch', flush=True)
    sys.exit(3)

# --- phase 2: arm C by contraction (deterministic, zero generation) ---
print('[phase2] loading NLI scorer (CPU, frozen config)...', flush=True)
from closure_harness.nli import NLIScorer
scalar = NLIScorer()
# sanitize ALL arm outputs identically (invalid-citation claims stripped, logged)
for t in tasks:
    nd = len(docs_for(t))
    for arm in ('A', 'B'):
        gen[(t['task_id'], arm)] = sanitize(gen[(t['task_id'], arm)], nd, t['task_id'], arm)
if SANITATION:
    print(f'[sanitize] stripped invalid-citation claims: { {f"{k[0]}/{k[1]}":v for k,v in sorted(SANITATION.items())} }', flush=True)

for t in tasks:
    if (t['task_id'], 'C') in gen:
        continue
    a_out = parse_output(gen[(t['task_id'], 'A')])
    c_out = contract(scalar, docs_for(t), a_out)
    log_row({'task_id': t['task_id'], 'arm': 'C', 'derived_from': 'A(sanitized)',
             'output': out_to_dict(c_out), 'serialized_sha256': hashlib.sha256(serialize(c_out).encode()).hexdigest(),
             'config_hash': CH, 'ts': now()})
    gen[(t['task_id'], 'C')] = out_to_dict(c_out)
    print(f'[contract] {t["task_id"]} C: {len(c_out.claims)} claims survive', flush=True)
contract_excluded = {}
print(f'[phase2] all {len(tasks)} tasks in play; sanitation register: {len(SANITATION)} arm-outputs touched', flush=True)

# --- phase 3: scoring with pruning register ---
per = {}   # (task_id, arm) -> dict
for t in tasks:
    keep = [i for i in range(len(t['must_change'])) if i not in pruned.get(t['task_id'], set())]
    ann = Annotations(must_change=tuple(t['must_change'][i] for i in keep),
                      must_persist=tuple(t['must_persist']))
    for arm in ('A', 'B', 'C'):
        o = parse_output(gen[(t['task_id'], arm)])
        s = score(scalar, o, ann)
        n = len(ann.must_change)
        rec = {'task_id': t['task_id'], 'arm': arm, 'family': t['family'],
               'n_items': n, 'contaminated_items': round(s.contamination * n),
               'contamination': s.contamination, 'completeness': s.completeness,
               'config_hash': CH, 'ts': now()}
        per[(t['task_id'], arm)] = rec
        with open(SCORES, 'a') as f:
            f.write(json.dumps(rec) + '\n')
    print(f'[score] {t["task_id"]} done', flush=True)

# --- phase 4: statistics ---
def pooled(arm):
    su = sum(per[(t['task_id'], arm)]['contaminated_items'] for t in tasks)
    tr = sum(per[(t['task_id'], arm)]['n_items'] for t in tasks)
    return su, tr
res = {'config_hash': CH, 'head': None, 'ts': now(),
       'corpus_sha256': sha(REPO / 'experiments/E5-reclosure/corpus/tasks.jsonl'),
       'armb_sha256': sha(REPO / 'experiments/E5-reclosure/ARM-B-INSTRUCTION.md'),
       'n_tasks_scored': len(tasks), 'excluded_tasks': contract_excluded,
       'sanitation_register': {f'{k[0]}/{k[1]}': v for k, v in sorted(SANITATION.items())},
       'arms': {}, 'tests': {}, 'per_family': {}}
for arm in ('A', 'B', 'C'):
    su, tr = pooled(arm)
    comp = [per[(t['task_id'], arm)]['completeness'] for t in tasks]
    res['arms'][arm] = {'contaminated': su, 'trials': tr, 'rate': su / tr,
                        'mean_completeness': sum(comp) / len(comp)}
for a, b in (('A', 'B'), ('A', 'C'), ('B', 'C')):
    sa, ta = pooled(a); sb, tb = pooled(b)
    z = two_proportion_ztest(sa, ta, sb, tb)
    res['tests'][f'{a}_vs_{b}'] = {'p_a': z.p_hat_a, 'p_b': z.p_hat_b, 'z': z.z,
                                   'p_value': z.p_value, 'p_corrected': z.p_value_corrected,
                                   'significant': z.significant}
ni = completeness_non_inferiority([per[(t['task_id'], 'C')]['completeness'] for t in tasks],
                                  [per[(t['task_id'], 'B')]['completeness'] for t in tasks])
res['tests']['C_completeness_noninferior_to_B'] = {'mean_c': ni.mean_c, 'mean_b': ni.mean_b,
                                                   'diff': ni.diff, 'margin': ni.margin,
                                                   'non_inferior': ni.non_inferior}
for fam in ('F1', 'F2', 'F3'):
    res['per_family'][fam] = {}
    for arm in ('A', 'B', 'C'):
        rs = [per[(t['task_id'], arm)] for t in tasks if t['family'] == fam]
        su = sum(r['contaminated_items'] for r in rs); tr = sum(r['n_items'] for r in rs)
        res['per_family'][fam][arm] = {'rate': su / tr, 'contaminated': su, 'trials': tr}
json.dump(res, open(SUMMARY, 'w'), indent=2)
print('[phase4] RESULTS WRITTEN', flush=True)
print(json.dumps({k: res['arms'][k]['rate'] for k in res['arms']}, indent=2), flush=True)
