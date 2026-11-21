"""Audit saved coverage, check boundary cases, and reproduce the report tables."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
from statistics import median

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments.ilp_baseline import solve_ilp
from nscover import Instance, brute_force, solve_pairflow

OUT = Path(__file__).resolve().parent

def read(path):
    return [json.loads(line) for line in path.read_text().splitlines()]

original, current, benchmarks, commands = [], [], [], []
for path in sorted(OUT.glob('*.jsonl')):
    if path.name == 'boundary-cases.jsonl':
        continue
    rows = read(path)
    assert rows[0].get('meta'), path
    commands.append('bash results/ilp-baseline-20261115/run.sh ' + shlex.join(rows[0]['argv'][1:]))
    if path.name.startswith('agreement-'):
        cases = rows[1:-1]
        assert rows[-1]['summary'] and rows[-1]['count'] == len(cases) == 500
        assert all(r['agreement'] and r['ilp'] == r['pf'] == r['oracle'] for r in cases)
        (current if path.name.startswith('agreement-current-') else original).extend(cases)
    else:
        assert len(rows) == 2, path
        benchmarks.append(rows[1])
assert len(original) == len(current) == 3000
assert [r['instance'] for r in original] == [r['instance'] for r in current]
assert len(benchmarks) == 82
shortage = sorted([r for r in benchmarks if r['family'] == 'shortage'], key=lambda r: r['e'])
even = [r for r in benchmarks if r['family'] != 'shortage']
assert [r['e'] for r in shortage] == [2,4,8,12,16,20,30,50,100,200]
assert {(r['family'], r['target_m'], r['index'], r['variant']) for r in even} == {
    (f,m,i,v) for f in ('sparse','dense') for m in (50,200,1000) for i in range(3)
    for v in ('FIX-yes','FREE-yes','FIX-cut','FREE-cut')}
for r in benchmarks:
    assert r['agreement']
    assert hashlib.sha256(json.dumps(r['instance'], sort_keys=True).encode()).hexdigest() == r['sha256']
    assert r['ilp']['status'] == r['pf']['status'] in ('YES','NO')
    for alg in ('ilp','pf','bb'):
        assert r[alg]['status'] in ('YES','NO','LIMIT')
        if r[alg]['status'] == 'YES':
            assert r[alg]['walks_checked']
    if r['family'] != 'shortage':
        assert r['even'] == r['components'] > 0
        if r['variant'].endswith('yes'):
            assert r['ilp']['status'] == 'YES'
    else:
        assert r['ilp']['status'] == 'NO'

cases = [
    ('empty-fixed', Instance(2, [], [1,0], [1,0]), 'YES'),
    ('empty-moved', Instance(2, [], [1,0], [0,1]), 'NO'),
    ('empty-no-walks', Instance(2, [], [0,0]), 'YES'),
    ('empty-total-mismatch', Instance(2, [], [1,0], [0,0]), 'NO'),
    ('no-token-edge', Instance(2, [(0,1,0)], [0,0]), 'NO'),
    ('fixed-total-mismatch', Instance(2, [(0,1,0)], [1,0], [0,0]), 'NO'),
    ('isolated-end', Instance(3, [(0,1,1)], [1,0,2], [0,1,0]), 'NO'),
    ('same-time-path', Instance(3, [(0,1,5),(1,2,5)], [1,0,0], [0,0,1]), 'YES'),
    ('time-reversed-path', Instance(3, [(0,1,2),(1,2,1)], [1,0,0], [0,0,1]), 'NO'),
    ('parallel-return', Instance(2, [(0,1,7),(0,1,7)], [1,0], [1,0]), 'YES'),
    ('closed-cycle-no-walk', Instance(3, [(0,1,1),(1,2,1),(2,0,1)], [0,0,0]), 'NO'),
    ('unsorted-negative-times', Instance(3, [(1,2,-1),(0,1,-2)], [1,0,0], [0,0,1]), 'YES'),
]
boundaries = []
for name, inst, expected in cases:
    result = solve_ilp(inst, 60)
    pf = solve_pairflow(inst)
    oracle = 'YES' if brute_force(inst) else 'NO'
    assert result.status == pf.status == oracle == expected, name
    boundaries.append(dict(case=name, instance=inst.to_json(), ilp=result.status,
                           pf=pf.status, oracle=oracle, tails=result.tails))
try:
    solve_ilp(Instance(2, [], [1,0], end_set=[0]), 60)
    raise AssertionError('ENDSET must be rejected')
except ValueError:
    pass
assert solve_ilp(Instance(2, [], [1,0]), 0).status == 'LIMIT'
(OUT/'boundary-cases.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in boundaries))
(OUT/'commands.sh').write_text('#!/usr/bin/env bash\nset -eu\n# From repository root, with fresh output filenames (existing files are protected).\n'+'\n'.join(commands)+'\n')
counts = Counter(r['mode'] for r in original)
counts.update(r['oracle'] for r in original)
counts['with_even_components'] = sum(r['even'] > 0 for r in original)
counts['disagreements'] = 0
summary = {'agreement': dict(counts), 'initial_checks':3000, 'current_checks':3000,
           'boundary_checks':len(boundaries), 'benchmarks':len(benchmarks), 'groups':[]}
table = ['| Family | Target m | Cases | ILP median / max s | PF median / max s | BB median / max s | BB limits |',
         '|---|---:|---:|---:|---:|---:|---:|']
for family in ('sparse','dense'):
    for m in (50,200,1000):
        group = [r for r in even if r['family']==family and r['target_m']==m]
        record = {'family':family, 'target_m':m, 'cases':len(group)}
        cells=[]
        for alg in ('ilp','pf','bb'):
            times = [min(60,r[alg]['seconds']) if r[alg]['status']=='LIMIT' else r[alg]['seconds'] for r in group]
            record[alg] = {'median':median(times), 'max':max(times),
                           'limits':sum(r[alg]['status']=='LIMIT' for r in group)}
            cells.append(f'{median(times):.4f} / {max(times):.4f}')
        summary['groups'].append(record)
        table.append(f'| {family} | {m} | {len(group)} | '+ ' | '.join(cells) + f" | {record['bb']['limits']} |")
short_table = ['| e | m | ILP s | PF s | BB s / status |', '|---:|---:|---:|---:|---:|']
for r in shortage:
    bb = f"{r['bb']['seconds']:.4f}" if r['bb']['status']!='LIMIT' else 'LIMIT (60 s)'
    short_table.append(f"| {r['e']} | {r['m']} | {r['ilp']['seconds']:.4f} | {r['pf']['seconds']:.4f} | {bb} |")
summary['limits'] = {a:sum(r[a]['status']=='LIMIT' for r in benchmarks) for a in ('ilp','pf','bb')}
summary['resolved_statuses'] = dict(Counter(r['ilp']['status'] for r in benchmarks))
summary['max_seconds'] = {a:max(r[a]['seconds'] for r in benchmarks) for a in ('ilp','pf','bb')}
(OUT/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
source_paths = ['experiments/ilp_baseline.py','nscover/instance.py','nscover/timeline.py',
                'nscover/chainflow.py','nscover/pairflow.py','nscover/branch.py','nscover/walks.py',
                'nscover/brute.py','nscover/generators.py','experiments/family.py','experiments/even_rich_bench.py']
(OUT/'source-sha256.txt').write_text(''.join(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()+'  '+p+'\n' for p in source_paths))
version = read(OUT/'shortage-e200.jsonl')[0]
head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
readme = f'''# Independent ILP baseline — 2026-11-15

## Material Passport

Artifact: experiment result; mode: run; status: completed and locally verified.
Inputs: user-specified FIX/FREE characterization and repository generators.
Evidence: JSONL instances, statuses, timings, checked witnesses, and the audit below.

## Outcome and agreement

The initial **3,000 random cases** have **zero disagreements** between ILP, PF,
and the operational `nscover.brute.brute_force` oracle. There are 1,500 FIX and
1,500 FREE cases; 1,500 use `random_instance` and 1,500 use `cycle_instance`.
All have at most 10 edges; 484 contain at least one even component.
Answers: 1,853 YES and 1,147 NO. Every ILP/PF YES was built into walks and checked.
Six seeds are 20261115 through 20261120, with 500 cases each. FIX and FREE are
balanced within each generator. Cycle samples exceeding 10 edges are rejected
so every random case receives a full operational oracle check.

A second pass reran the **same 3,000 cases against the current library** with
zero disagreements; these are repeated checks, not 3,000 additional distinct
random draws. Twelve named boundary cases also agree with PF and brute force.
They include empty graphs, isolated vertices, total mismatch, no-token cycles,
parallel edges, same-time traversals, and unsorted/negative labels. ENDSET is
explicitly rejected; a nonpositive time budget returns LIMIT.

All **82 benchmark cases** were attempted with ILP, PF, and BB: 10 shortage
sizes and 72 even-rich cases. ILP and PF resolved all 82 and agree throughout.
BB resolved 74 and agrees on all 74; its other eight results are LIMIT.
Every benchmark YES from all three solvers passed walk construction/checking.

## Encoding

`solve_ilp(inst, time_limit)` returns the library `Result` shape: status
YES/NO/LIMIT and, on YES, the tail vertex for every edge in input order.
It independently constructs snapshot components and affine counters; it does
not call Timeline, chain constraints, PF, or BB to build or decide the model.
The module imports those APIs only for agreement/benchmark orchestration and
uses the required library walk builder/checker to validate each ILP YES.

Binary x_e=1 puts the tail at the first listed endpoint. An earlier incident
edge contributes 1-2*x_e at its first endpoint and 2*x_e-1 at its second.
For every vertex appearance the counter after the entire timestamp is >=0.
For every edge-containing snapshot component the sum of counters before that
timestamp is >=1. FIX additionally equates every final counter to `inst.end`,
including isolated vertices. FREE needs no final constraints: total walks are
conserved by each edge. The objective is identically zero. Empty edge sets
are decided directly. These conventions match chainflow.py and walks.py.
Rounded binary incumbents are checked against the integer constraints before
being converted to independently checked walks. Infeasible HiGHS status yields
NO; a limit without a valid incumbent yields LIMIT; unexpected failures raise.

## Timing protocol and limitations

Each solver gets a fresh forked process and a **60-second wall limit**, including
model/Timeline construction, solving, and one walk validation for YES. Imports
and process startup are excluded from reported solver seconds; startup is
included in the hard wall budget. ILP also receives HiGHS time_limit=60.
The parent terminates a child on the hard deadline. BB uses its 60-second
cooperative limit with max_flows=10**18, so its flow cap is not the restriction.
Raw elapsed times can exceed 60 slightly from scheduling/deadline handling.

Solvers run sequentially within this experiment. PF/BB use default `augment`
with SciPy available. OPENBLAS_NUM_THREADS=1 and OMP_NUM_THREADS=1. There is one
measurement per solver/case, without warm-up or timing repetitions. Tiny times
are noisy. No brute-force claim is made for the large benchmark cases.

**Concurrent-work caveat:** another actor changed `nscover/pairflow.py` during
this run to add optional incremental reorientation, retaining the default
`scratch` path used here. Another actor also created commit `{head}`,
which captured some in-progress ILP artifacts; this agent did not commit,
change library/tests/manuscripts, or create a branch. The change adds an
optional branch and leaves default orientation reconstruction intact. Initial
rows cannot be individually attributed to before/after that change because
source hashes were not captured at each launch. The current-library agreement
rerun verifies correctness after the change. Other concurrent experiment work
was present in the workspace, so **these are shared-machine observations,
not isolated performance estimates**. Timing ratios should not be generalized.
`source-sha256.txt` captures final source bytes for future reproduction.

## Shortage family

FREE instances use `family(e)` with r=e-1, hence all ten are NO. No size was
skipped after a BB LIMIT. All times below are seconds.

{chr(10).join(short_table)}

## Even-rich family

Seed **20261113**, sparse/dense, target m=50,200,1000, graph indices 0,1,2.
Each graph has FIX-yes, FREE-yes, FIX-cut, FREE-cut variants (12 rows per group).
The existing generator can overshoot the target edge count; each JSONL records
both target_m and actual m, the full instance, and its SHA-256. Cut does not
imply infeasible. Every generated snapshot component is even (audited).

The table pools the four variants and three graph indices per group. It reports
median / maximum seconds. BB LIMITs enter this descriptive table as 60 seconds;
the raw JSONL retains actual elapsed times and flags hard deadline terminations.
All ILP and PF limit counts are zero.

{chr(10).join(table)}

## Environment and exact commands

Python: `{version['python']}`. SciPy: **{version['scipy']}**; NumPy:
**{version['numpy']}**; bundled HiGHS: **1.8.0**.
Platform: `{version['platform']}`.

The requested environment command was attempted:

```sh
nix shell nixpkgs#python3Packages.scipy nixpkgs#python3Packages.numpy -c python3 ...
```

It failed because the sandbox denied connection to the local Nix daemon socket.
No dependency was installed. `run.sh` instead uses the default `python3` plus
already-cached Nix SciPy/NumPy site-packages through PYTHONPATH; its exact store
paths are recorded in that script. Every JSONL metadata row records argv and
Python/SciPy/NumPy versions. `commands.sh` lists **every exact successful run
command**, including the current-library reruns, each as a separate command.
Each benchmark command runs one instance (at most 180 solver seconds), and each
agreement command runs 500 small cases. `run.sh` enforces 240 seconds per command,
below five minutes. Outputs are opened exclusively to prevent silent overwrites.
Run from the repository root using fresh output filenames/a fresh result target.

To re-audit and regenerate this README, boundary results, summary, command list,
and final source hashes, run from the repository root:

```sh
PYTHONPATH=/nix/store/2zn0v1k3nnc25snk47mf5vjimwdva4sm-python3.13-scipy-1.16.3/lib/python3.13/site-packages:/nix/store/bvcpg8ny128rrnkzhw5wmkakp06hpm62-python3.13-numpy-2.3.4/lib/python3.13/site-packages OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 timeout 240 python3 results/ilp-baseline-20261115/verify.py
```

The audit checks exact grid coverage, all statuses, absence of disagreement,
instance hashes, planted feasibility, even-component coverage, witness flags,
and the correspondence of the initial/current random instances. Source authority
was the supplied task plus instance.py, chainflow.py, and walks.py;
`docs/WORKFLOW.md` was absent. No external service was contacted.

A separate regression check, `python3 -m unittest discover -s tests -p test_unit.py`,
passed all 10 existing unit tests. No test files were changed by this task.
'''
(OUT/'README.md').write_text(readme)
print(json.dumps(summary, indent=2))
