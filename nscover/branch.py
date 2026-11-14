"""Branch and bound on the chain network (prop:nonstrict-bb in the thesis).

Solve the chain network.  If the decoded orientation leaves a component K of time t
without a walk, K is even, and every solution has c_t(v) >= 2 for some v in K that
appeared before t, i.e. B[v][j] <= before[v][j + 1] / 2 - 1 for its previous appearance
j.  One child per such v; every even component is branched on at most once per path.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from .chainflow import DEFAULT_BACKEND, ChainNetwork, prefix_caps, walk_counts
from .instance import Instance
from .timeline import Component, Timeline


@dataclass
class Result:
    status: str                      # "YES", "NO" or "LIMIT"
    tails: list[int] | None = None   # an orientation realising a solution
    flows: int = 0                   # maximum flows solved
    stats: dict = field(default_factory=dict)


def first_dead(inst: Instance, tl: Timeline, tails: list[int]) -> Component | None:
    before, _ = walk_counts(inst, tl, tails)
    for comp, counts in zip(tl.components, before):
        if sum(counts.values()) == 0:
            return comp
    return None


def solve_branch(inst: Instance, max_flows: int = 10 ** 6, tl: Timeline | None = None,
                 backend: str = DEFAULT_BACKEND, max_seconds: float | None = None) -> Result:
    """'LIMIT' when max_flows flows or max_seconds seconds are used up."""
    began = time.perf_counter()
    tl = tl or Timeline(inst)
    caps = prefix_caps(inst, tl)
    if caps is None:
        return Result("NO")
    stack = [caps]
    flows = 0
    while stack:
        if flows >= max_flows or (max_seconds is not None
                                  and time.perf_counter() - began > max_seconds):
            return Result("LIMIT", flows=flows)
        node = stack.pop()
        flows += 1
        net = ChainNetwork(inst, tl, node, backend)
        if not net.complete:
            continue
        tails = net.tails()
        dead = first_dead(inst, tl, tails)
        if dead is None:
            return Result("YES", tails, flows)
        if not dead.even:
            raise AssertionError("a walk-free component that is not even")
        for v in dead.vertices:
            j = dead.position[v] - 1
            if j < 0:
                continue  # c_t(v) = a_v is fixed
            child = [row[:] for row in node]
            child[v][j] = min(child[v][j], tl.before[v][j + 1] // 2 - 1)
            if child[v][j] >= 0:
                stack.append(child)
    return Result("NO", flows=flows)
