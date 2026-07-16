"""Regenerate results-summary.json from raw arms-scores.jsonl after crash #2
(json serialization of numpy bool in run_arms.py phase 4; all 180 score rows intact).
Reuses the FROZEN harness stats functions; only the serialization differs (bool cast).
Sanitation register + hashes carried from the partial file's pre-crash output,
cross-checked against arms-log.jsonl where possible."""
import json, hashlib, pathlib, datetime

D = pathlib.Path('/Users/vlad/repos/merchloom-2/merchloom/_dev_notes/closure-ir-research/E5-CORPUS')
REPO = pathlib.Path('/Users/vlad/repos/closure')

from closure_harness.stats import two_proportion_ztest, completeness_non_inferiority
from closure_harness.config import config_hash

CH = config_hash()
tasks = [json.loads(l) for l in open(REPO / 'experiments/E5-reclosure/corpus/tasks.jsonl')]

rows = [json.loads(l) for l in open(D / 'arms-scores.jsonl')]
assert all(r['config_hash'] == CH for r in rows), 'config hash mismatch in scores'
per = {}
for r in rows:
    key = (r['task_id'], r['arm'])
    assert key not in per, f'duplicate score row {key}'
    per[key] = r
assert len(per) == 180, f'expected 180 unique (task,arm), got {len(per)}'
for t in tasks:
    for arm in 'ABC':
        assert (t['task_id'], arm) in per, f'missing {t["task_id"]}/{arm}'

# carry deterministic pre-crash fields from the partial file (truncated JSON, parse by hand)
partial = (D / 'results-summary.json').read_text()
san_start = partial.index('"sanitation_register"')
san_block = partial[partial.index('{', san_start): partial.index('}', san_start) + 1]
sanitation = json.loads(san_block)

def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()

def pooled(arm):
    su = sum(per[(t['task_id'], arm)]['contaminated_items'] for t in tasks)
    tr = sum(per[(t['task_id'], arm)]['n_items'] for t in tasks)
    return su, tr

res = {'config_hash': CH, 'head': None,
       'ts': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
       'regenerated_from': 'arms-scores.jsonl after phase-4 serialization crash (see EVENTS.md); scores untouched',
       'corpus_sha256': sha(REPO / 'experiments/E5-reclosure/corpus/tasks.jsonl'),
       'armb_sha256': sha(REPO / 'experiments/E5-reclosure/ARM-B-INSTRUCTION.md'),
       'n_tasks_scored': len(tasks), 'excluded_tasks': {},
       'sanitation_register': sanitation,
       'arms': {}, 'tests': {}, 'per_family': {}}
for arm in 'ABC':
    su, tr = pooled(arm)
    comp = [per[(t['task_id'], arm)]['completeness'] for t in tasks]
    res['arms'][arm] = {'contaminated': su, 'trials': tr, 'rate': su / tr,
                        'mean_completeness': sum(comp) / len(comp)}
for a, b in (('A', 'B'), ('A', 'C'), ('B', 'C')):
    sa, ta = pooled(a); sb, tb = pooled(b)
    z = two_proportion_ztest(sa, ta, sb, tb)
    res['tests'][f'{a}_vs_{b}'] = {'p_a': z.p_hat_a, 'p_b': z.p_hat_b, 'z': z.z,
                                   'p_value': z.p_value, 'p_corrected': z.p_value_corrected,
                                   'significant': bool(z.significant)}
ni = completeness_non_inferiority([per[(t['task_id'], 'C')]['completeness'] for t in tasks],
                                  [per[(t['task_id'], 'B')]['completeness'] for t in tasks])
res['tests']['C_completeness_noninferior_to_B'] = {'mean_c': ni.mean_c, 'mean_b': ni.mean_b,
                                                   'diff': ni.diff, 'margin': ni.margin,
                                                   'non_inferior': bool(ni.non_inferior)}
for fam in ('F1', 'F2', 'F3'):
    res['per_family'][fam] = {}
    for arm in 'ABC':
        rs = [per[(t['task_id'], arm)] for t in tasks if t['family'] == fam]
        su = sum(r['contaminated_items'] for r in rs); tr = sum(r['n_items'] for r in rs)
        res['per_family'][fam][arm] = {'rate': su / tr, 'contaminated': su, 'trials': tr}

out = json.dumps(res, indent=2, default=lambda o: bool(o))
json.loads(out)  # must round-trip
(D / 'results-summary.json').write_text(out)
print('WRITTEN', len(out), 'bytes')
print(json.dumps(res['tests'], indent=2))
print(json.dumps(res['per_family'], indent=2))
