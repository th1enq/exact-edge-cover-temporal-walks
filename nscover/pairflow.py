"""The polynomial algorithm (thm:complexity): M-convex submodular flow on walk pairs.

Pair counting.  c_t(v) has a fixed parity p_t(v), so q_t(v) = (c_t(v) - p_t(v)) / 2 is
the number of walk *pairs* at v before t.  Every vertex v is a chain of ports:

    S_v -> IN(K_1, v)   OUT(K_1, v) -> IN(K_2, v)   ...   OUT(K_q, v) -> Z_v

where K_j is the component of v's j-th appearance.  The flow xi on a waiting arc
(one of the arrows) is the number of pairs waiting at v between the two times.  With
boundary d xi = outflow - inflow, the ports of a component K carry (-alpha, beta):
alpha pairs come in, beta pairs go out.  The instance is feasible iff some xi >= 0 has
d xi in the direct sum of

  * Gamma_K for every component (Gamma'_K = Gamma_K minus {0} if K is even),
    Gamma_K = {(-alpha, beta) : alpha, beta >= 0, beta - alpha realisable}, where g is
    realisable iff some orientation of K has in - out = 2g + p_out - p_in;
  * the single point floor(a_v / 2) at S_v;
  * at the Z ports: the single point -(z_v - p_end(v)) / 2 (NS-FIX), or the simplex of
    non-negative pair vectors with the forced total (NS-FREE).
    NS-ENDSET uses that simplex on T and the singleton zero outside T;
    a nonzero final parity outside T is rejected by the chain counting check.

All of these sets are M-convex (lem:gamma-mconvex), so this is the feasibility problem of an
M-convex submodular flow, solved by shortest augmenting paths: keep x in the sets and
xi >= 0, and move one unit of the discrepancy d = d xi - x at a time from a positive
port to a negative port along a shortest path of the auxiliary graph, whose arcs are

  * head -> tail of a waiting arc (raise xi by one; always allowed),
  * tail -> head of a waiting arc with xi > 0 (lower xi by one),
  * i -> j inside one set when x + e_i - e_j stays in the set (an exchange).

The NS-FREE simplex at the Z ports allows every exchange i -> j with gamma_i >= 1; these
go through one extra hub node (i -> hub -> j) so that a search costs O(n) there instead
of O(n^2).  Hop distances stay consistent with every arc, which is all the exchange
lemma needs, and a simple path changes each gamma_i at most once, so the simplex part of
an augmentation is always valid.

Inside a component, g + e_v - e_w is realisable iff the current orientation has a
directed path from v to w (reverse it).  A shortest path never leaves the sets
(Murota's exchange lemma for M-convex sets); the code re-checks this after every
augmentation and raises if it fails.  If no positive port reaches a negative one, the
instance is infeasible.

Warm start: the chain network gives xi and x with d = 0 everywhere except on even
components left without a walk; each of those starts with one unit of discrepancy, so
the number of augmentations is at most the number of such components.
"""

from __future__ import annotations

from collections import deque

from .branch import Result
from .chainflow import DEFAULT_BACKEND, ChainNetwork, prefix_caps, walk_counts
from .instance import Instance
from .maxflow import orient_with_indegree
from .timeline import Timeline

START, END = -1, -2
HUB = -3  # search node for the NS-FREE simplex


