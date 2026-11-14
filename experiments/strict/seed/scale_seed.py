import sys, random, time
sys.dont_write_bytecode = True
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[3])); pass
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import lil_matrix
from nscover import Instance

def planted(rng, n, k, steps, T):
    """k strict walks, each takes <=1 edge per time stamp; edges = the steps taken."""
    pos = [rng.randrange(n) for _ in range(k)]; start = pos[:]; edges = []
    for t in range(1, T + 1):
        for w in range(k):
            if rng.random() < steps:
                v = rng.randrange(n - 1); v += v >= pos[w]
                edges.append((pos[w], v, t)); pos[w] = v
    z = [0] * n
    for p in pos: z[p] += 1
    s = [0] * n
    for p in start: s[p] += 1
    return edges, s, z

def solve_ilp(inst, tl=120):
    n, m = inst.n, inst.m
    times = sorted({t for *_, t in inst.edges}); idx = {t: i for i, t in enumerate(times)}
    # per vertex: list of (time index, e, coef, const) in time order
    inc = [[] for _ in range(n)]
    for e, (u, w, t) in enumerate(inst.edges):
        inc[u].append((t, e, 1, 0)); inc[w].append((t, e, -1, 1))
    rows, ub = [], []
    A = lil_matrix((sum(len({t for t, *_ in inc[v]}) for v in range(n)), m)); r = 0
    prevdeg = 0
    for v in range(n):
        inc[v].sort(); cum_deg = 0; cum_c = 0; i = 0; L = inc[v]
        while i < len(L):
            t = L[i][0]; j = i
            while j < len(L) and L[j][0] == t: j += 1
            # edges before t: weight 2 (cumulative), edges at t: weight 1
            for t2, e, co, c0 in L[:i]: A[r, e] += 2 * co
            for t2, e, co, c0 in L[i:j]: A[r, e] += 1 * co
            const = sum(2 * c0 for *_, c0 in L[:i]) + sum(c0 for *_, c0 in L[i:j])
            ub.append(inst.start[v] + i - const); r += 1; i = j
    cons = [LinearConstraint(A.tocsr(), -np.inf, np.array(ub, float))]
    if inst.end is not None:
        B = lil_matrix((n, m)); beq = []
        for v in range(n):
            const = 0
            for t, e, co, c0 in inc[v]: B[v, e] += 2 * co; const += 2 * c0
            beq.append(inst.start[v] + len(inc[v]) - inst.end[v] - const)
        cons.append(LinearConstraint(B.tocsr(), np.array(beq, float), np.array(beq, float)))
    t0 = time.perf_counter()
    res = milp(np.zeros(m), constraints=cons, integrality=np.ones(m), bounds=Bounds(0, 1), options={'time_limit': tl})
    return res.status, time.perf_counter() - t0

rng = random.Random(1)
print("n   k   T   m    mode  planted(YES) status/time | perturbed status/time")
for (n, k, T) in [(20, 5, 12), (50, 15, 20), (100, 30, 30), (200, 60, 40), (400, 120, 60), (800, 250, 80)]:
    edges, s, z = planted(rng, n, k, 0.6, T)
    for fix in (False, True):
        inst = Instance(n, edges, s, z if fix else None)
        st, tm = solve_ilp(inst, 60)
        # perturb: move one edge's time to another stamp
        e2 = list(edges); i = rng.randrange(len(e2)); u, v, t = e2[i]; e2[i] = (u, v, 1 + (t % T))
        inst2 = Instance(n, e2, s, z if fix else None)
        st2, tm2 = solve_ilp(inst2, 60)
        print(f"{n:4d} {k:4d} {T:3d} {len(edges):5d} {'FIX ' if fix else 'FREE'}  st={st} {tm:6.2f}s | st={st2} {tm2:6.2f}s")
