"""R1 integral lower-bound circulation and reproducible strict-model study.

Run python3 experiments/strict/relax.py --self-test (stdlib only).
"""
from __future__ import annotations

import argparse
from collections import deque
from itertools import combinations, combinations_with_replacement, product
import json
from pathlib import Path
import random
import time

try:
    from .oracle import Instance, decide, identity_brute, reachable_counts, validate
except ImportError:
    from oracle import Instance, decide, identity_brute, reachable_counts, validate


class Dinic:
    def __init__(self, n):
        self.adj = [[] for _ in range(n)]

    def add(self, u, v, cap):
        a, b = [v, cap, None], [u, 0, None]
        a[2], b[2] = b, a
        self.adj[u].append(a)
        self.adj[v].append(b)

    def flow(self, source, sink):
        total = 0
        while True:
            level = [-1] * len(self.adj)
            level[source] = 0
            queue = deque([source])
            while queue:
                u = queue.popleft()
                for v, cap, _ in self.adj[u]:
                    if cap and level[v] < 0:
                        level[v] = level[u] + 1
                        queue.append(v)
            if level[sink] < 0:
                return total
            pos = [0] * len(self.adj)

            def push(u, amount):
                if u == sink:
                    return amount
                while pos[u] < len(self.adj[u]):
                    edge = self.adj[u][pos[u]]
                    v, cap, rev = edge
                    if cap and level[v] == level[u] + 1:
                        sent = push(v, min(amount, cap))
                        if sent:
                            edge[1] -= sent
                            rev[1] += sent
                            return sent
                    pos[u] += 1
                return 0

            while (sent := push(source, 10**18)):
                total += sent


def feasible_circulation(nodes, arcs):
    net = Dinic(nodes + 2)
    balance = [0] * nodes
    for u, v, lower, upper in arcs:
        if lower < 0 or upper < lower:
            return False
        net.add(u, v, upper - lower)
        balance[u] -= lower
        balance[v] += lower
    demand = 0
    for v, b in enumerate(balance):
        if b > 0:
            net.add(nodes, v, b)
            demand += b
        elif b < 0:
            net.add(v, nodes + 1, -b)
    return net.flow(nodes, nodes + 1) == demand


def r1(inst: Instance) -> bool:
    validate(inst)
    if inst.end is not None and sum(inst.end) != inst.k:
        return False
    # k is a sufficient finite replacement for infinite token capacity.
    cap, arcs, nodes = inst.k, [], 2
    source, sink = 0, 1

    def node():
        nonlocal nodes
        result = nodes
        nodes += 1
        return result

    def arc(u, v, lo=0, hi=None):
        arcs.append((u, v, lo, cap if hi is None else hi))

    ports = {}
    for v in range(inst.n):
        initial = node()
        arc(source, initial, inst.start[v], inst.start[v])
        prev = initial
        for t in sorted({t for u, w, t in inst.edges if v in (u, w)}):
            before, after = node(), node()
            ports[v, t] = before, after
            arc(prev, before)
            arc(before, after)  # token waits through this snapshot
            prev = after
        if inst.end is None:
            arc(prev, sink)
        else:
            arc(prev, sink, inst.end[v], inst.end[v])
    for u, v, t in inst.edges:
        enter, leave = node(), node()
        arc(enter, leave, 1, 1)  # split gadget forces exactly one unit
        for w in (u, v):
            arc(ports[w, t][0], enter, hi=1)
            arc(leave, ports[w, t][1], hi=1)
    arc(sink, source, cap, cap)
    return feasible_circulation(nodes, arcs)


def parity_condition(inst):
    """Global endpoint parity: degree(v) == start(v)+end(v) modulo 2."""
    degree = [0] * inst.n
    for u, v, _ in inst.edges:
        degree[u] += 1
        degree[v] += 1
    residues = [(degree[v] + inst.start[v]) % 2 for v in range(inst.n)]
    if inst.end is not None:
        return sum(inst.end) == inst.k and all(
            inst.end[v] % 2 == residues[v] for v in range(inst.n))
    return sum(residues) <= inst.k and (inst.k - sum(residues)) % 2 == 0


