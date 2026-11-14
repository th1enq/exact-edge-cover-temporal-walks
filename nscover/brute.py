"""Exhaustive oracle from the operational definition, for small instances only.

Walks are indistinguishable tokens.  Within a snapshot the edges are traversed one at a
time in any order, each by a token standing at one of its endpoints; this is exactly a
partition into non-strict walks (a walk may take several edges of one snapshot).  The
oracle uses neither orientations nor the characterisation.
"""

from __future__ import annotations

import functools

from .instance import Instance


def brute_force(inst: Instance) -> bool:
    def final_ok(tokens) -> bool:
        if inst.end_set is not None:
            return all(c == 0 or v in inst.end_set for v, c in enumerate(tokens))
        return inst.end is None or list(tokens) == list(inst.end)

    times = sorted({t for _, _, t in inst.edges})
    by_time = [frozenset(i for i, e in enumerate(inst.edges) if e[2] == t) for t in times]

    @functools.lru_cache(maxsize=None)
    def run(step: int, tokens: tuple[int, ...], left: frozenset) -> bool:
        if not left:
            if step + 1 >= len(times):
                return final_ok(tokens)
            return run(step + 1, tokens, by_time[step + 1])
        for e in left:
            u, v, _ = inst.edges[e]
            for x, y in ((u, v), (v, u)):
                if tokens[x]:
                    moved = list(tokens)
                    moved[x] -= 1
                    moved[y] += 1
                    if run(step, tuple(moved), left - {e}):
                        return True
        return False

    if not times:
        return final_ok(inst.start)
    return run(0, tuple(inst.start), by_time[0])
