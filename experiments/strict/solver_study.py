"""Reproducible validation/benchmark driver; never imports seed experiment loops."""
from __future__ import annotations
import argparse
import ast
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from nscover import Instance, solve_pairflow
from experiments.strict import oracle
from experiments.strict.solver import solve_strict, check_strict_walks, build_strict_walks

OUT = ROOT / 'results/strict-solver-20261101'


def seed_functions(filename, names):
    """Execute exactly the unchanged generator function ASTs, not module loops."""
    path = Path(__file__).parent / 'seed' / filename
    tree = ast.parse(path.read_text())
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = dict(Instance=Instance)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), 'exec'), namespace)
    return namespace


def generators():
    classes = seed_functions('classes_seed.py', {'snap_ok', 'gen'})
    general = seed_functions('ilp_seed.py', {'rand_inst'})
    return classes, general


def tiny(rng, kind, fix, classes, general):
    if kind == 'general':
        return general['rand_inst'](rng, fix)
    if kind == 'cycle':
        # maxdeg2 in classes_seed permits paths and parallel cycles too; explicitly
        # construct simple cycles here and check using its maxdeg2 predicate.
        n = rng.randint(3, 5)
        edges = []
        for t in range(rng.randint(1, 2)):
            length = rng.randint(3, min(n, 8 - len(edges)))
            vertices = rng.sample(range(n), length)
            layer = [(vertices[i], vertices[(i + 1) % length]) for i in range(length)]
            assert classes['snap_ok']('maxdeg2', layer, n)
            edges.extend((u, v, t) for u, v in layer)
            if 8 - len(edges) < 3:
                break
        a, z = [0] * n, [0] * n
        for _ in range(rng.randint(1, 4)):
            a[rng.randrange(n)] += 1; z[rng.randrange(n)] += 1
        return Instance(n, edges, a, z if fix else None)
    while True:
        inst = classes['gen'](rng, 'matching' if kind == 'proper' else kind, fix)
        if inst.m <= 8:
            for t in {t for _, _, t in inst.edges}:
                assert classes['snap_ok']('matching' if kind == 'proper' else kind,
                                         [(u, v) for u, v, s in inst.edges if s == t], inst.n)
            return inst


def regressions():
    cases = [
        (Instance(1, [], [0]), True),
        (Instance(1, [], [2], [2]), True),
        (Instance(2, [], [1, 0], [0, 1]), False),
        (Instance(1, [], [1], [0]), False),
        (Instance(2, [(0, 1, -3)], [1, 0], [0, 1]), True),
        (Instance(2, [(0, 1, 0)], [1, 0], [1, 0]), False),
        (Instance(3, [(0, 1, 0), (1, 2, 0)], [1, 0, 0]), False),
        (Instance(2, [(0, 1, 0)] * 2, [2, 0], [0, 2]), True),
        (Instance(2, [(0, 1, 0)] * 2, [1, 0]), False),
        (Instance(3, [(1, 2, 100), (0, 1, -1)], [1, 0, 0], [0, 0, 1]), True),
        (Instance(2, [(0, 1, 0)], [0, 0]), False),
    ]
    for inst, truth in cases:
        assert oracle.decide(inst) == oracle.identity_brute(inst) == truth
        for filtered in (False, True):
            result = solve_strict(inst, filtered)
            assert result['status'] == ('YES' if truth else 'NO'), (inst.to_json(), result)
    # Deliberately corrupted witnesses exercise the independent definition.
    inst = Instance(3, [(0, 1, 0), (1, 2, 1)], [1, 0, 0], [0, 0, 1])
    assert check_strict_walks(inst, [dict(start=0, edges=[0, 1])])
    for bad in ([], [dict(start=1, edges=[0, 1])], [dict(start=0, edges=[1, 0])],
                [dict(start=0, edges=[0, 0, 1])], [dict(start=0, edges=[0])],
                [dict(start=0, edges=[0, 9])], [dict(start=-1, edges=[0, 1])]):
        assert not check_strict_walks(inst, bad)
    assert not check_strict_walks(Instance(3, [(0, 1, 0), (1, 2, 0)], [1, 0, 0]),
                                  [dict(start=0, edges=[0, 1])])
    assert not check_strict_walks(Instance(2, [], [1, 0], [0, 1]), [dict(start=0, edges=[])])
    return len(cases)