CLASSES = ('general', 'proper', 'forest', 'cycle', 'simple')


def counts(rng, n, k):
    result = [0] * n
    for _ in range(k):
        result[rng.randrange(n)] += 1
    return result


def generate(rng, kind):
    n = rng.randint(3 if kind == 'cycle' else 2, 5)
    k = rng.randrange(5)
    edges = []
    pairs = list(combinations(range(n), 2))
    if kind in ('general', 'simple'):
        m = rng.randint(0, min(8, len(pairs)) if kind == 'simple' else 8)
        selected = rng.sample(pairs, m) if kind == 'simple' else rng.choices(pairs, k=m)
        edges = [(u, v, rng.randrange(4)) for u, v in selected]
    else:
        for t in range(rng.randint(1, 4)):
            if kind == 'cycle':
                vertices = rng.sample(range(n), rng.randint(3, min(n, 8 - len(edges))))
                layer = list(zip(vertices, vertices[1:] + vertices[:1]))
            else:
                parent = list(range(n))
                used, layer = set(), []

                def root(v):
                    while parent[v] != v:
                        v = parent[v]
                    return v

                rng.shuffle(pairs)
                for u, v in pairs:
                    if len(edges) + len(layer) == 8:
                        break
                    allowed = (u not in used and v not in used) if kind == 'proper' else root(u) != root(v)
                    if allowed and rng.random() < 0.5:
                        layer.append((u, v))
                        used.update((u, v))
                        parent[root(u)] = root(v)
            edges.extend((u, v, t) for u, v in layer)
            if len(edges) >= (6 if kind == 'cycle' else 8):
                break
    return Instance(n, edges, counts(rng, n, k), counts(rng, n, k))


def class_ok(inst, kind):
    if kind == 'simple':
        return len({tuple(sorted((u, v))) for u, v, _ in inst.edges}) == inst.m
    for t in {t for _, _, t in inst.edges}:
        layer = [(u, v) for u, v, s in inst.edges if s == t]
        degree, parent = [0] * inst.n, list(range(inst.n))

        def root(v):
            while parent[v] != v:
                v = parent[v]
            return v

        cyclic = False
        for u, v in layer:
            degree[u] += 1
            degree[v] += 1
            if root(u) == root(v):
                cyclic = True
            parent[root(u)] = root(v)
        if kind == 'proper' and max(degree) > 1:
            return False
        if kind == 'forest' and cyclic:
            return False
        if kind == 'cycle':
            active = [v for v, d in enumerate(degree) if d]
            if len(active) < 3 or any(degree[v] != 2 for v in active) or len({root(v) for v in active}) != 1:
                return False
    return True


def vector_compositions(n, k):
    if n == 1:
        yield (k,)
    else:
        for first in range(k + 1):
            for rest in vector_compositions(n - 1, k - first):
                yield (first,) + rest


def small_census():
    """Exhaust n=1..3, m=0..2, k=0..2; canonical contiguous timestamps."""
    gaps, checked, violations = {}, 0, 0
    for n in range(1, 4):
        for m in range(3):
            for pairs in combinations_with_replacement(list(combinations(range(n), 2)), m):
                for times in product(range(m), repeat=m) if m else [()]:
                    if set(times) != set(range(len(set(times)))):
                        continue
                    edges = [(u, v, t) for (u, v), t in zip(pairs, times)]
                    for k in range(3):
                        for a in vector_compositions(n, k):
                            for end in [None] + list(vector_compositions(n, k)):
                                inst = Instance(n, edges, list(a), None if end is None else list(end))
                                exact, relaxed = decide(inst), r1(inst)
                                assert exact == identity_brute(inst), inst.to_json()
                                checked += 1
                                violations += int(exact and not relaxed)
                                assert not exact or relaxed, inst.to_json()
                                if relaxed and not exact:
                                    mode = 'FREE' if end is None else 'FIX'
                                    key = (m, n, k, len(set(times)), edges, a, end or ())
                                    if mode not in gaps or key < gaps[mode][0]:
                                        gaps[mode] = key, inst.to_json()
    return {'decisions': checked, 'violations': violations,
            'domain': 'n=1..3, m=0..2, k=0..2; all canonical timestamp assignments and terminal compositions',
            'smallest_order': 'm,n,k,number of timestamps,edges,start,end',
            'smallest_gaps': {mode: value[1] for mode, value in gaps.items()}}


