import sys, random
sys.dont_write_bytecode = True
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[3]))
import numpy as np
from scipy.optimize import linprog, milp, LinearConstraint, Bounds
from nscover import Instance
from experiments.strict import oracle

def system(inst):
    """x_e = 1 iff edge e departs from its first endpoint u (so o_{e,u}=x_e, o_{e,v}=1-x_e)."""
    n, m = inst.n, inst.m
    times = sorted({t for *_, t in inst.edges})
    # coefficient of x_e and constant in  out(v, e)
    def out(e, v):  # returns (coef, const) of o_{e,v}
        u, w, _ = inst.edges[e]
        return (1, 0) if v == u else (-1, 1)
    A, ub = [], []
    deg = {t: [0] * n for t in times}
    for e, (u, w, t) in enumerate(inst.edges): deg[t][u] += 1; deg[t][w] += 1
    for v in range(n):
        prevdeg = 0
        for t in times:
            if deg[t][v]:
                row = np.zeros(m); const = 0
                for e, (u, w, s) in enumerate(inst.edges):
                    if v in (u, w) and s <= t:
                        coef, c0 = out(e, v); k = 1 if s == t else 2
                        row[e] += k * coef; const += k * c0
                A.append(row); ub.append(inst.start[v] + prevdeg - const)
            prevdeg += deg[t][v]
    Aeq, beq = [], []
    if inst.end is not None:
        for v in range(n):
            row = np.zeros(m); const = 0
            for e, (u, w, s) in enumerate(inst.edges):
                if v in (u, w):
                    coef, c0 = out(e, v); row[e] += 2 * coef; const += 2 * c0
            tot = sum(deg[t][v] for t in times)
            # a + tot - 2*sum o = z  ->  2*sum o = a + tot - z
            Aeq.append(row); beq.append(inst.start[v] + tot - inst.end[v] - const)
    return (np.array(A) if A else np.zeros((0, m))), np.array(ub, float), \
           (np.array(Aeq) if Aeq else np.zeros((0, m))), np.array(beq, float)

def lp_feasible(inst):
    A, ub, Aeq, beq = system(inst)
    if inst.m == 0: return True
    r = linprog(np.zeros(inst.m), A_ub=A if len(A) else None, b_ub=ub if len(A) else None,
                A_eq=Aeq if len(Aeq) else None, b_eq=beq if len(Aeq) else None, bounds=(0, 1), method='highs')
    return r.status == 0

def ilp_feasible(inst):
    A, ub, Aeq, beq = system(inst)
    if inst.m == 0: return True
    cons = []
    if len(A): cons.append(LinearConstraint(A, -np.inf, ub))
    if len(Aeq): cons.append(LinearConstraint(Aeq, beq, beq))
    r = milp(np.zeros(inst.m), constraints=cons, integrality=np.ones(inst.m), bounds=Bounds(0, 1))
    return r.status == 0

def rand_inst(rng, fix):
    n, m, k = rng.randint(2, 5), rng.randint(1, 8), rng.randint(1, 3)
    edges = [tuple(rng.sample(range(n), 2)) + (rng.randint(1, 3),) for _ in range(m)]
    s = [0] * n; z = [0] * n
    for _ in range(k): s[rng.randrange(n)] += 1; z[rng.randrange(n)] += 1
    return Instance(n, edges, s, z if fix else None)

if __name__ == '__main__':
    rng = random.Random(5); N = int(sys.argv[1])
    for fix in (False, True):
        c = dict(yes=0, ilp_bad=0, lp_yes=0, gap=0, lp_no_but_yes=0); ex = []
        for _ in range(N):
            inst = rand_inst(rng, fix)
            truth = oracle.decide(inst); i = ilp_feasible(inst); l = lp_feasible(inst)
            c['yes'] += truth; c['ilp_bad'] += (i != truth); c['lp_yes'] += l
            c['gap'] += (l and not truth); c['lp_no_but_yes'] += (truth and not l)
            if l and not truth and len(ex) < 2: ex.append((inst.n, inst.edges, inst.start, inst.end))
        print('FIX' if fix else 'FREE', N, c, ex)