def validate(count, identity_count, seed):
    begin = time.perf_counter()
    boundary_cases = regressions()
    classes, general = generators()
    rng = random.Random(seed)
    rows = {}
    kinds = ('general', 'proper', 'star', 'forest', 'cycle', 'maxdeg2')
    identity_done = 0
    examples = {}
    for i in range(count):
        kind = kinds[(i // 2) % len(kinds)]
        fix = bool(i % 2)
        inst = tiny(rng, kind, fix, classes, general)
        assert inst.n <= 5 and inst.m <= 8
        truth = oracle.decide(inst)
        if i < identity_count:
            assert oracle.identity_brute(inst) == truth, inst.to_json()
            identity_done += 1
        # Test the actual ILP even on cases that the NS filter would reject.
        result = solve_strict(inst, use_ns_filter=False)
        assert result['status'] == ('YES' if truth else 'NO'), (inst.to_json(), result)
        filtered = solve_strict(inst)
        assert filtered['status'] == result['status'], (inst.to_json(), filtered)
        if truth:
            assert check_strict_walks(inst, result['walks'])
            assert check_strict_walks(inst, filtered['walks'])
        label = kind + ('/FIX' if fix else '/FREE')
        row = rows.setdefault(label, Counter(samples=0, strict_yes=0, ns_yes=0,
                                             ns_yes_strict_no=0, ns_orientation_works=0))
        row['samples'] += 1
        row['strict_yes'] += int(truth)
        ns_yes = filtered['ns_status'] == 'YES'
        row['ns_yes'] += int(ns_yes)
        row['ns_yes_strict_no'] += int(ns_yes and not truth)
        row['ns_orientation_works'] += int(ns_yes and truth and filtered['ns_orientation_strict'])
        assert not truth or ns_yes
        if ns_yes and not truth:
            examples.setdefault(label, inst.to_json())
        if (i + 1) % 2000 == 0:
            print(f'Validated {i + 1}/{count}: 0 disagreements', flush=True)
    totals = sum(rows.values(), Counter())
    return dict(seed=seed, random_instances=count, identity_instances=identity_done,
                boundary_cases=boundary_cases, disagreements=0, totals=dict(totals),
                rows={k: dict(v) for k, v in rows.items()}, examples=examples,
                seconds=time.perf_counter() - begin)


CONFIGS = [(20, 5, 12), (50, 15, 20), (100, 30, 30), (200, 60, 40),
           (400, 120, 60), (800, 250, 80), (1200, 500, 100),
           (4, 4, 500), (6, 8, 1000), (6, 8, 4000)]


def benchmark(case):
    index, mode, variant = case.split('-')
    index = int(index)
    n, k, T = CONFIGS[index]
    rng = random.Random(20261101 + index)
    planted = seed_functions('scale_seed.py', {'planted'})['planted']
    edges, a, z = planted(rng, n, k, 0.9 if index >= 7 else 0.6, T)
    change = None
    if variant == 'perturbed':
        e = rng.randrange(len(edges))
        u, v, t = edges[e]
        change = dict(edge=e, old_time=t, new_time=1 + t % T)
        edges[e] = (u, v, change['new_time'])
    inst = Instance(n, edges, a, z if mode == 'FIX' else None)
    ground_truth_walks = None
    if variant == 'planted':
        ground_truth_walks = build_strict_walks(inst, [u for u, _, _ in edges])
        assert check_strict_walks(inst, ground_truth_walks)
    result = solve_strict(inst, time_limit=60)
    if result['status'] == 'YES':
        assert check_strict_walks(inst, result['walks'])
    data = dict(case=case, n=n, k=k, T=T, m=inst.m, mode=mode, variant=variant,
                token_scarce=index >= 7, perturbation=change, instance=inst.to_json(), **result)
    if variant == 'planted':
        data['planted_assertion'] = 'PASS' if result['status'] == 'YES' else 'FAIL: solver UNKNOWN on known YES'
        if result['status'] != 'YES':
            data['ground_truth_walks'] = ground_truth_walks
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / ('bench-' + case + '.json')).write_text(json.dumps(data) + '\n')
    print(json.dumps({key: value for key, value in data.items()
                      if key not in ('instance', 'orientation', 'walks', 'ground_truth_walks')}), flush=True)
    # Preserve even a failed planted assertion so limits remain auditable.
    if variant == 'planted':
        assert result['status'] == 'YES', (case, result)


def report():
    import numpy
    import scipy
    validation = json.loads((OUT / 'validation.json').read_text())
    raw = [json.loads(p.read_text()) for p in sorted(OUT.glob('bench-*.json'))]
    expected = {f'{i}-{mode}-{variant}' for i in range(len(CONFIGS))
                for mode in ('FREE', 'FIX') for variant in ('planted', 'perturbed')}
    assert {r['case'] for r in raw} == expected, 'benchmark matrix incomplete'
    assert all(r['status'] == 'YES' for r in raw
               if int(r['case'].split('-')[0]) <= 6 and r['variant'] == 'planted')
    rows = [{k: v for k, v in r.items() if k not in
             ('instance', 'walks', 'orientation', 'ground_truth_walks')} for r in raw]
    groups = []
    for index, (n, k, T) in enumerate(CONFIGS):
        group = [r for r in rows if r['case'].startswith(str(index) + '-')]
        groups.append(dict(n=n, k=k, T=T, m=group[0]['m'],
                           statuses={s: sum(r['status'] == s for r in group)
                                     for s in ('YES', 'NO', 'UNKNOWN')},
                           max_seconds=max(r['seconds'] for r in group),
                           max_timings={stage: max(r['timings'][stage] for r in group)
                                        for stage in ('ns_filter', 'ilp_build', 'ilp', 'witness')}))
    env = dict(python=sys.version, scipy=scipy.__version__, numpy=numpy.__version__,
               platform=platform.platform(), processor=platform.processor(),
               thread_environment={k: os.environ.get(k) for k in
                                   ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS')})
    env['source_sha256'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in [Path(__file__), Path(__file__).with_name('solver.py'),
                                      Path(__file__).with_name('oracle.py'),
                                      ROOT / 'nscover/pairflow.py',
                                      *sorted((Path(__file__).parent / 'seed').glob('*.py'))]}
    (OUT / 'summary.json').write_text(json.dumps(dict(environment=env, validation=validation,
                                                      benchmark=rows, benchmark_groups=groups), indent=2) + '\n')
    totals = validation['totals']
    share = totals['ns_orientation_works'] / totals['strict_yes'] if totals['strict_yes'] else 0
    table = ['| n/k/T | m | Mode/type | Status | NS s | Build s | ILP s | Witness s | Total s |',
             '|---|---:|---|---|---:|---:|---:|---:|---:|']
    for r in rows:
        tm = r['timings']
        table.append(f"| {r['n']}/{r['k']}/{r['T']} | {r['m']} | {r['mode']}/{r['variant']} | {r['status']} | "
                     f"{tm['ns_filter']:.4f} | {tm['ilp_build']:.4f} | {tm['ilp']:.4f} | {tm['witness']:.4f} | {r['seconds']:.4f} |")
    counts = dict(Counter(r['status'] for r in rows))
    text = f'''# Exact strict temporal-walk solver

The S model treats each walk as one token. It traverses at most one edge per
snapshot, may wait, and may be empty. Every input edge occurrence is used exactly
once. FREE prescribes start counts a; FIX also prescribes end counts z. Parallel
edges have distinct input IDs. Only loop-free integer-count instances are supported.

For an orientation let o_t(v) count departures and deg_t(v) count incident edges.
Feasibility is o_t(v) + 2 sum_(s<t) o_s(v) <= a_v + sum_(s<t) deg_s(v), and,
for FIX, a_v + sum_s deg_s(v) - 2 sum_s o_s(v) = z_v.
The implementation uses binary x_e (one iff the first endpoint is the tail),
and continuous auxiliary b(v,t) variables after each incident snapshot:
o_t(v) <= b_previous and b(v,t) = b_previous + deg_t(v) - 2 o_t(v),
starting at a_v. These equalities force b integral. Bounds 0 <= b <= k are
redundant for feasible token walks. Eliminating b recovers the supplied prefix
formulation, while the sparse matrix has O(m) entries. FIX constrains the last
b to z; isolated vertices and empty instances are handled explicitly.

Optional stage 1 calls the existing non-strict pair-flow solver: its NO implies
strict NO. Stage 2 uses SciPy HiGHS MILP with zero objective and a 60 s optimization
limit. A returned incumbent is rounded and checked using exact integer snapshot
counts before acceptance. A feasible incumbent on timeout is YES; no incumbent
on a limit is UNKNOWN. Only a HiGHS infeasibility status or the sound NS filter
produces NO (plus explicit impossible empty/isolated terminal boundaries).
There is no LP feasibility shortcut. SciPy is imported lazily; dependency files
were not changed. time_limit caps optimization, not matrix construction, imports,
NS filtering or witness checking. Timings separate those costs. Witness time
includes construction AND the mandatory independent check; totals include all
solver stages. First-use import overhead appears in build time.

For YES, departures reserve distinct standing tokens before any arrivals are
committed. Witness JSON contains a start vertex and ordered edge IDs per walk,
including empty walks. check_strict_walks independently follows undirected edges,
checks strict time increase, exact use of all IDs, and start/end counts. It uses
no orientation test, solver, or token simulation. Every solver YES asserts this
checker. Each bench JSON contains the full instance, orientation and walks so
witnesses can be checked separately without SciPy.

## Validation

Seed {validation['seed']}: {validation['random_instances']} random tiny instances
(n <= 5, m <= 8), evenly alternating FREE/FIX and cycling general, proper, star,
forest, cycle, maxdeg2 classes, sampled with replacement. General uses unchanged
ilp_seed.rand_inst. Proper/star/forest/maxdeg2 use unchanged classes_seed.gen,
rejecting m > 8; proper maps to matching. Actual simple cycles are explicitly
constructed (the seed maxdeg2 class alone also permits paths), with its maxdeg2
predicate checked. Cycle n is 3..5, one or two snapshots, k is 1..4; other seed
classes use their original distributions. No conditioning on feasibility.
Function AST loading avoids running seed modules' top-level benchmark loops.
{validation['identity_instances']} stratified initial random instances were also
checked with oracle.identity_brute, which assigns edges to distinct labeled
tokens rather than enumerating orientations. {validation['boundary_cases']}
additional boundary cases cover zero tokens, empty graphs, unequal terminal
totals, isolated vertices, parallel edges, negative/unsorted times and simultaneous
arrival reuse. Deliberately invalid witnesses test checker rejection.

Every random case compares BOTH the unfiltered ILP and the default filtered solver
against oracle.decide; every YES witness from both calls is independently checked.
Disagreements: {validation['disagreements']}. NS-YES/strict-NO:
{totals['ns_yes_strict_no']} / {validation['random_instances']}. NS-YES/strict-YES:
{totals['strict_yes']}; NS orientations already satisfying strict inequalities:
{totals['ns_orientation_works']} / {totals['strict_yes']} = {share:.2%}.
This measures potential ILP avoidance; the current solver deliberately still runs
stage 2 for NS-YES to measure and validate the ILP. Rates are generator-specific,
not uniform probabilities over graph classes. Per-class counts and small NS gap
examples are in validation.json.

## Scalability

Each benchmark case runs in its own command. Graphs use scale_seed.planted with
seed 20261101 + configuration index. Ordinary move probability is 0.6; the three
last configurations use 0.9, very few tokens, few vertices and long horizons,
creating several incident edges per vertex per snapshot. Perturbation moves one
random edge to the next time (cyclically); this need not destroy feasibility.
FREE/FIX and planted/perturbed cases share their base graphs. Planted YES is
asserted. Each JSON records full data, including the exact perturbation.

Status counts: {counts}. Limit-status instances:
{sum(r.get('ilp_status') == 1 for r in rows)}. Maximum observed ILP optimization time:
{max((r['timings']['ilp'] for r in rows), default=0):.3f} s.
Planted-YES assertions that failed because optimization returned UNKNOWN:
{sum(r['variant'] == 'planted' and r['status'] != 'YES' for r in rows)}.
These are unsolved known-feasible stress cases, not false NO answers. For these
cases the benchmark files also retain independently checked ground_truth_walks
from the generator, separate from the solver's null witness. Ordinary planted
benchmarks (configuration indices 0..6) must all assert YES. HiGHS' time limit
is best effort: observed optimization time can exceed 60 seconds before control
returns to Python. The outer command timeout is below five minutes.
The planted ground truth is not given to the optimizer as an incumbent, hint,
or objective; the solver still searches with the same zero objective.

{chr(10).join(table)}

## Scope and reproduction

The finite random study is not exhaustive and does not establish the formulation
for all inputs. Large YES answers have independently checked witnesses; large NO
answers have NOT been checked with an exact oracle or an independently verified
infeasibility certificate. NO depends on the existing NS solver or HiGHS. The
independent checker certifies YES only. No external theorem or complexity result
was checked. Timings describe this environment and these seeds, with one trial
per case, no repeated-run confidence intervals, no real datasets and no memory
profiling. Sparse extended formulation equivalence is explained above and tested
against tiny oracles; it is not a new general complexity proof.

worst-case complexity of strict is open; the ILP carries no polynomial guarantee

Environment: Python {platform.python_version()}, SciPy {scipy.__version__}, NumPy
{numpy.__version__}; {platform.platform()}. Full metadata: summary.json.
Measured commands set OPENBLAS_NUM_THREADS=1 and OMP_NUM_THREADS=1. Source
SHA256 hashes are recorded in summary.json. Some small benchmark runs overlapped
the tiny validation workload; timings are observations, not isolated CPU trials.

Run reduced validation (does not overwrite these results):
`python3 experiments/strict/solver.py --self-test`.
Full validation: `python3 experiments/strict/solver_study.py --validate 20000 --identity 2000`.
One benchmark: `python3 experiments/strict/solver_study.py --benchmark 0-FREE-planted`.
Configuration indices 0..9, modes FREE/FIX, variants planted/perturbed.
Rebuild report: `python3 experiments/strict/solver_study.py --report`.
Standalone witness check (stdlib and existing nscover imports only):
`python3 experiments/strict/solver_study.py --check results/strict-solver-20261101/bench-0-FREE-planted.json`.
'''
    (OUT / 'README.md').write_text(text)
    print('\n'.join(table))
    print('Status counts:', counts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validate', type=int)
    parser.add_argument('--identity', type=int, default=2000)
    parser.add_argument('--benchmark')
    parser.add_argument('--report', action='store_true')
    parser.add_argument('--check', type=Path)
    args = parser.parse_args()
    if args.validate:
        data = validate(args.validate, min(args.identity, args.validate), 20261101)
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / 'validation.json').write_text(json.dumps(data, indent=2) + '\n')
        print(json.dumps(data['totals']), '0 disagreements', data['seconds'], 's')
    elif args.benchmark:
        benchmark(args.benchmark)
    elif args.report:
        report()
    elif args.check:
        data = json.loads(args.check.read_text())
        assert data['status'] == 'YES'
        assert check_strict_walks(Instance.from_json(data['instance']), data['walks'])
        print('Witness PASS')
    else:
        parser.error('choose an action')


if __name__ == '__main__':
    main()