def study(samples=20000, seed=20261101):
    begin = time.monotonic()
    rng = random.Random(seed)
    cross_checks = 0
    for _ in range(2500):
        inst = generate(rng, 'general')
        for item in (inst.free_end(), inst):
            exact, relaxed = decide(item), r1(item)
            assert exact == identity_brute(item), item.to_json()
            assert relaxed == identity_brute(item, allow_stay=True), item.to_json()
            assert not exact or relaxed, item.to_json()
            cross_checks += 1
    census = small_census()
    rows, examples = [], {}
    for kind in CLASSES:
        tally = {mode: dict(oracle_yes=0, r1_yes=0, gap=0, parity_r1_yes=0,
                            parity_gap=0, violations=0) for mode in ('FREE', 'FIX')}
        for _ in range(samples):
            inst = generate(rng, kind)
            assert class_ok(inst, kind), inst.to_json()
            states = reachable_counts(inst)
            for mode, item in (('FREE', inst.free_end()), ('FIX', inst)):
                exact = bool(states) if mode == 'FREE' else tuple(inst.end) in states
                relaxed = r1(item)
                parity = parity_condition(item)
                assert not exact or parity, item.to_json()
                row = tally[mode]
                row['oracle_yes'] += int(exact)
                row['r1_yes'] += int(relaxed)
                row['gap'] += int(relaxed and not exact)
                row['parity_r1_yes'] += int(relaxed and parity)
                row['parity_gap'] += int(relaxed and parity and not exact)
                row['violations'] += int(exact and not relaxed)
                assert not exact or relaxed, item.to_json()
                if relaxed and not exact:
                    label = kind + '/' + mode
                    key = (item.m, item.n, item.k, len({t for _, _, t in item.edges}))
                    if label not in examples or key < examples[label][0]:
                        examples[label] = key, item.to_json()
                    if parity:
                        examples.setdefault('parity_failure/' + label, (key, item.to_json()))
        for mode, row in tally.items():
            rows.append(dict(graph_class=kind, mode=mode, samples=samples, **row))
        print(f"Completed {kind}: {samples} paired FREE/FIX instances", flush=True)
    return dict(seed=seed, samples_per_class_per_mode=samples,
                oracle_identity_random_decisions=cross_checks, census=census,
                r1_identity_random_decisions=cross_checks,
                rows=rows, examples={key: value[1] for key, value in examples.items()},
                total_necessary_condition_violations=sum(r['violations'] for r in rows) + census['violations'],
                conjecture_proposed=False,
                conjecture_reason='R1 plus endpoint parity still has false positives; no exactness conjecture is proposed.',
                seconds=round(time.monotonic() - begin, 3))


