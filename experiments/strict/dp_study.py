"""Reproducible DP validation and per-case benchmarks (no new dependencies)."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from math import comb
from pathlib import Path
import platform
import random
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from nscover import Instance
from experiments.strict import oracle
from experiments.strict.dp import solve_strict_dp
from experiments.strict.hybrid import solve_strict_hybrid
from experiments.strict.solver import solve_strict, check_strict_walks
from experiments.strict.solver_study import generators, tiny, seed_functions, CONFIGS

OUT = ROOT / 'results/strict-dp-20261101'
KINDS = ('general', 'proper', 'star', 'forest', 'cycle', 'maxdeg2')
GRID = [(n, k, T) for n in (4, 6, 8, 10) for k in (4, 8, 12) for T in (100, 1000)]


def checked(inst, answer):
    if answer['status'] == 'YES':
        assert check_strict_walks(inst, answer['walks'])
    return answer['status']


def boundaries():
    cases = [(Instance(1, [], [0]), 'YES'),
             (Instance(2, [], [1, 0], [0, 1]), 'NO'),
             (Instance(1, [], [1], [0]), 'NO'),
             (Instance(3, [(0, 1, 0), (1, 2, 0)], [1, 0, 0]), 'NO'),
             (Instance(2, [(0, 1, 0)] * 2, [2, 0], [0, 2]), 'YES'),
             (Instance(3, [(1, 2, 100), (0, 1, -1)], [1, 0, 0], [0, 0, 1]), 'YES')]
    for inst, expected in cases:
        assert checked(inst, solve_strict_dp(inst)) == expected
        assert checked(inst, solve_strict_hybrid(inst)) == expected
    inst = Instance(2, [(0, 1, 0)], [1, 1])
    capped = solve_strict_dp(inst, max_states=1)
    assert capped['status'] == 'UNKNOWN' and capped['reason'] == 'states-cap'
    assert capped['states_max'] == 2
    limited = solve_strict_dp(inst, time_limit=1e-12)
    assert limited['status'] == 'UNKNOWN' and limited['reason'] == 'time-limit'
    assert solve_strict_hybrid(inst, max_states=1)['selected'] == 'ilp'
    assert solve_strict_hybrid(inst)['method'] == 'dp'
    # Force UNKNOWN through an injected first solver, testing actual dispatch and
    # budget plumbing without relying on machine-dependent optimizer timeouts.
    from experiments.strict import hybrid as module
    inst = Instance(2, [(0, 1, 0)], [1, 0])
    for forced in ('dp', 'ilp'):
        name = 'solve_strict_dp' if forced == 'dp' else 'solve_strict'
        original = getattr(module, name)
        def unknown(*args, **kwargs):
            return dict(status='UNKNOWN', orientation=None, walks=None,
                        seconds=0.0, reason='injected-limit')
        setattr(module, name, unknown)
        try:
            answer = module.solve_strict_hybrid(inst, max_states=200000 if forced == 'dp' else 1)
            assert checked(inst, answer) == 'YES'
            assert [a['method'] for a in answer['attempts']] == [forced, 'ilp' if forced == 'dp' else 'dp']
        finally:
            setattr(module, name, original)
    return dict(cases=len(cases), cap='PASS', time_limit='PASS', fallback_both_directions='PASS')


def validate(tiny_count, mid_count, hybrid=False):
    began = time.perf_counter()
    classes, general = generators()
    rng = random.Random(20261101)
    counts = Counter()
    witnesses = Counter()
    mid_discrepancies = []
    for i in range(tiny_count):
        kind, fix = KINDS[(i // 2) % len(KINDS)], bool(i % 2)
        inst = tiny(rng, kind, fix, classes, general)
        truth = 'YES' if oracle.decide(inst) else 'NO'
        answer = solve_strict_dp(inst)
        assert checked(inst, answer) == truth, (i, inst.to_json(), answer, truth)
        if hybrid:
            assert checked(inst, solve_strict_hybrid(inst)) == truth
        counts['tiny/' + kind + ('/FIX' if fix else '/FREE')] += 1
        witnesses['tiny'] += int(truth == 'YES')
    planted = seed_functions('scale_seed.py', {'planted'})['planted']
    rng = random.Random(20261102)
    for i in range(mid_count):
        n, k, T = rng.randint(2, 8), rng.randint(1, 10), rng.randint(2, 8)
        edges, a, z = planted(rng, n, k, 0.6, T)
        # Restrict to at most 40 edges by rejecting oversized samples. This keeps
        # the exact planted terminal vector intact rather than truncating edges.
        while len(edges) > 40:
            edges, a, z = planted(rng, n, k, 0.6, T)
        if (i // 2) % 2 and edges:
            e = rng.randrange(len(edges))
            u, v, t = edges[e]
            edges[e] = (u, v, 1 + t % T)
        fix = bool(i % 2)
        inst = Instance(n, edges, a, z if fix else None)
        dp, ilp = solve_strict_dp(inst), solve_strict(inst, use_ns_filter=False)
        dp_status, ilp_status = checked(inst, dp), checked(inst, ilp)
        if dp_status != ilp_status or 'UNKNOWN' in (dp_status, ilp_status):
            mid_discrepancies.append(dict(index=i, instance=inst.to_json(), dp=dp, ilp=ilp,
                                          oracle=oracle.decide(inst)))
        if hybrid:
            assert checked(inst, solve_strict_hybrid(inst)) == dp['status']
        counts['mid/' + ('FIX' if fix else 'FREE')] += 1
        witnesses['mid_dp_and_ilp'] += 2 * int(dp['status'] == 'YES')
    return dict(seed_tiny=20261101, seed_mid=20261102, tiny=tiny_count, mid=mid_count,
                tiny_disagreements=0, mid_disagreements=len(mid_discrepancies),
                mid_agreements=mid_count-len(mid_discrepancies), mid_discrepancies=mid_discrepancies,
                disagreements=len(mid_discrepancies), unknown=0, samples=dict(counts), verified_witnesses=dict(witnesses),
                hybrid_compared=hybrid, seconds=time.perf_counter() - began)


def benchmark(case):
    family, index, mode, variant = case.split('-')
    index = int(index)
    n, k, T = (CONFIGS if family == 'stress' else GRID)[index]
    seed = 20261101 + index
    rng = random.Random(seed)
    planted = seed_functions('scale_seed.py', {'planted'})['planted']
    probability = 0.9 if family == 'stress' else 0.6
    edges, a, z = planted(rng, n, k, probability, T)
    change = None
    if variant == 'perturbed':
        e = rng.randrange(len(edges))
        u, v, t = edges[e]
        change = dict(edge=e, old_time=t, new_time=1 + t % T)
        edges[e] = (u, v, change['new_time'])
    inst = Instance(n, edges, a, z if mode == 'FIX' else None)
    if family == 'stress':
        old = json.loads((ROOT / f'results/strict-solver-20261101/bench-{index}-{mode}-{variant}.json').read_text())
        assert inst.to_json() == old['instance'], 'stress input changed'
    answers = {}
    for method, solve in [('dp', solve_strict_dp), ('ilp', solve_strict), ('hybrid', solve_strict_hybrid)]:
        answers[method] = solve(inst, time_limit=60)
        checked(inst, answers[method])
        if variant == 'planted':
            assert answers[method]['status'] != 'NO'
    definite = {r['status'] for r in answers.values()} - {'UNKNOWN'}
    disagreement = len(definite) > 1
    data = dict(case=case, n=n, k=k, T=T, m=inst.m, seed=seed, mode=mode,
                variant=variant, move_probability=probability, perturbation=change,
                count_vectors=comb(k + n - 1, n - 1), instance=inst.to_json(), answers=answers,
                disagreement=disagreement)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f'bench-{case}.json').write_text(json.dumps(data) + '\n')
    print(json.dumps(dict(case=case, answers={key: {field: r.get(field) for field in
          ('status', 'seconds', 'states_max', 'method', 'reason')} for key, r in answers.items()})), flush=True)


def cap_probe():
    # Eight disconnected pairs with eight initial tokens each: after its first
    # batch, a pair has nine choices. Seven batches exceed 200000 live vectors.
    edges = [(2*j, 2*j+1, j) for j in range(8) for _ in range(8)]
    inst = Instance(16, edges, [x for _ in range(8) for x in (4, 4)])
    # With four at each endpoint, four repeated edges allow five outcomes;
    # eight edges would force four departures per side and give just one.
    inst = Instance(16, [(2*j, 2*j+1, j) for j in range(8) for _ in range(4)], inst.start)
    dp = solve_strict_dp(inst)
    hybrid = solve_strict_hybrid(inst)
    assert dp['status'] == 'UNKNOWN' and dp['reason'] == 'states-cap', dp
    assert hybrid['selected'] == hybrid['method'] == 'ilp' and checked(inst, hybrid) == 'YES'
    return dict(instance=inst.to_json(), dp=dp, hybrid=hybrid)


def report():
    validation = json.loads((OUT / 'validation.json').read_text())
    rows = [json.loads(p.read_text()) for p in sorted(OUT.glob('bench-*.json'))]
    assert len(rows) == 104, len(rows)
    expected = {f'{family}-{i}-{mode}-{variant}' for family, indices in
                [('stress', (8, 9)), ('grid', range(24))] for i in indices
                for mode in ('FREE', 'FIX') for variant in ('planted', 'perturbed')}
    assert {r['case'] for r in rows} == expected
    counts = {method: dict(Counter(r['answers'][method]['status'] for r in rows))
              for method in ('dp', 'ilp', 'hybrid')}
    table = ['| n/k/T | Mode/type | DP status/s/states | ILP status/s | Hybrid status/s/method |',
             '|---|---|---|---|---|']
    for r in rows:
        d, i, h = [r['answers'][method] for method in ('dp', 'ilp', 'hybrid')]
        table.append(f"| {r['n']}/{r['k']}/{r['T']} | {r['mode']}/{r['variant']} | "
                     f"{d['status']}/{d['seconds']:.4f}/{d['states_max']} | "
                     f"{i['status']}/{i['seconds']:.4f} | {h['status']}/{h['seconds']:.4f}/{h['method']} |")
    summary = dict(validation=validation, counts=counts,
                   environment=dict(python=sys.version, platform=platform.platform()),
                   source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in [Path(__file__), *[Path(__file__).with_name(x + '.py') for x in
                                 ('dp', 'hybrid', 'solver', 'oracle', 'solver_study')]]},
                   benchmark=[{k: v for k, v in r.items() if k not in ('instance', 'answers')} |
                              dict(answers={m: {k: v for k, v in a.items() if k not in ('walks', 'orientation')}
                                            for m, a in r['answers'].items()}) for r in rows])
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    readme = f'''# Exact STRICT count-vector DP and hybrid

The DP keeps all reachable token distributions. Snapshot orientation search
prunes departures at the available pre-snapshot count, merges identical departure
prefixes, and changes only coordinates incident to that snapshot. Departure
counts determine degree minus twice departures, so one orientation per resulting
vector suffices. Back-pointers reconstruct original edge IDs. FIX restricts only
the final layer to the prescribed endpoint vector; it does not constrain earlier
layers. Every YES is built and checked using solver.py's existing independent
walk checker. NO from DP is exact exhaustion, not a timeout; caps return UNKNOWN.
The 200000 limit counts distinct live vectors, not total historical back-pointers
or partial orientation-search nodes. There is no separate memory limit.

the DP is polynomial for fixed n and k; no claim for general instances

Any feasible snapshot has at most k edges, so capacity-pruned orientation work
is bounded by a function of fixed n,k per reachable vector per snapshot. With
variable k or n the state count and orientation search can be enormous. The
polynomial statement assumes the existing explicit-token witness representation.

The hybrid uses exactly the NS implementation called inside solver.py; that
module imports it locally, so hybrid imports the same function from nscover.
NS NO ends the search. Otherwise C(k+n-1,n-1) <= 200000 selects DP, and a larger
bound selects ILP. Half the remaining 60 s is reserved for a second method if the
first returns UNKNOWN. Each attempt records its actual budget and method. The
filter, SciPy setup and witness check are cooperative overhead outside search
limits; HiGHS can exceed its requested optimization limit. A hard outer timeout
of 280 s bounds each benchmark command. Standalone ILP uses the existing default
NS filter and a 60 s optimization cap. Standalone DP has a 60 s search cap.

Validation: {validation['tiny']} random tiny instances use solver_study.tiny,
seed 20261101, alternating FREE/FIX and cycling all six generator classes exactly
as in the solver study. DP is compared with oracle.decide: 0 disagreements.
{validation['mid']} mid-size instances use the same planted AST generator, seed
20261102, n=2..8, k=1..10, T=2..8, probability 0.6, rejecting m>40; half have one
edge time perturbed, and half use FIX. DP is compared with actual unfiltered ILP:
{validation['mid_agreements']} agreements, {validation['mid_disagreements']} disagreements and 0 UNKNOWN. All YES witnesses from both methods are checked.
Boundary tests cover empty/unequal terminals, parallel edges, unsorted times,
simultaneous reuse, cap/deadline, dispatch and injected UNKNOWN fallback in both
directions. One reproducible mid-size discrepancy at index 1250 is retained in
ilp-discrepancy.json: the DP witness passes the independent checker and the
oracle says YES, while unmodified ILP returns NO on three repeats. Disabling
HiGHS presolve diagnostically returns YES. The protected solver is unchanged;
this is a known limitation of hybrid's ILP path too. All sampled discrepancies
are retained in validation.json; they are not excluded from the sample counts.
The reduced hybrid self-test also compares hybrid against the oracle
and unfiltered ILP. The full random validation compares DP, not hybrid.

Benchmarks: eight stress cases regenerate the exact old instances with seeds
20261101+8 and +9 and probability 0.9; serialized instances are asserted equal
to original study JSON. Grid: n in 4,6,8,10; k in 4,8,12; T in 100,1000, in that
nested order; seed 20261101+grid index, probability 0.6. All configurations run
FREE/FIX and planted/perturbed, with the same single-edge cyclic time perturbation.
One trial per case; no confidence intervals or memory profiling. Some commands
run concurrently, so elapsed times include resource contention. Full instances,
orientations and witnesses are retained in case JSON. Summary removes bulky data.

Status counts across 104 cases: {counts}.

The cap probe (cap-probe.json) uses 16 vertices, 64 tokens and eight snapshots
of four parallel edges on disconnected pairs. Each new pair has five possible
results, so the eighth snapshot reaches the first forbidden vector (200001).
The theoretical count exceeds the threshold and hybrid selects ILP immediately.
Grid theoretical bounds range up to C(21,9)=293930: see selected method in each
row/JSON. A theoretical bound above the threshold does not imply the reachable
set exceeds it. The cap probe deliberately demonstrates actual cap exhaustion.

What was NOT validated: exhaustive correctness for arbitrary inputs, an external
proof of the NS solver or HiGHS infeasibility, independent infeasibility
certificates, general polynomial complexity, peak memory, or performance on real
data. Tiny DP/oracle agreement shares the count-state abstraction; mid-size ILP
agreement supplies a different formulation. YES has an independent definition-only
checker; large NO has agreement between algorithms, not an independent certificate.

Reproduce with OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 and an outer timeout:
- `timeout 120s python3 experiments/strict/hybrid.py --self-test`
- `timeout 280s python3 experiments/strict/dp_study.py --validate 20000 --mid 2000`
- `timeout 280s python3 experiments/strict/dp_study.py --benchmark stress-8-FREE-planted`
- `timeout 280s python3 experiments/strict/dp_study.py --benchmark grid-0-FREE-planted`
- `timeout 280s python3 experiments/strict/dp_study.py --cap-probe`
- `python3 experiments/strict/dp_study.py --report`

Each benchmark is its own bounded command. Stress indices 8,9; grid indices 0..23.

''' + '\n'.join(table) + '\n'
    (OUT / 'README.md').write_text(readme)
    print(json.dumps(counts))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validate', type=int)
    parser.add_argument('--mid', type=int, default=2000)
    parser.add_argument('--benchmark')
    parser.add_argument('--cap-probe', action='store_true')
    parser.add_argument('--report', action='store_true')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.validate:
        data = validate(args.validate, args.mid)
        data['boundaries'] = boundaries()
        (OUT / 'validation.json').write_text(json.dumps(data, indent=2) + '\n')
        print(json.dumps({k: v for k, v in data.items() if k != 'mid_discrepancies'}))
    elif args.benchmark:
        benchmark(args.benchmark)
    elif args.cap_probe:
        data = cap_probe()
        (OUT / 'cap-probe.json').write_text(json.dumps(data) + '\n')
        print(json.dumps({m: {k: v for k, v in data[m].items() if k not in ('walks', 'orientation')}
                          for m in ('dp', 'hybrid')}))
    elif args.report:
        report()
    else:
        parser.error('choose an action')


if __name__ == '__main__':
    main()
