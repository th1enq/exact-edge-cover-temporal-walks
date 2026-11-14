"""Exact STRICT FREE/FIX dynamic programming on token-count vectors.

For fixed n,k there are C(k+n-1,n-1) vectors. A snapshot with more than k
edges is impossible. Only touched coordinates enter the orientation search;
next[v] = count[v] + degree[v] - 2*out[v]. Thus identical departure prefixes
at the same edge index can safely share one representative orientation.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from experiments.strict.solver import build_strict_walks, check_strict_walks


class _TimeLimit(Exception):
    pass


def _transitions(edges, counts, deadline):
    """Yield distinct (departure counts, representative local tails).

    Explicit DFS avoids recursion depth limits. Memoizing (edge index, out)
    merges parallel-edge permutations and other equivalent partial choices.
    Capacity is tested BEFORE adding a departure, using pre-snapshot counts.
    """
    zero = (0,) * len(counts)
    stack = [(0, zero, ())]
    seen = [set() for _ in range(len(edges) + 1)]
    while stack:
        if time.perf_counter() >= deadline:
            raise _TimeLimit
        j, out, tails = stack.pop()
        if out in seen[j]:
            continue
        seen[j].add(out)
        if j == len(edges):
            yield out, tails
            continue
        u, v = edges[j]
        for tail in (v, u):
            if out[tail] < counts[tail]:
                after = list(out)
                after[tail] += 1
                stack.append((j + 1, tuple(after), tails + (tail,)))


def solve_strict_dp(inst, max_states=200000, time_limit=60):
    """Exact YES/NO, or UNKNOWN on a live-layer state cap/deadline.

    states_max includes the first vector exceeding the cap. Back-pointers retain
    only ancestors of live states. Limits are cooperative; witness construction
    and checking are mandatory even if the search uses its entire budget.
    """
    if inst.end_set is not None:
        raise ValueError('Only strict S-FREE and S-FIX are supported')
    if max_states < 1 or time_limit <= 0:
        raise ValueError('max_states and time_limit must be positive')
    began = time.perf_counter()
    deadline = began + time_limit
    states_max = 1

    def result(status, reason, orientation=None):
        walks = None
        if status == 'YES':
            walks = build_strict_walks(inst, orientation)
            if not check_strict_walks(inst, walks):
                raise AssertionError('invalid DP strict witness')
        return dict(status=status, states_max=states_max,
                    seconds=time.perf_counter() - began,
                    orientation=orientation, walks=walks, reason=reason)

    if inst.end is not None and sum(inst.end) != inst.k:
        return result('NO', 'terminal-total')
    groups = defaultdict(list)
    for e, (u, v, stamp) in enumerate(inst.edges):
        groups[stamp].append((e, u, v))
    stamps = sorted(groups)
    # Node = (previous node, input-edge IDs, representative tails).
    states = {tuple(inst.start): None}
    try:
        for step, stamp in enumerate(stamps):
            if time.perf_counter() >= deadline:
                raise _TimeLimit
            layer = groups[stamp]
            if len(layer) > inst.k:
                return result('NO', 'snapshot-more-edges-than-tokens')
            touched = sorted({v for _, u, w in layer for v in (u, w)})
            index = {v: j for j, v in enumerate(touched)}
            edges = [(index[u], index[v]) for _, u, v in layer]
            ids = tuple(e for e, _, _ in layer)
            degrees = [0] * len(touched)
            for u, v in edges:
                degrees[u] += 1
                degrees[v] += 1
            after = {}
            for c, node in states.items():
                local = tuple(c[v] for v in touched)
                if sum(local) < len(layer):
                    continue
                for out, tails in _transitions(edges, local, deadline):
                    nxt = list(c)
                    for j, v in enumerate(touched):
                        nxt[v] += degrees[j] - 2 * out[j]
                    nxt = tuple(nxt)
                    if (step == len(stamps) - 1 and inst.end is not None
                            and nxt != tuple(inst.end)):
                        continue
                    if nxt not in after:
                        after[nxt] = (node, ids, tuple(touched[v] for v in tails))
                        states_max = max(states_max, len(after))
                        if len(after) > max_states:
                            return result('UNKNOWN', 'states-cap')
            states = after
            if not states:
                return result('NO', 'unreachable')
    except _TimeLimit:
        return result('UNKNOWN', 'time-limit')
    target = tuple(inst.end) if inst.end is not None else next(iter(states))
    if target not in states:
        return result('NO', 'unreachable-terminal')
    orientation = [None] * inst.m
    node = states[target]
    while node is not None:
        node, ids, tails = node
        for e, tail in zip(ids, tails):
            orientation[e] = tail
    return result('YES', 'reachable', orientation)
