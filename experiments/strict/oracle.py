"""Small exact strict temporal edge-cover oracles; no NS solver is used."""
from __future__ import annotations

from functools import lru_cache
from itertools import product
from pathlib import Path
import sys

sys.dont_write_bytecode = True  # importing Instance must not write into nscover/
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from nscover.instance import Instance


def snapshots(inst: Instance):
    return [tuple((u, v) for u, v, s in inst.edges if s == t)
            for t in sorted({t for _, _, t in inst.edges})]


def validate(inst: Instance):
    if inst.end_set is not None:
        raise ValueError("Only S-FREE and S-FIX are supported")


@lru_cache(maxsize=16384)
def orientations(n, edges):
    """Departure counts and net changes for all 2**m edge orientations."""
    choices = set()
    for bits in product((0, 1), repeat=len(edges)):
        out, delta = [0] * n, [0] * n
        for (u, v), bit in zip(edges, bits):
            x, y = (u, v) if bit == 0 else (v, u)
            out[x] += 1
            delta[x] -= 1
            delta[y] += 1
        choices.add((tuple(out), tuple(delta)))
    return tuple(sorted(choices))


def reachable_counts(inst: Instance) -> set[tuple[int, ...]]:
    validate(inst)
    states = {tuple(inst.start)}
    for edges in snapshots(inst):
        if len(edges) > inst.k:
            return set()
        choices = orientations(inst.n, edges)
        states = {tuple(c[v] + delta[v] for v in range(inst.n))
                  for c in states for out, delta in choices
                  if all(out[v] <= c[v] for v in range(inst.n))}
        if not states:
            break
    return states


def decide(inst: Instance) -> bool:
    states = reachable_counts(inst)
    return bool(states) if inst.end is None else tuple(inst.end) in states


def identity_brute(inst: Instance, *, allow_stay: bool = False) -> bool:
    """Independent edge-to-token injection search, retaining labeled positions.

    An edge is assigned an unused token based on its pre-snapshot position;
    the new position is committed only when every edge has an assignment.
    This does not enumerate orientations or call the count-vector DP.
    Optional allow_stay independently simulates the R1 gadget's same-side exit.
    """
    validate(inst)
    initial = tuple(v for v, count in enumerate(inst.start) for _ in range(count))
    layers = snapshots(inst)

    @lru_cache(None)
    def run(step, positions):
        if step == len(layers):
            return inst.end is None or all(positions.count(v) == inst.end[v]
                                           for v in range(inst.n))
        edges = layers[step]

        def assign(j, used, after):
            if j == len(edges):
                return run(step + 1, after)
            u, v = edges[j]
            for token, x in enumerate(positions):
                if not (used >> token & 1) and x in (u, v):
                    for destination in (u, v) if allow_stay else (v if x == u else u,):
                        moved = list(after)
                        moved[token] = destination
                        if assign(j + 1, used | (1 << token), tuple(moved)):
                            return True
            return False

        return assign(0, 0, positions)

    return run(0, initial)