def report(data, directory):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'study.json').write_text(json.dumps(data, indent=2) + '\n')
    header = '| Class | Mode | N | Oracle YES | R1 YES | Gap | R1+parity gap |\n|---|---|---:|---:|---:|---:|---:|'
    table = [header]
    for r in data['rows']:
        table.append('| {graph_class} | {mode} | {samples} | {oracle_yes} | {r1_yes} | {gap} | {parity_gap} |'.format(**r))
    table = '\n'.join(table)
    text = f"""# Strict temporal exact edge-cover study

The experiment uses the strict S model: one edge per token per timestamp,
each edge exactly once, waiting and empty walks allowed. FREE leaves endpoints
unconstrained; FIX prescribes all end counts. There are no loops.

{table}

N counts generated instances, with replacement, in each class and mode; FREE
and FIX share the same graph and start vector. Oracle YES counts exact feasible
instances. R1 YES counts feasible integral lower-bound circulations. Gap counts
R1 YES and oracle NO. R1+parity gap counts false positives after the additional
necessary endpoint-parity test. These are generator-specific frequencies, not
uniform graph-class probabilities. Classes overlap.

Seed: {data['seed']}. Runtime: {data['seconds']} seconds.
Oracle/count DP versus independent labeled-token brute force: {data['oracle_identity_random_decisions']}
random decisions plus {data['census']['decisions']} exhaustive decisions; zero mismatches.
R1 versus independently simulated labeled tokens allowed same-side gadget exits:
{data['r1_identity_random_decisions']} random decisions; zero mismatches.
Oracle YES implies R1 YES violations: {data['total_necessary_condition_violations']}.
Every sampled graph is checked for its claimed class. Every exact YES is also
checked against endpoint parity.

## Sampling scope

n is uniform in 2..5 (3..5 for cycle); k is uniform in 0..4. Starts and FIX
ends independently place k labeled tokens at uniformly chosen vertices, so
count vectors are multinomial, not uniformly distributed. General graphs use
m uniform in 0..8 and independent unordered endpoint pairs with replacement,
then independent timestamps uniform in 0..3. Simple graphs sample globally
distinct unordered pairs without replacement, m uniform in 0..min(8,n choose 2),
then timestamps uniform in 0..3. Thus simple means no repeated pair even across
timestamps, a stronger restriction than snapshot simplicity.

Proper and forest generators select 1..4 candidate timestamps. At each time,
shuffle all unordered pairs and accept each eligible pair with probability 1/2,
subject to the matching/acyclic restriction and total m <= 8. Empty candidate
snapshots have no effect. The cycle generator chooses 1..4 candidate timestamps,
each with a randomly ordered simple cycle on 3..min(n,remaining edge budget)
vertices plus isolates; stop once m >= 6, ensuring m <= 8. Cycles are length
at least three, so two parallel edges are not sampled as a cycle. Across times,
pairs may repeat outside the simple class. No conditioning on feasibility is used.

## Small gap witnesses

The following witnesses are smallest under the recorded census ordering
(m,n,k,number of timestamps,edges,start,end), in the exhaustive domain
{data['census']['domain']}. Isomorphic vertices are not quotiented.

"""
    for mode, inst in data['census']['smallest_gaps'].items():
        text += f"{mode}: `{json.dumps(inst, sort_keys=True)}`\n\n"
    text += """For FREE, one token begins at the center of two edges at successive
timestamps. A strict traversal of the first edge strands it at a leaf, while
R1 permits it to return to the center through the same edge gadget and use
the second edge. For FIX, a single edge with one token required to end at its
starting endpoint already exposes the same-side exit allowed by R1.

R1 is not exact even on proper graphs: both witnesses have matching snapshots.
Polynomial solvability of the proper class does not imply exactness of this
particular relaxation. The cited AAAI corollary is user-supplied context and was
not independently verified here.

## Construction and additional condition

Each edge gadget has a split arc with lower=upper=1 and four endpoint port
arcs. Each vertex has a wait arc from before to after each incident timestamp,
wait arcs between successive incident timestamps, and exact start supply.
The final arc has exact FIX demand or free capacity; isolated vertices have
direct waiting paths. k replaces infinity, since only k tokens circulate.
An integral lower-bound circulation is reduced to integral max flow with
super source/sink and an exact k-unit sink-to-source return arc.
Every strict traversal maps to a cross-side gadget traversal, giving necessity.
The count oracle tests all simultaneous orientations with departures bounded
by pre-snapshot token counts; this prevents reuse of snapshot arrivals.
The independent brute force assigns distinct labeled tokens to snapshot edges.

Endpoint parity requires degree(v) = start(v)+end(v) mod 2. For FREE this
means the sum of required end parities is at most k (and the remaining count
is even). R1 plus this condition still has false positives: see parity_failure
examples below, reproduced verbatim from the machine-readable results.
No condition tested closed all gaps, so no exactness CONJECTURE is proposed
and the conditional further 20,000-instance conjecture test does not apply.
No tighter plain-flow gadget was established. Simply using separate directed
cross arcs loses the shared exactly-one-use constraint on an undirected edge;
it is not an asserted replacement.

"""
    for label, inst in data['examples'].items():
        if label.startswith('parity_failure/'):
            text += f"{label}: `{json.dumps(inst, sort_keys=True)}`\n\n"
    text += """## Limitations

No large instances, loops, nonintegral supplies, more than four tokens, or more
than eight edges were tested. Random sampling does not exhaust the listed
classes. FIX experiments use equal start/end totals; regression checks also
cover unequal totals. The small census exhausts only its stated bounds and
canonical time labels; no general minimality theorem is claimed. No other
flow relaxations or systematic search over extra conditions was performed.
No complexity theorem or external corollary was verified. no complexity claim is made.

Reproduce: `python3 experiments/strict/relax.py --self-test`.
This rewrites only study.json and README.md in the default results directory.
Individual instances can be checked with `--instance path/to/instance.json`.
"""
    (directory / 'README.md').write_text(text)
    print(table)
    print(f"Oracle YES implies R1 YES: {data['total_necessary_condition_violations']} violations")
    for mode, inst in data['census']['smallest_gaps'].items():
        print(f'Smallest census {mode} gap: {json.dumps(inst, sort_keys=True)}')
    print(data['conjecture_reason'])


