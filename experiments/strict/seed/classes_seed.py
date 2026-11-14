import sys, random
sys.dont_write_bytecode = True
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[3])); pass
from experiments.strict.seed import ilp_seed as lp
from nscover import Instance
from experiments.strict import oracle

def snap_ok(kind, edges, n):
    deg = [0] * n
    for u, v in edges: deg[u] += 1; deg[v] += 1
    if kind == 'matching': return max(deg, default=0) <= 1
    if kind == 'maxdeg2': return max(deg, default=0) <= 2
    if kind == 'star':
        return len(edges) <= 1 or any(all(u == c or v == c for u, v in edges) for c in range(n))
    if kind == 'forest':
        par = list(range(n))
        def f(x):
            while par[x] != x: par[x] = par[par[x]]; x = par[x]
            return x
        for u, v in edges:
            a, b = f(u), f(v)
            if a == b: return False
            par[a] = b
        return True
    return True

def gen(rng, kind, fix):
    for _ in range(1000):
        n, T, k = rng.randint(2, 5), rng.randint(1, 3), rng.randint(1, 3)
        edges = []
        for t in range(1, T + 1):
            cand = [tuple(sorted(rng.sample(range(n), 2))) for _ in range(rng.randint(0, 3))]
            while cand and not snap_ok(kind, cand, n): cand.pop()
            edges += [(u, v, t) for u, v in cand]
        if not edges: continue
        s = [0] * n; z = [0] * n
        for _ in range(k): s[rng.randrange(n)] += 1; z[rng.randrange(n)] += 1
        return Instance(n, edges, s, z if fix else None)

rng = random.Random(9); N = int(sys.argv[2])
for kind in ('matching', 'star', 'maxdeg2', 'forest', 'any'):
    row = []
    for fix in (False, True):
        yes = gap = 0
        for _ in range(N):
            inst = gen(rng, kind, fix); truth = oracle.decide(inst); l = lp.lp_feasible(inst)
            yes += truth; gap += (l and not truth); assert not (truth and not l)
        row.append(f"{'FIX ' if fix else 'FREE'} yes={yes} lp_gap={gap}")
    print(f"{kind:9s}", ' | '.join(row))
