"""The chain network: condition (i) of the characterisation as one maximum flow.

An orientation chooses a tail for every edge.  B[v][j] is the number of tails at v in
its first j + 1 appearances.  Condition (i) is B[v][j] <= floor(before[v][j+1] / 2),
i.e. B[v][j] <= floor((a_v + G_{v,j}) / 2) with G_{v,j} the degree up to appearance j.
For NS-FIX the last prefix must equal h_v = (a_v + G_v - z_v) / 2.
For NS-ENDSET the same equality with z_v = 0 holds outside end_set;
inside end_set only the ordinary prefix upper bounds apply.

Network: source -> edge e (cap 1) -> slot (u, j_u) or slot (v, j_v); slot (v, j) ->
slot (v, j + 1) with the prefix capacity; the last slot of v -> sink.  A flow of value
m orients every edge and satisfies every prefix bound (the bounds are laminar per
vertex); the flow on the arc after slot (v, j) is B[v][j].

Backends.  "augment" (default) exploits that the prefix bounds can be made
non-decreasing (B is non-decreasing, so B[v][j] <= min over j' >= j of caps[v][j'] is
the same condition): edges taken in time order are then assigned greedily to an
endpoint with slack; the edges left over are routed by SciPy's Dinic on the residual
network of the greedy flow ("augment"), or one breadth-first augmenting-path search
per edge ("augment-bfs", pure Python).  "python" (Dinic in maxflow.py) and "scipy" (SciPy's Dinic)
solve the same network from scratch and serve as independent checks.
"""

from __future__ import annotations

from collections import deque

from .instance import Instance
from .maxflow import MaxFlow
from .timeline import Timeline


