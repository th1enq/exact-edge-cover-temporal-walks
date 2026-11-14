#!/usr/bin/env python3
"""NO certificates; verifier uses only plain instance fields and the stdlib.

Extraction imports the solver lazily. Checkers do not import solver/timeline code.
Run --self-test (20,000 instances), --coverage, or --verify FILE.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import sys
import time

# Importing the extractor must not write bytecode into the shared nscover tree.
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / 'results/certify-no-20261101'
CATEGORIES = ('independently verified', 'network-relative', 'theory-relative', 'none')


def _require(condition):
    if not condition:
        raise ValueError("invalid certificate state")


def degrees(inst):
    at = [Counter() for _ in range(inst.n)]
    for u, v, t in inst.edges:
        at[u][t] += 1
        at[v][t] += 1
    return at


def counting(inst):
    if inst.end is None:
        return None
    if sum(inst.start) != sum(inst.end):
        return {'kind': 'counting', 'violation': 'total walks'}
    for v, row in enumerate(degrees(inst)):
        d = inst.start[v] + sum(row.values()) - inst.end[v]
        if d < 0 or d % 2 or (not row and d != 0):
            return {'kind': 'counting', 'violation': 'vertex balance', 'vertex': v}
    return None


def bounds(inst):
    at = degrees(inst)
    times, caps = [], []
    for v, row in enumerate(at):
        ts = sorted(row)
        run = inst.start[v]
        cs = []
        h = None if inst.end is None else (run + sum(row.values()) - inst.end[v]) // 2
        for t in ts:
            run += row[t]
            cs.append(run // 2 if h is None else min(run // 2, h))
        times.append(ts)
        caps.append(cs)
    return times, caps


def cut_certificate(inst):
    # Larger endpoint capacities give the same feasibility problem, but ensure
    # a deficient min cut never cuts an edge-to-endpoint arc.
    times, caps = bounds(inst)
    base, size = [], 2 + inst.m
    for ts in times:
        base.append(size)
        size += len(ts)
    arcs = []
    pos = [{t: j for j, t in enumerate(ts)} for ts in times]
    for e, (u, v, t) in enumerate(inst.edges):
        arcs.append((0, 2 + e, 1))
        for w in (u, v):
            arcs.append((2 + e, base[w] + pos[w][t], inst.m + 1))
    for v, cs in enumerate(caps):
        for j, c in enumerate(cs):
            arcs.append((base[v] + j, base[v] + j + 1 if j + 1 < len(cs) else 1, c))
    try:
        # Optional acceleration already used by nscover; no new dependency.
        from scipy.sparse import csr_matrix
        from scipy.sparse.csgraph import maximum_flow
        rows, cols, data = zip(*arcs)
        graph = csr_matrix((data, (rows, cols)), shape=(size, size), dtype='int64')
        result = maximum_flow(graph, 0, 1)
        value = int(result.flow_value)
        residual = (graph - result.flow).tocsr()
        reach, todo = [False] * size, [0]
        reach[0] = True
        while todo:
            a = todo.pop()
            for k in range(residual.indptr[a], residual.indptr[a+1]):
                b = int(residual.indices[k])
                if residual.data[k] > 0 and not reach[b]:
                    reach[b] = True; todo.append(b)
    except ImportError:
        from nscover.maxflow import MaxFlow
        net = MaxFlow(size)
        for a, b, c in arcs:
            net.add(a, b, c)
        value = net.flow(0, 1)
        reach = net.reachable(0)
    if value == inst.m:
        return None
    prefixes = []
    for v, ts in enumerate(times):
        js = [j for j in range(len(ts)) if reach[base[v] + j]]
        prefixes.append(ts[max(js)] if js else None)
    return {'kind': 'prefix cut', 'category': 'independently verified',
            'prefixes': prefixes, 'flow_value': value,
            'raw_cut': [i for i, b in enumerate(reach) if b],
            'network_definition': 'chain-v1-endpoint-m+1',
            'reason': 'chain network'}


def layout(inst):
    """Independent snapshot connectivity, parities and pair port bookkeeping."""
    by = {}
    for e, (_, _, t) in enumerate(inst.edges):
        by.setdefault(t, []).append(e)
    comps, before = [], list(inst.start)
    for t, es in sorted(by.items()):
        parent = {}
        def find(v):
            parent.setdefault(v, v)
            while parent[v] != v:
                v = parent[v]
            return v
        for e in es:
            u, v, _ = inst.edges[e]
            parent[find(u)] = find(v)
        groups = {}
        for e in es:
            groups.setdefault(find(inst.edges[e][0]), []).append(e)
        for _, members in sorted(groups.items()):
            deg = Counter(w for e in members for w in inst.edges[e][:2])
            vs = sorted(deg)
            comps.append({'edges': members, 'vertices': vs,
                          'pin': {v: before[v] % 2 for v in vs},
                          'pout': {v: (before[v] + deg[v]) % 2 for v in vs},
                          'even': all((before[v] | deg[v]) % 2 == 0 for v in vs)})
        for e in es:
            for v in inst.edges[e][:2]:
                before[v] += 1
    size = 2 * inst.n
    prev, nxt = [-1] * size, [-1] * size
    last = list(range(inst.n))
    for c in comps:
        c['base'] = size
        for v in c['vertices']:
            prev.extend([last[v], -1]); nxt.extend([-1, -1])
            nxt[last[v]] = size
            last[v] = size + 1
            size += 2
    for v in range(inst.n):
        prev[inst.n + v] = last[v]
        nxt[last[v]] = inst.n + v
    return comps, prev, nxt, before


def theory_graph(inst, cert):
    """Validate the state, then independently derive every auxiliary arc."""
    comps, prev, nxt, total = layout(inst)
    x, flow, heads = cert['x'], cert['flow'], cert['heads']
    size, n = len(prev), inst.n
    _require(len(x) == len(flow) == size and len(heads) == len(comps))
    _require(all(type(a) is int for a in x + flow))
    _require(all(a >= 0 for a in flow))
    _require(all(flow[i] == 0 for i in range(size) if prev[i] < 0))
    _require(x[:n] == [a // 2 for a in inst.start])
    _require(all(x[n+v] <= 0 for v in range(n)))
    if inst.end is not None:
        _require(all(inst.end[v] % 2 == total[v] % 2 and
                   x[n+v] == -(inst.end[v] - total[v] % 2) // 2 for v in range(n)))
    else:
        _require(sum(-a for a in x[n:2*n]) == (sum(inst.start) - sum(a % 2 for a in total)) // 2)
    graph = [set() for _ in range(size + 1)]
    hub = size
    for i in range(size):
        if prev[i] >= 0:
            graph[i].add(prev[i])
        if nxt[i] >= 0 and flow[nxt[i]] > 0:
            graph[i].add(nxt[i])
    if inst.end is None:
        for v in range(n):
            graph[hub].add(n+v)
            if x[n+v] < 0:
                graph[n+v].add(hub)
    for c, hs in zip(comps, heads):
        vs, b = c['vertices'], c['base']
        _require(len(hs) == len(c['edges']))
        adj = {v: set() for v in vs}
        balance = Counter()
        for e, h in zip(c['edges'], hs):
            u, v, _ = inst.edges[e]
            _require(h in (u, v))
            tail = v if h == u else u
            adj[tail].add(h)
            balance[h] += 1; balance[tail] -= 1
        for j, v in enumerate(vs):
            alpha, beta = -x[b+2*j], x[b+2*j+1]
            _require(alpha >= 0 and beta >= 0)
            _require(balance[v] == 2*(beta-alpha) + c['pout'][v] - c['pin'][v])
        norm = sum(abs(a) for a in x[b:b+2*len(vs)])
        _require(not c['even'] or norm > 0)
        for j, v in enumerate(vs):
            seen, todo = {v}, [v]
            while todo:
                for w in adj[todo.pop()]:
                    if w not in seen:
                        seen.add(w); todo.append(w)
            for si in (0, 1):
                i = b+2*j+si
                if si == 0 and x[i] == 0:
                    continue
                for k, w in enumerate(vs):
                    if w not in seen:
                        continue
                    for sj in (0, 1):
                        q = b+2*k+sj
                        if q == i or (sj == 1 and x[q] == 0):
                            continue
                        if c['even'] and norm + (-1 if si == 0 else 1) + (1 if sj == 0 else -1) == 0:
                            continue
                        graph[i].add(q)
    d = [(flow[nxt[i]] if nxt[i] >= 0 else 0) - flow[i] - x[i] for i in range(size)]
    _require(d == cert['d'] and sum(d) == 0)
    _require(any(a > 0 for a in d))
    return graph, d


def verify_certificate(inst, cert):
    """False on malformed/invalid evidence. No solver or timeline imports here.

    True for theory-relative evidence certifies state/closure only; it does not
    independently prove NO. Read cert['category'] before interpreting the result.
    """
    try:
        if not isinstance(cert, dict):
            return False
        if cert['kind'] == 'counting':
            return cert['category'] == CATEGORIES[0] and counting(inst) == {
                k: v for k, v in cert.items() if k not in ('category', 'reason')}
        if cert['kind'] == 'prefix cut':
            _require(cert['category'] == CATEGORIES[0] and counting(inst) is None)
            ps = cert['prefixes']
            _require(len(ps) == inst.n)
            ts, caps = bounds(inst)
            budget = 0
            for v, t in enumerate(ps):
                if t is not None:
                    _require(type(t) is int and t in ts[v])
                    budget += caps[v][ts[v].index(t)]
            enclosed = sum(ps[u] is not None and ps[v] is not None and t <= ps[u] and t <= ps[v]
                           for u, v, t in inst.edges)
            return enclosed > budget
        if cert['kind'] == 'pair closure':
            _require(cert['category'] == 'theory-relative')
            graph, d = theory_graph(inst, cert)
            r = set(cert['reachable'])
            _require(all(type(i) is int and 0 <= i < len(graph) for i in r))
            _require(all(i in r for i, a in enumerate(d) if a > 0))
            _require(all(i not in r for i, a in enumerate(d) if a < 0))
            return all(graph[i] <= r for i in r)
        return False
    except (AssertionError, KeyError, TypeError, ValueError, IndexError):
        return False


def certificate(inst):
    """Return evidence for a solver NO, otherwise None; no nscover files edited."""
    from nscover.chainflow import ChainNetwork, prefix_caps
    from nscover.pairflow import PairFlow
    from nscover.timeline import Timeline
    c = counting(inst)
    if c:
        return dict(c, category=CATEGORIES[0], reason='counting')
    tl = Timeline(inst)
    root = ChainNetwork(inst, tl, prefix_caps(inst, tl))
    if not root.complete:
        return cut_certificate(inst)
    pf = PairFlow(inst, tl, root.tails())
    while pf.positive:
        if pf.augment():
            continue
        c = {'kind': 'pair closure', 'category': 'theory-relative',
             'reason': 'no augmenting path', 'x': pf.x[:], 'flow': pf.flow[:],
             'heads': pf.heads, 'd': pf.d[:]}
        graph, d = theory_graph(inst, c)
        r = {i for i, a in enumerate(d) if a > 0}
        todo = list(r)
        while todo:
            for j in graph[todo.pop()]:
                if j not in r:
                    r.add(j); todo.append(j)
        c['reachable'] = sorted(r)
        return c
    return None


def random_instance(rng, fixed):
    from nscover.instance import Instance
    n = rng.randint(1, 5)
    edges = []
    for _ in range(rng.randint(0, 7) if n > 1 else 0):
        u, v = rng.sample(range(n), 2)
        edges.append((u, v, rng.randint(0, 3)))
    a = [0] * n
    # Include sparse tokens (dead components) and ample-token YES controls.
    for _ in range(rng.randint(0, 5)):
        a[rng.randrange(n)] += 1
    z = None
    if fixed:
        z = [0] * n
        for _ in range(sum(a) if rng.random() < .9 else rng.randint(0, 5)):
            z[rng.randrange(n)] += 1
    return Instance(n, edges, a, z)


def summary(rows):
    no = [r for r in rows if not r['yes']]
    counts = Counter(r['category'] for r in no)
    return {'instances': len(rows), 'NO': len(no),
            'counts': {c: counts[c] for c in CATEGORIES},
            'independent_fraction': counts[CATEGORIES[0]] / len(no) if no else None,
            'YES_with_certificate': sum(r['yes'] and r['certificate'] is not None for r in rows)}


def evaluate(inst, yes=None):
    c = certificate(inst)
    if c is not None:
        assert verify_certificate(inst, c), (inst.to_json(), c)
    if yes is None:
        yes = c is None
    assert not (yes and c is not None), ('YES received certificate', inst.to_json(), c)
    return {'name': inst.name, 'yes': yes, 'category': c['category'] if c else 'none',
            'instance': inst.to_json(), 'certificate': c}


def save(name, rows, extra=None):
    OUT.mkdir(parents=True, exist_ok=True)
    result = dict(summary(rows), metadata=extra or {}, records=rows)
    (OUT / (name + '.json')).write_text(json.dumps(result, separators=(',', ':')) + '\n')
    print(name, json.dumps(summary(rows)), flush=True)


def self_test():
    from nscover.brute import brute_force
    from nscover.pairflow import solve_pairflow
    rng = random.Random(20261101)
    rows = []
    began = time.monotonic()
    for i in range(20000):
        inst = random_instance(rng, fixed=(i % 2 == 0))
        inst.name = f'soundness-{i}'
        yes = brute_force(inst)
        row = evaluate(inst, yes)
        assert (solve_pairflow(inst).status == 'YES') == yes
        rows.append(row)
        if (i+1) % 5000 == 0:
            print(f'soundness {i+1}/20000: {time.monotonic()-began:.1f}s', flush=True)
        assert time.monotonic() - began < 260, 'internal time budget'
    # Tamper checks: invalid inequality, non-closed set, invalid state must fail.
    for kind in ('counting', 'prefix cut', 'pair closure'):
        examples = [r for r in rows if r['certificate'] and r['certificate']['kind'] == kind]
        assert examples, f'unexercised category {kind}'
        for row in examples[:100]:
            from nscover.instance import Instance
            inst = Instance.from_json(row['instance'])
            c = json.loads(json.dumps(row['certificate']))
            if kind == 'prefix cut':
                c['prefixes'] = [None] * inst.n
            elif kind == 'pair closure':
                c['reachable'] = []
            else:
                c['violation'] = 'invalid'
            assert not verify_certificate(inst, c)
            if kind == 'pair closure':
                for field in ('x', 'flow', 'heads', 'd', 'reachable'):
                    bad = json.loads(json.dumps(row['certificate']))
                    if field == 'heads':
                        bad[field][0][0] = -1
                    elif field == 'reachable':
                        bad[field] = list(range(len(bad['x']) + 1))
                    elif field == 'flow':
                        bad[field][0] = -1
                    else:
                        bad[field][0] += 1
                    assert not verify_certificate(inst, bad), field
    save('soundness', rows, {'by_problem': {mode: summary(rows[offset::2]) for mode, offset in [('FIX', 0), ('FREE', 1)]}, 'seed': 20261101, 'FIX': 10000, 'FREE': 10000,
                           'oracle': 'operational brute_force; every certificate and solver answer checked',
                           'seconds': round(time.monotonic()-began, 3)})


def coverage():
    from nscover.instance import Instance
    from nscover.brute import brute_force
    files = sorted((ROOT / 'practice/cp-temporal-edge-cover/tests').glob('test*/NS_WALK.inp'))
    assert len(files) == 999, len(files)
    rows = []
    provenance = []
    began = time.monotonic()
    for p in files:
        answer = p.with_suffix('.out').read_text().split()[0].upper()
        assert answer in ('YES', 'NO')
        provenance.append({'path': str(p.relative_to(ROOT)), 'answer': answer,
                           'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
        if answer != 'NO':
            continue
        data = list(map(int, p.read_text().split()))
        n, m = data[:2]
        assert len(data) == 2+n+3*m
        edges = [(data[i]-1, data[i+1]-1, data[i+2]) for i in range(2+n, len(data), 3)]
        deg = Counter(w for u, v, _ in edges for w in (u, v))
        inst = Instance(n, edges, [min(a, deg[v]) for v, a in enumerate(data[2:2+n])], name=p.parent.name)
        rows.append(evaluate(inst, False))
        if len(rows) % 50 == 0:
            print(f'practice NO {len(rows)}: {time.monotonic()-began:.1f}s', flush=True)
        assert time.monotonic() - began < 260, 'coverage internal time budget'
    save('practice', rows, {'total_tests': len(files), 'labels': 'NS_WALK.out',
                            'start_capped_at_degree': True, 'inputs': provenance})
    rng = random.Random(20261102)
    rows = []
    for i in range(5000):
        inst = random_instance(rng, True)
        inst.name = f'coverage-fix-{i}'
        rows.append(evaluate(inst, brute_force(inst)))
    save('random-fix', rows, {'seed': 20261102, 'oracle': 'brute_force'})
    historical = []
    for path in sorted((ROOT / 'results/census-20261025').glob('transit*.jsonl')):
        records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        historical.append({'path': str(path.relative_to(ROOT)),
                           'historical_NO': sum(r.get('pair', {}).get('status') == 'NO' for r in records)})
    OUT.joinpath('transit.json').write_text(json.dumps({
        'status': 'skipped', 'measured': False, 'counts': None,
        'reason': 'Historical census stores metrics, not instances; transit loader defaults changed since that run. Exact reconstruction and provenance validation omitted under the optional cheap-only scope.',
        'historical_sources': historical}, indent=2) + '\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--self-test', action='store_true')
    p.add_argument('--coverage', action='store_true')
    p.add_argument('--verify', type=Path)
    a = p.parse_args()
    if a.self_test:
        self_test()
    if a.coverage:
        coverage()
    if a.verify:
        from types import SimpleNamespace
        data = json.loads(a.verify.read_text())
        count = 0
        for r in data['records']:
            if r['certificate']:
                item = r['instance']
                inst = SimpleNamespace(n=item['num_vertices'], edges=[(e['u'], e['v'], e['time']) for e in item['edges']], start=item['start'], end=item.get('end'))
                _require(verify_certificate(inst, r['certificate']))
                count += 1
        print(f'PASS: {count} certificates verified (trust category retained)')
    if not (a.self_test or a.coverage or a.verify):
        p.print_help()

if __name__ == '__main__':
    main()
