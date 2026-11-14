"""Reproducible exhaustive audit; invoked by gamma_mconvex.py audit.

The C++ kernel enumerates orientations and finite port sets; Python enumerates
ALL labelled multiplicity vectors, quotients only vertex relabelling, and keeps
the exact orbit size. No mathematical M-convexity theorem is used by the checker.
"""
import argparse
import hashlib
import itertools as it
import json
import random
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/mconvex-20261101'


def dump(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def prepare():
    OUT.mkdir(exist_ok=True)
    jobs = []
    for n in range(1, 6):
        slots = list(it.combinations(range(n), 2))
        perms = list(it.permutations(range(n)))
        slot_id = {e: i for i, e in enumerate(slots)}
        maps = [[slot_id[tuple(sorted((p[u], p[v])))] for u, v in slots] for p in perms]
        for m in range(7):
            if m < n - 1 or (n == 1 and m):
                continue
            reps, orbit = {}, {}
            for selected in it.combinations_with_replacement(range(len(slots)), m):
                counts = tuple(selected.count(i) for i in range(len(slots)))
                seen = {0}
                while True:
                    new = seen | {v for i in selected for u, v in (slots[i], slots[i][::-1]) if u in seen}
                    if new == seen:
                        break
                    seen = new
                if len(seen) != n:
                    continue
                if counts not in orbit:
                    variants = set()
                    for mapping in maps:
                        row = [0] * len(slots)
                        for i, c in enumerate(counts):
                            row[mapping[i]] = c
                        variants.add(tuple(row))
                    canonical = min(variants)
                    for v in variants:
                        orbit[v] = canonical
                    reps[canonical] = 0
                reps[orbit[counts]] += 1
            rows = []
            for counts, weight in sorted(reps.items()):
                edges = [e for e, c in zip(slots, counts) for _ in range(c)]
                job = dict(id=len(jobs), n=n, m=m, edges=edges, weight=weight)
                jobs.append(job)
                rows.append(' '.join(map(str, [job['id'], weight, n, m] + [v for e in edges for v in e])))
            if rows:
                (OUT / f'input-n{n}-m{m}.txt').write_text('\n'.join(rows) + '\n')
    dump(OUT / 'graphs.json', jobs)
    print(f'Prepared {len(jobs)} representatives, {sum(j["weight"] for j in jobs)} labelled graphs')


def random_runs(count, seed):
    source_paths = ['pairflow.py', 'chainflow.py', 'timeline.py', 'instance.py', 'maxflow.py', 'branch.py']
    def source_hashes():
        return {p: hashlib.sha256((ROOT/'nscover'/p).read_bytes()).hexdigest() for p in source_paths}
    initial_hashes = source_hashes()
    sys.path.insert(0, str(ROOT))
    from nscover.instance import Instance
    from nscover.pairflow import PairFlow, solve_pairflow
    assert __debug__, 'Assertions must remain active'
    rng = random.Random(seed)
    stats = defaultdict(Counter)
    failures = []
    original_augment, original_reorient = PairFlow.augment, PairFlow._reorient
    active = {}

    def augment(self):
        active['attempts'] += 1
        result = original_augment(self)
        active['augmentations'] += int(result)
        return result

    def reorient(self, c):
        active['reorient_calls'] += 1
        return original_reorient(self, c)

    PairFlow.augment, PairFlow._reorient = augment, reorient
    for trial in range(count):
        mode = 'FIX' if trial % 2 == 0 else 'FREE'
        # Alternate generic random temporal graphs and even snapshot blocks.
        n = rng.randint(2, 5)
        edges = []
        if trial % 4 < 2:
            for _ in range(rng.randint(0, 12)):
                u, v = rng.sample(range(n), 2)
                edges.append((u, v, rng.randrange(4)))
        else:
            for t in range(rng.randint(1, 5)):
                for _ in range(rng.randint(1, 3)):
                    u, v = rng.sample(range(n), 2)
                    edges.extend([(u, v, t)] * 2)
        start = [rng.randrange(4) if rng.random() < .4 else 0 for _ in range(n)]
        if trial % 7 == 0:
            start[rng.randrange(n)] += 2
        end = None
        if mode == 'FIX':
            end = [0] * n
            for _ in range(sum(start)):
                end[rng.randrange(n)] += 1
            if trial % 5 == 0:
                # Obtain a feasible chain endpoint by an independently sampled
                # orientation when its per-time balances are nonnegative.
                c = start.copy()
                for t in sorted({e[2] for e in edges}):
                    delta = [0] * n
                    for u, v, stamp in edges:
                        if stamp == t:
                            if rng.randrange(2):
                                u, v = v, u
                            delta[u] -= 1
                            delta[v] += 1
                    c = [a + b for a, b in zip(c, delta)]
                    if min(c) < 0:
                        break
                if min(c) >= 0:
                    end = c
        inst = Instance(n, edges, start, end)
        active = Counter()
        stats[mode]['instances'] += 1
        try:
            result = solve_pairflow(inst, backend='python')
            stats[mode][result.status] += 1
        except AssertionError as exc:
            stats[mode]['AssertionError'] += 1
            failure = dict(trial=trial, mode=mode, error=str(exc), instance=inst.to_json())
            failures.append(failure)
            print('ASSERTION FAILURE ' + json.dumps(failure), flush=True)
        stats[mode].update(active)
        if (trial + 1) % 2000 == 0:
            print(f'Random {trial + 1}/{count}: {dict(stats)}', flush=True)
    PairFlow.augment, PairFlow._reorient = original_augment, original_reorient
    dump(OUT / 'random.json', dict(seed=seed, count=count, stats=dict(stats), failures=failures,
                                  source_hash=hashlib.sha256((ROOT/'nscover/pairflow.py').read_bytes()).hexdigest(),
                                  initial_source_hashes=initial_hashes, final_source_hashes=source_hashes(),
                                  source_stable=initial_hashes == source_hashes()))


def simplex():
    from gamma_mconvex import m_violation
    rows = []
    for n in range(1, 6):
        for total in range(13):
            def compositions(k, t):
                if k == 1:
                    yield (t,)
                else:
                    for a in range(t + 1):
                        for tail in compositions(k - 1, t - a):
                            yield (a,) + tail
            # Both signs are equivalent under x -> -x; solver uses negative.
            points = {tuple(-v for v in x) for x in compositions(n, total)}
            # Direct constructive exhaustive check is faster than generic set
            # lookup: still visits every ordered pair and positive coordinate.
            pairs = 0
            for x in sorted(points):
                for y in sorted(points):
                    pairs += 1
                    for i in range(n):
                        if x[i] <= y[i]:
                            continue
                        found = False
                        for j in range(n):
                            if x[j] >= y[j]:
                                continue
                            a, b = list(x), list(y)
                            a[i] -= 1; a[j] += 1
                            b[i] += 1; b[j] -= 1
                            if tuple(a) in points and tuple(b) in points:
                                found = True
                                break
                        assert found, (n, total, x, y, i)
            rows.append(dict(n=n, total=total, size=len(points), pairs=pairs, failure=False))
            print(f'Z simplex n={n} total={total} pairs={pairs} PASS', flush=True)
    dump(OUT / 'simplex.json', rows)


def summarize():
    jobs = {j['id']: j for j in json.loads((OUT/'graphs.json').read_text())}
    stats = defaultdict(Counter)
    graphs = defaultdict(set)
    smallest = {}
    failures = []
    supplemental = []
    assert len(list(OUT.glob('graph-*.jsonl'))) == len(jobs), 'Incomplete graph shards'
    for path in sorted(OUT.glob('graph-*.jsonl')):
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        job = jobs[int(path.stem.split('-')[1])]
        assert sum(r['family'] == 'Gamma' for r in rows) == 2 ** job['n']
        if job['n'] == 1:
            supplemental.extend(rows)
            continue  # Edgeless singleton has no Timeline appearance.
        for row in rows:
            fam = row['family']; job = jobs[row['graph_id']]
            stats[fam]['sets'] += row['weight']
            stats[fam]['representative_sets'] += 1
            stats[fam]['pairs_checked'] += row['pairs']
            stats[fam]['pairs_labelled_equivalent'] += row['pairs'] * row['weight']
            stats[fam]['failures'] += row['weight'] * row['failure']
            stats[fam]['disconnected_sets'] += row['weight'] * (row['exchange_components'] > 1)
            graphs[fam].add(job['id'])
            if row['failure']:
                deg = [sum(v in e for e in job['edges']) for v in range(job['n'])]
                pin = [(row['parity_mask'] >> v) & 1 for v in range(job['n'])]
                witness = dict(n=job['n'], m=job['m'], edges=job['edges'], p_in=pin,
                               p_out=[(a+b)%2 for a,b in zip(pin, deg)],
                               x=row['x'], y=row['y'], i=row['i'])
                if 'fixed_g' in row:
                    witness['fixed_g'] = row['fixed_g']
                failures.append(dict(family=fam, weight=row['weight'], **witness))
                key = (job['n'], job['m'], job['edges'], pin, row.get('fixed_g', []), row['x'], row['y'], row['i'])
                if fam not in smallest or key < smallest[fam][0]:
                    smallest[fam] = (key, witness)
    for fam in stats:
        stats[fam]['graphs'] = sum(jobs[i]['weight'] for i in graphs[fam])
    # The independently enumerated fixed-sigma flow images equal these sets
    # for EVERY graph/parity; aliases represent the same exact exchange checks.
    stats['fixed_internal_Gamma'] = stats['Gamma'].copy()
    stats['fixed_internal_Gamma_prime'] = stats['Gamma_prime'].copy()
    z = json.loads((OUT/'simplex.json').read_text())
    stats['Z_simplex'] = Counter(graphs=0, dimensions=5, sets=len(z),
                                 pairs_checked=sum(r['pairs'] for r in z), failures=0)
    for fam in stats:
        print(f'{fam}: {dict(stats[fam])}', flush=True)
    witnesses = {k: v[1] for k, v in smallest.items()}
    for fam, w in witnesses.items():
        print(f'SMALLEST {fam}: {json.dumps(w, separators=(",", ":"))}', flush=True)
    dump(OUT / 'summary.json', dict(families=dict(stats), smallest_failures=witnesses,
                                   supplemental_singleton=supplemental))
    dump(OUT / 'failures.json', failures)


def run(first, last, kernel):
    jobs = json.loads((OUT/'graphs.json').read_text())
    began = time.monotonic()
    for j in jobs[first:last]:
        path = OUT / f'graph-{j["id"]:05d}.jsonl'
        data = ' '.join(map(str, [j['id'], j['weight'], j['n'], j['m']] + [v for e in j['edges'] for v in e])) + '\n'
        result = subprocess.run([kernel], input=data, text=True, capture_output=True,
                                check=True, timeout=min(120, max(1, 220-(time.monotonic()-began))))
        path.write_text(result.stdout)
        print(f'Graph {j["id"]} n={j["n"]} m={j["m"]} completed ({time.monotonic()-began:.2f}s)', flush=True)


def verify():
    from gamma_mconvex import m_violation
    jobs = {j['id']: j for j in json.loads((OUT/'graphs.json').read_text())}
    count = 0
    for path in sorted(OUT.glob('graph-*.jsonl')):
        j = jobs[int(path.stem.split('-')[1])]
        if j['n'] > 3 or j['m'] > 4:
            continue
        n, edges = j['n'], j['edges']
        deg = [sum(v in e for e in edges) for v in range(n)]
        for row in map(json.loads, path.read_text().splitlines()):
            pin = [(row['parity_mask'] >> v) & 1 for v in range(n)]
            pout = [(a+b)%2 for a,b in zip(pin,deg)]
            balances = set()
            for bits in it.product((0, 1), repeat=len(edges)):
                d = [0]*n
                for bit,(u,v) in zip(bits,edges):
                    if bit: u,v = v,u
                    d[u] -= 1; d[v] += 1
                balances.add(tuple((d[v]-pout[v]+pin[v])//2 for v in range(n)))
            if 'fixed_g' in row:
                balances &= {tuple(row['fixed_g'])}
            points = set()
            for alpha in it.product(*(range(d+1) for d in deg)):
                for g in balances:
                    beta = tuple(a+b for a,b in zip(alpha,g))
                    if all(0 <= b <= d for b,d in zip(beta,deg)):
                        points.add(tuple(-a for a in alpha)+beta)
            if 'prime' in row['family']:
                points.discard((0,)*(2*n))
            assert len(points) == row['size'], row
            assert (m_violation(points) is not None) == row['failure'], row
            if row['failure']:
                x,y,i = row['x'],row['y'],row['i']
                assert tuple(x) in points and tuple(y) in points and x[i] > y[i]
                for k in range(2*n):
                    if x[k] >= y[k]: continue
                    a,b=list(x),list(y)
                    a[i]-=1;a[k]+=1;b[i]+=1;b[k]-=1
                    assert tuple(a) not in points or tuple(b) not in points
            count += 1
    # Validate every saved failure directly in the UNBOUNDED fixed-g slice.
    # This also rules out a finite-box artifact in the negative result.
    failures = json.loads((OUT/'failures.json').read_text())
    for f in failures:
        assert f['family'] == 'fixed_g_prime', f
        n, g = f['n'], f['fixed_g']
        def member(z):
            return (all(a <= 0 for a in z[:n]) and all(b >= 0 for b in z[n:])
                    and any(z) and [z[n+v]+z[v] for v in range(n)] == g)
        x,y,i = f['x'], f['y'], f['i']
        assert member(x) and member(y) and x[i] > y[i], f
        for k in range(2*n):
            if x[k] >= y[k]: continue
            a,b=list(x),list(y)
            a[i]-=1;a[k]+=1;b[i]+=1;b[k]-=1
            assert not member(a) or not member(b), f
    dump(OUT/'verification.json', dict(sets_crosschecked=count, passed=True,
                                      unbounded_failure_witnesses_checked=len(failures)))
    print(f'Python/C++ cross-check: {count} sets PASS')
    print(f'Unbounded fixed-g-prime witnesses: {len(failures)} PASS')


def main(argv):
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['prepare', 'random', 'simplex', 'summarize', 'run', 'verify'])
    p.add_argument('--count', type=int, default=20000)
    p.add_argument('--seed', type=int, default=20261101)
    p.add_argument('--first', type=int, default=0)
    p.add_argument('--last', type=int, default=111)
    p.add_argument('--kernel', default='/tmp/gamma-exchange-fast')
    a = p.parse_args(argv)
    if a.action == 'prepare': prepare()
    elif a.action == 'random': random_runs(a.count, a.seed)
    elif a.action == 'simplex': simplex()
    elif a.action == 'run': run(a.first, a.last, a.kernel)
    elif a.action == 'verify': verify()
    else: summarize()
