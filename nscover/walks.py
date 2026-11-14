"""Witnesses: build explicit walks from an orientation, and check walks independently.

``build_walks`` follows the sufficiency proof of the characterisation: per component,
add r dummy arcs from deficit to surplus vertices (r = total surplus), take an Euler
circuit, and cut it at the dummy arcs into r trails; with r = 0 the whole circuit is one
closed trail, started at a vertex that holds a walk.  Every trail is taken by a walk
that was at its first vertex before the time step.

``check_walks`` uses nothing but the instance and the walks.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from .instance import Instance
from .timeline import Timeline

Walk = tuple[int, list[int]]  # (start vertex, edge indices in order)


class InfeasibleOrientation(ValueError):
    pass


def _euler_circuit(start: int, arcs: list[tuple[int, int]]) -> list[int]:
    """Arc ids of an Euler circuit from ``start`` in a balanced, connected digraph."""
    out: dict[int, list[int]] = defaultdict(list)
    for i, (a, _) in enumerate(arcs):
        out[a].append(i)
    stack: list[tuple[int, int]] = [(start, -1)]
    circuit: list[int] = []
    while stack:
        vertex, arc = stack[-1]
        if out[vertex]:
            nxt = out[vertex].pop()
            stack.append((arcs[nxt][1], nxt))
        else:
            stack.pop()
            if arc >= 0:
                circuit.append(arc)
    circuit.reverse()
    if len(circuit) != len(arcs):
        raise InfeasibleOrientation("component digraph is not connected")
    return circuit


def build_walks(inst: Instance, tails: list[int], tl: Timeline | None = None) -> list[Walk]:
    tl = tl or Timeline(inst)
    walks: list[Walk] = []
    here: list[list[int]] = [[] for _ in range(inst.n)]
    for v, count in enumerate(inst.start):
        for _ in range(count):
            here[v].append(len(walks))
            walks.append((v, []))
    for comp in tl.components:
        arcs: list[tuple[int, int]] = []
        real: list[int] = []
        surplus: Counter = Counter()
        for e in comp.edges:
            u, v, _ = inst.edges[e]
            tail = tails[e]
            head = v if tail == u else u
            arcs.append((tail, head))
            real.append(e)
            surplus[tail] += 1
            surplus[head] -= 1
        givers = [x for x in comp.vertices for _ in range(max(0, surplus[x]))]
        takers = [x for x in comp.vertices for _ in range(max(0, -surplus[x]))]
        for taker, giver in zip(takers, givers):
            arcs.append((taker, giver))  # dummy arc, id >= len(real)
        if givers:
            circuit = _euler_circuit(takers[0], arcs)
            cut = next(i for i, a in enumerate(circuit) if a >= len(real))
            circuit = circuit[cut + 1:] + circuit[:cut + 1]
            trails, current = [], []
            for a in circuit:
                if a >= len(real):
                    trails.append(current)
                    current = []
                else:
                    current.append(a)
        else:
            holder = next((x for x in comp.vertices if here[x]), None)
            if holder is None:
                raise InfeasibleOrientation(f"component at time {comp.time} holds no walk")
            trails = [_euler_circuit(holder, arcs)]
        moves = []
        for trail in trails:
            first = arcs[trail[0]][0]
            if not here[first]:
                raise InfeasibleOrientation(f"no walk at {first} before time {comp.time}")
            w = here[first].pop()
            walks[w][1].extend(real[a] for a in trail)
            moves.append((w, arcs[trail[-1]][1]))
        for w, last in moves:
            here[last].append(w)
    return walks


def check_walks(inst: Instance, walks: list[Walk]) -> None:
    """Raise AssertionError unless ``walks`` is an exact cover by non-strict walks."""
    assert Counter(s for s, _ in walks) == Counter(
        {v: c for v, c in enumerate(inst.start) if c}), "start counts differ"
    used = Counter(e for _, es in walks for e in es)
    assert len(used) == inst.m and all(c == 1 for c in used.values()), "not an exact cover"
    finals = Counter()
    for start, es in walks:
        position, last = start, None
        for e in es:
            u, v, t = inst.edges[e]
            assert position in (u, v), f"walk leaves from {position} along {(u, v)}"
            assert last is None or t >= last, "time decreases along a walk"
            position, last = (v if position == u else u), t
        finals[position] += 1
    if inst.end is not None:
        assert finals == Counter({v: c for v, c in enumerate(inst.end) if c}), "end counts differ"
    if inst.end_set is not None:
        assert all(v in inst.end_set for v in finals), "walk ends outside end_set"