def regressions():
    cases = [
        (Instance(1, [], [0]), True, True),
        (Instance(1, [], [2], [2]), True, True),
        (Instance(2, [], [1, 0], [0, 1]), False, False),
        (Instance(1, [], [1], [0]), False, False),
        (Instance(2, [(0, 1, -3)], [1, 0], [0, 1]), True, True),
        (Instance(2, [(0, 1, 0)], [1, 0], [1, 0]), False, True),
        (Instance(3, [(0, 1, 0), (0, 2, 1)], [1, 0, 0]), False, True),
        (Instance(3, [(0, 1, 0), (1, 2, 0)], [1, 0, 0]), False, False),
        (Instance(2, [(0, 1, 0)] * 2, [2, 0], [0, 2]), True, True),
        (Instance(2, [(0, 1, 0)] * 2, [1, 0]), False, False),
        (Instance(3, [(0, 1, 0), (1, 2, 100)], [1, 0, 0], [0, 0, 1]), True, True),
    ]
    for inst, exact, relaxed in cases:
        assert decide(inst) == identity_brute(inst) == exact, inst.to_json()
        assert r1(inst) == relaxed, inst.to_json()
    print(f'Regressions: {len(cases)} passed', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--samples', type=int, default=20000)
    parser.add_argument('--seed', type=int, default=20261101)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[2] / 'results/strict-20261101')
    parser.add_argument('--instance', type=Path)
    args = parser.parse_args()
    if args.self_test:
        if args.samples < 1:
            parser.error('--samples must be positive')
        regressions()
        report(study(args.samples, args.seed), args.output)
    elif args.instance:
        inst = Instance.load(args.instance)
        print(json.dumps(dict(oracle=decide(inst), r1=r1(inst), parity=parity_condition(inst))))
    else:
        parser.error('choose --self-test or --instance')


if __name__ == '__main__':
    main()
