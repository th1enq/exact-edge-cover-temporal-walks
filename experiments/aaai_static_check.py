#!/usr/bin/env python3
"""The static reduction of Deligkas et al. (AAAI 2025, Thm 6.3; arXiv 2408.17107,
Thm 6.2 with Definition 6.3 and Lemma 6.5) on one instance with an even component.

Vertices x, u, y, v, w; edges {x,u}, {u,y} at time 1 and the triangle u, v, w at time
2; one walk from x to y.  The walk is at y after time 1, so the triangle (an even
component) holds no walk and the instance is infeasible.  The mixed
multigraph S of Definition 6.3 nevertheless has a static walk exact edge-cover from s
to e: it enters the triangle at u_2 and returns to u_1 over the undirected gadget edge.
The suffix switch of Lemma 6.5 needs a second walk W2 on the directed edge (u_1, u_2);
here that walk is W1 itself, and switching with it only detaches the triangle as a
cycle without a walk.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nscover import Instance, brute_force, solve_branch, solve_pairflow  # noqa: E402

X, U, Y, V, W = range(5)
EDGES = [(0, X, U, 1), (1, U, Y, 1), (2, U, V, 2), (3, V, W, 2), (4, W, U, 2)]
START, END = [1, 0, 0, 0, 0], [0, 0, 1, 0, 0]


def static_graph(edges, start, end):
    """Definition 6.3: terminal edges at times 0 and t_max + 1, one gadget vertex per
    label, min(deg <= t, deg > t) edges between consecutive labels, ceil half directed."""
    last = max(t for *_, t in edges) + 1
    temporal = list(edges)
    for v, count in enumerate(start):
        temporal += [(None, ("s", v, i), v, 0) for i in range(count)]
    for v, count in enumerate(end):
        temporal += [(None, v, ("e", v, i), last) for i in range(count)]
    labels: dict = {}
    for _, a, b, t in temporal:
        for z in (a, b):
            labels.setdefault(z, set()).add(t)
    arcs = [((a, t), (b, t), False) for _, a, b, t in temporal]
    for z, times in labels.items():
        times = sorted(times)
        for t, following in zip(times, times[1:]):
            before = sum(1 for _, a, b, s in temporal if z in (a, b) and s <= t)
            after = sum(1 for _, a, b, s in temporal if z in (a, b) and s > t)
            alpha = min(before, after)
            arcs += [((z, t), (z, following), i < (alpha + 1) // 2) for i in range(alpha)]
    return arcs


def single_walk_cover(arcs, source, target):
    """A static walk from source to target using every arc once (directed arcs forward)."""
    def extend(at, used, path):
        if len(used) == len(arcs):
            return path if at == target else None
        for i, (p, q, directed) in enumerate(arcs):
            if i in used:
                continue
            for a, b in [(p, q)] if directed else [(p, q), (q, p)]:
                if a == at:
                    found = extend(b, used | {i}, path + [b])
                    if found:
                        return found
        return None

    return extend(source, frozenset(), [source])


def main() -> None:
    inst = Instance(5, [(a, b, t) for _, a, b, t in EDGES], START, END)
    temporal = brute_force(inst)
    status = {"pairflow": solve_pairflow(inst).status, "branch": solve_branch(inst).status}
    arcs = static_graph(EDGES, START, END)
    last = max(t for *_, t in EDGES) + 1
    walk = single_walk_cover(arcs, (("s", X, 0), 0), (("e", Y, 0), last))
    print("temporal non-strict walk cover (brute force):", temporal)
    print("solvers:", status)
    print("static walk cover of S:", walk)
    assert not temporal and set(status.values()) == {"NO"} and walk is not None


if __name__ == "__main__":
    main()