def fixed_end_targets(inst: Instance, tl: Timeline) -> list[int] | None:
    """h_v = (a_v + G_v - z_v) / 2 per vertex, or None when the end vector is impossible."""
    assert inst.end is not None
    if sum(inst.start) != sum(inst.end):
        return None
    targets = []
    for v in range(inst.n):
        diff = tl.total[v] - inst.end[v]
        if diff < 0 or diff % 2:
            return None
        if not tl.g[v] and diff:
            return None  # an isolated vertex keeps its walks
        targets.append(diff // 2)
    return targets


def prefix_caps(inst: Instance, tl: Timeline) -> list[list[int]] | None:
    """caps[v][j] = largest allowed B[v][j]; None if ends fail a counting check."""
    caps = []
    for v in range(inst.n):
        row, running = [], inst.start[v]
        for x in tl.g[v]:
            running += x
            row.append(running // 2)
        caps.append(row)
    if inst.end is not None:
        targets = fixed_end_targets(inst, tl)
        if targets is None:
            return None
        for v, row in enumerate(caps):
            caps[v] = [min(c, targets[v]) for c in row]
    if inst.end_set is not None:
        for v in range(inst.n):
            if v not in inst.end_set:
                if tl.total[v] % 2 or (not tl.g[v] and inst.start[v]):
                    return None
        if not inst.end_set and inst.k:
            return None
    return caps


def _endset_orientation(inst: Instance, tl: Timeline, caps, base, count):
    """Feasible chain circulation with exact final arcs outside T.

    Lower bounds are removed with node demands and a super source/sink.
    Source->edge and sink->source arcs fix the total flow at m. This branch
    is used only for a proper end set; all legacy backends stay unchanged.
    """
    net = MaxFlow(count + 2)
    demand = [0] * count

    def arc(a, b, low, high):
        if high < low:
            return None
        demand[a] -= low
        demand[b] += low
        return net.add(a, b, high - low)

    choices = []
    for e, (u, v, _) in enumerate(inst.edges):
        arc(0, 2 + e, 1, 1)
        ju, jv = tl.slot[e]
        choices.append(arc(2 + e, base[u] + ju, 0, 1))
        arc(2 + e, base[v] + jv, 0, 1)
    for v in range(inst.n):
        q = len(tl.g[v])
        for j in range(q):
            last = j + 1 == q
            low = tl.total[v] // 2 if last and v not in inst.end_set else 0
            if arc(base[v] + j, 1 if last else base[v] + j + 1,
                   low, caps[v][j]) is None:
                return False, [False] * inst.m
    arc(1, 0, inst.m, inst.m)
    needed = 0
    for v, d in enumerate(demand):
        if d > 0:
            net.add(count, v, d)
            needed += d
        elif d < 0:
            net.add(v, count + 1, -d)
    complete = net.flow(count, count + 1) == needed
    return complete, [net.cap[a] == 0 for a in choices]


try:
    import numpy as np
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import maximum_flow
    HAVE_SCIPY = True
except ImportError:  # pragma: no cover
    HAVE_SCIPY = False

DEFAULT_BACKEND = "augment"


def _augment_orientation(inst: Instance, tl: Timeline, caps: list[list[int]],
                         use_scipy: bool = HAVE_SCIPY):
    """(complete, tail_is_u) by greedy assignment plus augmenting paths.

    Stops at the first edge that no augmenting path can route: the set of nodes
    reachable from the source never grows during augmentation, so the maximum flow is
    then below m.  Nodes: edge e is e; slot (v, j) is m + base[v] + j.
    """
    n, m = inst.n, inst.m
    cap = []
    for row in caps:
        eff, low = row[:], None
        for j in range(len(eff) - 1, -1, -1):
            low = eff[j] if low is None else min(low, eff[j])
            eff[j] = low
        cap.append(eff)
    base, slots = [], 0
    for row in cap:
        base.append(slots)
        slots += len(row)
    slot_v = [v for v in range(n) for _ in cap[v]]
    slot_j = [j for v in range(n) for j in range(len(cap[v]))]
    slot_cap = [c for row in cap for c in row]
    last = [base[v] + len(cap[v]) - 1 for v in range(n)]
    end_slot = [0] * m * 2  # end_slot[2e] = slot of e at u, end_slot[2e + 1] at v
    inc: list[list[int]] = [[] for _ in range(slots)]
    for e, (u, v, _) in enumerate(inst.edges):
        ju, jv = tl.slot[e]
        end_slot[2 * e], end_slot[2 * e + 1] = base[u] + ju, base[v] + jv
        inc[base[u] + ju].append(e)
        inc[base[v] + jv].append(e)

    side = [-1] * m           # 0: tail at u, 1: tail at v, -1: unassigned
    count = [0] * n
    remaining = [sum(tl.g[v]) for v in range(n)]
    left = []
    for e in sorted(range(m), key=lambda e: inst.edges[e][2]):
        u, v, _ = inst.edges[e]
        su = slot_cap[end_slot[2 * e]] - count[u]
        sv = slot_cap[end_slot[2 * e + 1]] - count[v]
        # urgency: tails still allowed at the end per remaining incident edge
        uu = (slot_cap[last[u]] - count[u]) / remaining[u]
        uv = (slot_cap[last[v]] - count[v]) / remaining[v]
        remaining[u] -= 1
        remaining[v] -= 1
        if su <= 0 and sv <= 0:
            left.append(e)
        elif sv <= 0 or (su > 0 and uu >= uv):
            side[e] = 0
            count[u] += 1
        else:
            side[e] = 1
            count[v] += 1
    if not left:
        return True, [s == 0 for s in side]
    if use_scipy:
        return _finish_with_scipy(m, slots, base, last, end_slot, inc, side, slot_cap, left)

    B = [0] * slots           # B[slot] = tails of its vertex in slots up to it
    def refresh(v: int) -> None:
        running = 0
        for s in range(base[v], last[v] + 1):
            running += sum(1 for f in inc[s] if side[f] >= 0 and end_slot[2 * f + side[f]] == s)
            B[s] = running

    for v in range(n):
        if cap[v]:
            refresh(v)
    stamp = [0] * (m + slots)
    parent = [0] * (m + slots)
    for round_, e0 in enumerate(left, 1):
        stamp[e0] = round_
        parent[e0] = -1
        queue = deque([e0])
        found = -1
        while queue and found < 0:
            a = queue.popleft()
            if a < m:
                for k in (0, 1):
                    if side[a] == k:
                        continue
                    s = m + end_slot[2 * a + k]
                    if stamp[s] != round_:
                        stamp[s], parent[s] = round_, a
                        queue.append(s)
                continue
            s = a - m
            if B[s] < slot_cap[s]:
                if s == last[slot_v[s]]:
                    found = a
                    break
                if stamp[a + 1] != round_:
                    stamp[a + 1], parent[a + 1] = round_, a
                    queue.append(a + 1)
            if slot_j[s] > 0 and B[s - 1] > 0 and stamp[a - 1] != round_:
                stamp[a - 1], parent[a - 1] = round_, a
                queue.append(a - 1)
            for f in inc[s]:
                if stamp[f] != round_ and side[f] >= 0 and end_slot[2 * f + side[f]] == s:
                    stamp[f], parent[f] = round_, a
                    queue.append(f)
        if found < 0:
            return False, [s == 0 if s >= 0 else None for s in side]
        touched = set()
        cur = found
        while True:
            p = parent[cur]
            if p >= m:
                cur = p
                continue
            f = p
            if side[f] >= 0:
                touched.add(slot_v[end_slot[2 * f + side[f]]])
            side[f] = 0 if end_slot[2 * f] == cur - m else 1
            touched.add(slot_v[cur - m])
            if parent[f] < 0:
                break
            cur = parent[f]
        for v in touched:
            refresh(v)
    return True, [s == 0 for s in side]


def _finish_with_scipy(m, slots, base, last, end_slot, inc, side, slot_cap, left):
    """Route the edges left by the greedy pass: SciPy's Dinic on the residual network
    of the greedy flow.  Nodes: 0 source, 1 sink, 2 + e edges, 2 + m + s slots."""
    B = [0] * slots
    tails_at = [0] * slots
    for e, k in enumerate(side):
        if k >= 0:
            tails_at[end_slot[2 * e + k]] += 1
    for v in range(len(base)):
        running = 0
        for s in range(base[v], last[v] + 1):
            running += tails_at[s]
            B[s] = running
    is_last = [False] * slots
    for v in range(len(base)):
        if last[v] >= base[v]:
            is_last[last[v]] = True
    rows, cols, data = [], [], []
    for e in left:
        rows.append(0); cols.append(2 + e); data.append(1)
    for e, k in enumerate(side):
        for kk in (0, 1):
            slot = 2 + m + end_slot[2 * e + kk]
            if k == kk:
                rows.append(slot); cols.append(2 + e)
            else:
                rows.append(2 + e); cols.append(slot)
            data.append(1)
    for s in range(slots):
        node = 2 + m + s
        target = 1 if is_last[s] else node + 1
        if slot_cap[s] - B[s] > 0:
            rows.append(node); cols.append(target); data.append(slot_cap[s] - B[s])
        if B[s] > 0 and not is_last[s]:
            rows.append(node + 1); cols.append(node); data.append(B[s])
    count = 2 + m + slots
    graph = csr_matrix((np.asarray(data, dtype=np.int32), (rows, cols)), shape=(count, count))
    result = maximum_flow(graph, 0, 1, method="dinic")
    if int(result.flow_value) < len(left):
        return False, [k == 0 if k >= 0 else None for k in side]
    # the flow matrix is antisymmetric: a positive entry edge -> slot is the new tail
    sub = result.flow.tocsr()[2:2 + m].tocoo()
    new_side = list(side)
    for e, col, val in zip(sub.row.tolist(), sub.col.tolist(), sub.data.tolist()):
        if val > 0 and col >= 2 + m:
            new_side[e] = 0 if end_slot[2 * e] == col - 2 - m else 1
    return True, [k == 0 for k in new_side]


class ChainNetwork:
    """One max flow on the chain network with caps[v][j] (optionally tightened).

    backend "python" is the Dinic of maxflow.py; "scipy" is SciPy's Dinic in C on the
    same network (much faster on long chains; used by default when available).
    Proper end sets use Python Dinic for lower-bound circulation independently
    of backend; the legacy backend paths apply unchanged otherwise.
    """

    def __init__(self, inst: Instance, tl: Timeline, caps: list[list[int]],
                 backend: str = DEFAULT_BACKEND):
        self.inst, self.tl = inst, tl
        m = inst.m
        base, count = [], 2 + m
        for v in range(inst.n):
            base.append(count)
            count += len(tl.g[v])
        self.base = base
        if inst.end_set is not None and len(inst.end_set) < inst.n:
            complete, self._tail_is_u = _endset_orientation(inst, tl, caps, base, count)
            self.value = m if complete else -1
            return
        if backend in ("augment", "augment-bfs"):
            complete, self._tail_is_u = _augment_orientation(
                inst, tl, caps, use_scipy=HAVE_SCIPY and backend == "augment")
            self.value = m if complete else -1  # -1: below m, exact value not computed
        elif backend == "python":
            net = MaxFlow(count)
            choice = []
            for e, (u, v, _) in enumerate(inst.edges):
                net.add(0, 2 + e, 1)
                ju, jv = tl.slot[e]
                choice.append(net.add(2 + e, base[u] + ju, 1))
                net.add(2 + e, base[v] + jv, 1)
            for v in range(inst.n):
                q = len(tl.g[v])
                for j in range(q):
                    net.add(base[v] + j, base[v] + j + 1 if j + 1 < q else 1, caps[v][j])
            self.value = net.flow(0, 1)
            self._tail_is_u = [net.cap[arc] == 0 for arc in choice]
        elif backend == "scipy":
            rows, cols, data = [], [], []
            for e, (u, v, _) in enumerate(inst.edges):
                ju, jv = tl.slot[e]
                rows += (0, 2 + e, 2 + e)
                cols += (2 + e, base[u] + ju, base[v] + jv)
                data += (1, 1, 1)
            for v in range(inst.n):
                q = len(tl.g[v])
                for j in range(q):
                    if caps[v][j] > 0:
                        rows.append(base[v] + j)
                        cols.append(base[v] + j + 1 if j + 1 < q else 1)
                        data.append(caps[v][j])
            graph = csr_matrix((np.asarray(data, dtype=np.int32), (rows, cols)),
                               shape=(count, count))
            result = maximum_flow(graph, 0, 1, method="dinic")
            self.value = int(result.flow_value)
            flow = result.flow.tocsr()[2:2 + m].tocoo()
            to_u = [False] * m
            for e, col, val in zip(flow.row.tolist(), flow.col.tolist(), flow.data.tolist()):
                if val > 0:
                    u = inst.edges[e][0]
                    if col == base[u] + tl.slot[e][0]:
                        to_u[e] = True
            self._tail_is_u = to_u
        else:
            raise ValueError(f"unknown backend {backend!r}")

    @property
    def complete(self) -> bool:
        return self.value == self.inst.m

    def tails(self) -> list[int]:
        """The tail vertex of every edge (only meaningful when complete)."""
        return [u if is_u else v for (u, v, _), is_u in zip(self.inst.edges, self._tail_is_u)]


def walk_counts(inst: Instance, tl: Timeline, tails: list[int]):
    """c_t(v) before every component, per component: {comp: {v: walks before t}}, and
    the final counts.  Pure bookkeeping, no feasibility check."""
    tokens = list(inst.start)
    before: list[dict[int, int]] = []
    for comp in tl.components:
        before.append({v: tokens[v] for v in comp.vertices})
        for e in comp.edges:
            u, v, _ = inst.edges[e]
            head = v if tails[e] == u else u
            tokens[tails[e]] -= 1
            tokens[head] += 1
    return before, tokens
