"""Dinic's maximum flow on adjacency arrays, and orientations with prescribed in-degrees."""

from __future__ import annotations

from collections import deque


class MaxFlow:
    def __init__(self, n: int):
        self.n = n
        self.head = [-1] * n
        self.to: list[int] = []
        self.cap: list[int] = []
        self.nxt: list[int] = []

    def add(self, a: int, b: int, c: int) -> int:
        """Add arc a -> b with capacity c; returns the arc id (its reverse is id ^ 1)."""
        self.to += [b, a]
        self.cap += [c, 0]
        self.nxt += [self.head[a], self.head[b]]
        self.head[a] = len(self.to) - 2
        self.head[b] = len(self.to) - 1
        return len(self.to) - 2

    def flow(self, s: int, t: int) -> int:
        total = 0
        to, cap, nxt, head = self.to, self.cap, self.nxt, self.head
        while True:
            level = [-1] * self.n
            level[s] = 0
            queue = deque([s])
            while queue:
                a = queue.popleft()
                arc = head[a]
                while arc != -1:
                    if cap[arc] > 0 and level[to[arc]] < 0:
                        level[to[arc]] = level[a] + 1
                        queue.append(to[arc])
                    arc = nxt[arc]
            if level[t] < 0:
                return total
            current = head[:]
            while True:
                path: list[int] = []
                a = s
                while a != t:
                    arc = current[a]
                    while arc != -1 and not (cap[arc] > 0 and level[to[arc]] == level[a] + 1):
                        arc = nxt[arc]
                    current[a] = arc
                    if arc == -1:
                        if a == s:
                            break
                        level[a] = -1
                        a = to[path.pop() ^ 1]
                        continue
                    path.append(arc)
                    a = to[arc]
                if a != t:
                    break
                push = min(cap[arc] for arc in path)
                for arc in path:
                    cap[arc] -= push
                    cap[arc ^ 1] += push
                total += push

    def reachable(self, s: int) -> list[bool]:
        """Vertices reachable from s in the residual network (the source side of a min cut)."""
        seen = [False] * self.n
        seen[s] = True
        stack = [s]
        while stack:
            a = stack.pop()
            arc = self.head[a]
            while arc != -1:
                if self.cap[arc] > 0 and not seen[self.to[arc]]:
                    seen[self.to[arc]] = True
                    stack.append(self.to[arc])
                arc = self.nxt[arc]
        return seen


def orient_with_indegree(vertices: list[int], edges: list[tuple[int, int]],
                         indegree: dict[int, int]) -> list[int] | None:
    """Orient every edge (u, v) so that each vertex x gets indegree[x] heads.

    Returns head[i] in {u, v} per edge, or None when no such orientation exists.
    One bipartite max flow: source -> edge (1) -> endpoint -> sink (indegree).
    """
    if sum(indegree[x] for x in vertices) != len(edges) or min(
            (indegree[x] for x in vertices), default=0) < 0:
        return None
    local = {x: i for i, x in enumerate(vertices)}
    m = len(edges)
    net = MaxFlow(2 + m + len(vertices))
    source, sink = 0, 1
    arcs = []
    for i, (u, v) in enumerate(edges):
        net.add(source, 2 + i, 1)
        arcs.append(net.add(2 + i, 2 + m + local[u], 1))
        net.add(2 + i, 2 + m + local[v], 1)
    for x in vertices:
        if indegree[x] > 0:
            net.add(2 + m + local[x], sink, indegree[x])
    if net.flow(source, sink) < m:
        return None
    return [u if net.cap[arc] == 0 else v for arc, (u, v) in zip(arcs, edges)]