class PairFlow:
    def __init__(self, inst: Instance, tl: Timeline, tails: list[int]):
        self.inst, self.tl = inst, tl
        self.end_vertices = range(inst.n) if inst.end_set is None else inst.end_set
        self.end_allowed = None if inst.end_set is None else frozenset(inst.end_set)
        n = inst.n
        comps = tl.components
        self.base = []
        count = 2 * n
        for comp in comps:
            self.base.append(count)
            count += 2 * len(comp.vertices)
        self.size = count
        self.group = [START] * n + [END] * n
        self.vertex = list(range(n)) + list(range(n))
        self.local: list[dict[int, int]] = []
        for comp in comps:
            self.local.append({v: i for i, v in enumerate(comp.vertices)})
            for v in comp.vertices:
                self.group += [comp.index, comp.index]
                self.vertex += [v, v]

        # waiting arcs, indexed by their head port
        self.prev = [-1] * count   # head port -> tail port
        self.next = [-1] * count   # tail port -> head port
        for v in range(n):
            tail = v  # S_v
            for c in tl.appear_comp[v]:
                head = self.port(c, v, 0)
                self.prev[head], self.next[tail] = tail, head
                tail = self.port(c, v, 1)
            self.prev[n + v], self.next[tail] = tail, n + v

        # state from the orientation
        before, final = walk_counts(inst, tl, tails)
        self.flow = [0] * count     # pairs on the waiting arc into each head port
        self.x = [0] * count
        for v in range(n):
            self.x[v] = inst.start[v] // 2
            self.flow[n + v] = (final[v] - tl.total[v] % 2) // 2
            self.x[n + v] = -self.flow[n + v]
        self.heads: list[list[int]] = []   # orientation of each component (head per edge)
        for comp, counts in zip(comps, before):
            heads = []
            for e in comp.edges:
                u, v, _ = inst.edges[e]
                heads.append(v if tails[e] == u else u)
            self.heads.append(heads)
            for v in comp.vertices:
                alpha = (counts[v] - comp.parity_in(v)) // 2
                self.flow[self.port(comp.index, v, 0)] = alpha
                self.x[self.port(comp.index, v, 0)] = -alpha
        for comp in comps:
            for v in comp.vertices:
                out = self.port(comp.index, v, 1)
                self.x[out] = self.flow[self.next[out]]
        self.d = [0] * count
        self.positive: set[int] = set()   # ports with d > 0
        self.dead = 0
        for comp in comps:
            if comp.even and all(self.x[self.port(comp.index, v, 0)] == 0 for v in comp.vertices):
                # walk-free even component: move x to (-e_v, e_v), one unit of discrepancy
                self.dead += 1
                v = comp.vertices[0]
                self.x[self.port(comp.index, v, 0)] = -1
                self.x[self.port(comp.index, v, 1)] = 1
                self.d[self.port(comp.index, v, 0)] = 1
                self.d[self.port(comp.index, v, 1)] = -1
                self.positive.add(self.port(comp.index, v, 0))
        self.augmentations = 0

    def port(self, c: int, v: int, side: int) -> int:
        """side 0 = IN, side 1 = OUT."""
        return self.base[c] + 2 * self.local[c][v] + side

    # ------------------------------------------------------------------ exchanges

    def _reach(self, c: int, v: int, cache: dict) -> list[int]:
        """Local indices of the vertices w of component c with a directed path v -> w
        (v included).  The adjacency of c is built once per search."""
        key = (c, v)
        if key not in cache:
            out = cache.get(("adj", c))
            if out is None:
                comp, local = self.tl.components[c], self.local[c]
                out = {}
                for e, head in zip(comp.edges, self.heads[c]):
                    a, b, _ = self.inst.edges[e]
                    out.setdefault(local[a if head == b else b], []).append(local[head])
                cache[("adj", c)] = out
            start = self.local[c][v]
            seen, stack = {start}, [start]
            while stack:
                a = stack.pop()
                for b in out.get(a, ()):
                    if b not in seen:
                        seen.add(b)
                        stack.append(b)
            cache[key] = sorted(seen)
        return cache[key]

    def exchanges(self, i: int, cache: dict):
        """Ports j != i of the same set with x + e_i - e_j in the set."""
        group, x = self.group[i], self.x
        if group in (START, END):  # single points; the simplex goes through HUB
            return
        comp, base = self.tl.components[group], self.base[group]
        side_i = (i - base) % 2
        if side_i == 0 and x[i] >= 0:
            return  # alpha_v would become negative
        total = None
        if comp.even:  # the new point must not be 0: sum |x| over the ports of c
            total = sum(map(abs, x[base:base + 2 * len(comp.vertices)]))
            total += -1 if side_i == 0 else 1
        for w in self._reach(group, self.vertex[i], cache):
            for side_j in (0, 1):
                j = base + 2 * w + side_j
                if j == i or (side_j == 1 and x[j] <= 0):
                    continue  # beta_w would become negative
                if total is not None and total + (1 if side_j == 0 else -1) == 0:
                    continue
                yield j

    # ------------------------------------------------------------------ augmentation

    def augment(self) -> bool:
        """One shortest augmenting path; False if no positive port reaches a negative one."""
        n, free = self.inst.n, self.inst.end is None
        parent: dict[int, tuple[int | None, int]] = {p: (None, 0) for p in self.positive}
        queue = deque(sorted(self.positive))
        cache: dict = {}
        target = -1
        while queue and target < 0:
            a = queue.popleft()
            steps = []
            if a == HUB:
                steps.extend((n + w, 5) for w in self.end_vertices)  # gamma_w + 1
            else:
                if self.prev[a] >= 0:
                    steps.append((self.prev[a], 1))           # raise xi on the arc into a
                if self.next[a] >= 0 and self.flow[self.next[a]] > 0:
                    steps.append((self.next[a], 2))           # lower xi on the arc out of a
                steps.extend((b, 3) for b in self.exchanges(a, cache))
                if (free and self.group[a] == END and self.x[a] <= -1
                        and (self.end_allowed is None or self.vertex[a] in self.end_allowed)):
                    steps.append((HUB, 4))                    # gamma_a - 1
            for b, kind in steps:
                if b not in parent:
                    parent[b] = (a, kind)
                    if b != HUB and self.d[b] < 0:
                        target = b
                        break
                    queue.append(b)
        if target < 0:
            return False
        touched = set()
        b = target
        while parent[b][0] is not None:
            a, kind = parent[b]
            if kind == 1:
                self.flow[a] += 1
            elif kind == 2:
                self.flow[b] -= 1
            elif kind == 4:
                self.x[a] += 1
            elif kind == 5:
                self.x[b] -= 1
            else:
                self.x[a] += 1
                self.x[b] -= 1
                touched.add(self.group[a])
            b = a
        self.d[b] -= 1
        self.d[target] += 1
        if self.d[b] == 0:
            self.positive.discard(b)
        for c in touched:
            if c >= 0:
                self._reorient(c)
        self.augmentations += 1
        return True

    def _reorient(self, c: int) -> None:
        comp = self.tl.components[c]
        indegree = {}
        for v in comp.vertices:
            alpha = -self.x[self.port(c, v, 0)]
            beta = self.x[self.port(c, v, 1)]
            if alpha < 0 or beta < 0:
                raise AssertionError("augmentation left the box alpha, beta >= 0")
            g = beta - alpha
            twice = comp.degree[v] + 2 * g + comp.parity_out(v) - comp.parity_in(v)
            indegree[v] = twice // 2
        if comp.even and all(self.x[self.port(c, v, s)] == 0 for v in comp.vertices for s in (0, 1)):
            raise AssertionError("augmentation reached 0 on an even component")
        pairs = [self.inst.edges[e][:2] for e in comp.edges]
        heads = orient_with_indegree(comp.vertices, pairs, indegree)
        if heads is None:
            raise AssertionError("augmentation left the realisable set (exchange lemma)")
        self.heads[c] = heads

    def tails(self) -> list[int]:
        out = [0] * self.inst.m
        for comp, heads in zip(self.tl.components, self.heads):
            for e, head in zip(comp.edges, heads):
                u, v, _ = self.inst.edges[e]
                out[e] = u if head == v else v
        return out


def solve_pairflow(inst: Instance, tl: Timeline | None = None,
                   backend: str = DEFAULT_BACKEND) -> Result:
    tl = tl or Timeline(inst)
    caps = prefix_caps(inst, tl)
    if caps is None:
        return Result("NO", stats={"reason": "counting"})
    root = ChainNetwork(inst, tl, caps, backend)
    if not root.complete:
        return Result("NO", flows=1, stats={"reason": "chain network"})
    pf = PairFlow(inst, tl, root.tails())
    while pf.positive:
        if not pf.augment():
            return Result("NO", flows=1, stats={"dead": pf.dead, "augmentations": pf.augmentations,
                                                "reason": "no augmenting path"})
    return Result("YES", pf.tails(), flows=1,
                  stats={"dead": pf.dead, "augmentations": pf.augmentations})
