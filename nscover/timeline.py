"""Snapshot components, vertex appearances and token parities.

For a vertex v with appearances j = 0..q-1 (the distinct times of its edges), g[v][j]
is its degree at appearance j and before[v][j] = a_v + (degree before appearance j).
Before a time t the vertex holds c_t(v) walks; c_t(v) has the parity of before[v][j]
whatever the orientation, because each incident edge changes it by one.

A component K of the snapshot graph E_t is *even* when every vertex of K has even
degree in E_t and even a_v + G_v^{<t}.  Only on even components can a walk-free
component appear (thm:nonstrict, condition (ii)).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .instance import Instance


@dataclass
class Component:
    index: int
    time: int
    vertices: list[int]          # sorted
    edges: list[int]             # edge indices
    degree: dict[int, int]       # degree of each vertex inside the component
    before: dict[int, int]       # a_v + G_v^{<t}
    position: dict[int, int]     # appearance index of each vertex at this time
    even: bool

    def parity_in(self, v: int) -> int:
        return self.before[v] % 2

    def parity_out(self, v: int) -> int:
        return (self.before[v] + self.degree[v]) % 2


class Timeline:
    def __init__(self, inst: Instance):
        self.inst = inst
        n = inst.n
        by_time: dict[int, list[int]] = defaultdict(list)
        for e, (_, _, t) in enumerate(inst.edges):
            by_time[t].append(e)
        self.times = sorted(by_time)

        # appearances of every vertex
        at: list[dict[int, list[int]]] = [defaultdict(list) for _ in range(n)]
        for e, (u, v, t) in enumerate(inst.edges):
            at[u][t].append(e)
            at[v][t].append(e)
        self.appear_times: list[list[int]] = [sorted(at[v]) for v in range(n)]
        self.g: list[list[int]] = [[len(at[v][t]) for t in self.appear_times[v]]
                                   for v in range(n)]
        self.before: list[list[int]] = []
        self.total: list[int] = []
        for v in range(n):
            running, row = inst.start[v], []
            for x in self.g[v]:
                row.append(running)
                running += x
            self.before.append(row)
            self.total.append(running)
        index_of = [{t: j for j, t in enumerate(self.appear_times[v])} for v in range(n)]
        self.slot = [(index_of[u][t], index_of[v][t]) for u, v, t in inst.edges]

        # components of every snapshot, in time order
        self.components: list[Component] = []
        self.appear_comp: list[list[int]] = [[0] * len(self.g[v]) for v in range(n)]
        for t in self.times:
            parent: dict[int, int] = {}

            def find(x: int) -> int:
                root = x
                while parent.setdefault(root, root) != root:
                    root = parent[root]
                while parent[x] != root:
                    parent[x], x = root, parent[x]
                return root

            for e in by_time[t]:
                u, v, _ = inst.edges[e]
                parent[find(u)] = find(v)
            groups: dict[int, list[int]] = defaultdict(list)
            for e in by_time[t]:
                groups[find(inst.edges[e][0])].append(e)
            for root in sorted(groups):
                members = groups[root]
                degree: dict[int, int] = defaultdict(int)
                for e in members:
                    u, v, _ = inst.edges[e]
                    degree[u] += 1
                    degree[v] += 1
                vertices = sorted(degree)
                position = {v: index_of[v][t] for v in vertices}
                before = {v: self.before[v][position[v]] for v in vertices}
                even = all(degree[v] % 2 == 0 and before[v] % 2 == 0 for v in vertices)
                comp = Component(len(self.components), t, vertices, members, dict(degree),
                                 before, position, even)
                self.components.append(comp)
                for v in vertices:
                    self.appear_comp[v][position[v]] = comp.index

    def even_components(self) -> list[Component]:
        return [c for c in self.components if c.even]
