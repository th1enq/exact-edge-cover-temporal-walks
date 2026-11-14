"""Seeded random instances for testing."""

from __future__ import annotations

import random

from .instance import Instance


def random_instance(rng: random.Random, max_n: int = 5, max_m: int = 8) -> Instance:
    n, m = rng.randint(2, max_n), rng.randint(1, max_m)
    horizon = rng.randint(1, 4)
    edges = []
    for _ in range(m):
        u, v = rng.sample(range(n), 2)
        edges.append((u, v, rng.randint(1, horizon)))
    return Instance(n, edges, [rng.randint(0, rng.randint(1, 2)) for _ in range(n)])


def cycle_instance(rng: random.Random, max_n: int = 6, max_snapshots: int = 4) -> Instance:
    """Snapshots made of short cycles and single edges, so even components are common."""
    n = rng.randint(3, max_n)
    edges = []
    for t in range(1, rng.randint(2, max_snapshots) + 1):
        for _ in range(rng.randint(1, 2)):
            if rng.random() < 0.6:
                cycle = rng.sample(range(n), rng.randint(2, min(4, n)))
                if len(cycle) == 2:
                    edges += [(cycle[0], cycle[1], t)] * 2
                else:
                    edges += [(cycle[i], cycle[(i + 1) % len(cycle)], t) for i in range(len(cycle))]
            else:
                u, v = rng.sample(range(n), 2)
                edges.append((u, v, t))
    start = [rng.choice((0, 0, 1, 2)) for _ in range(n)]
    if not any(start):
        start[rng.randrange(n)] = 1
    return Instance(n, edges, start)


def random_end(rng: random.Random, inst: Instance) -> list[int]:
    """End counts of a random greedy run when it succeeds (often feasible), else random."""
    tokens = list(inst.start)
    ok = True
    for t in sorted({t for _, _, t in inst.edges}):
        snapshot = [(u, v) for u, v, s in inst.edges if s == t]
        rng.shuffle(snapshot)
        for u, v in snapshot:
            sides = [(x, y) for x, y in ((u, v), (v, u)) if tokens[x]]
            if not sides:
                ok = False
                break
            x, y = rng.choice(sides)
            tokens[x] -= 1
            tokens[y] += 1
        if not ok:
            break
    if ok and rng.random() < 0.7:
        return tokens
    end = [0] * inst.n
    for _ in range(inst.k):
        end[rng.randrange(inst.n)] += 1
    return end
