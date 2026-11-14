"""Is the strict reachable token-count set R_t (FREE-end, tokens a at start) M-convex after halving?
Class 'match': snapshots are matchings; 'cherry': components are single edges or 2-edge paths;
'deg2': max degree <=2 (paths/cycles, parallel edges allowed); 'gen': arbitrary."""
import itertools, random, sys, json
def orients(edges, c):
    n = len(c)
    for bits in itertools.product((0, 1), repeat=len(edges)):
        o = [0]*n
        for (u, v), b in zip(edges, bits): o[u if b else v] += 1
        if all(o[i] <= c[i] for i in range(n)): yield tuple(o)
def step(R, edges):
    n = len(next(iter(R))); deg = [0]*n
    for u, v in edges: deg[u] += 1; deg[v] += 1
    out = set()
    for c in R:
        for o in orients(edges, c): out.add(tuple(c[i]+deg[i]-2*o[i] for i in range(n)))
    return out
def mconv(S):
    S = list(S)
    if not S: return True
    n = len(S[0]); p = [x % 2 for x in S[0]]
    H = {tuple((x[i]-p[i])//2 for i in range(n)) for x in S}
    for x in H:
        for y in H:
            for i in range(n):
                if x[i] > y[i]:
                    ok = False
                    for j in range(n):
                        if x[j] < y[j]:
                            x2 = list(x); x2[i] -= 1; x2[j] += 1
                            y2 = list(y); y2[i] += 1; y2[j] -= 1
                            if tuple(x2) in H and tuple(y2) in H: ok = True; break
                    if not ok: return False
    return True
def snap(cls, n, rng):
    m = rng.randint(1, 4); es = []
    for _ in range(40):
        if len(es) >= m: break
        u, v = rng.sample(range(n), 2); e = (u, v)
        deg = [0]*n
        for a, b in es: deg[a] += 1; deg[b] += 1
        deg[u] += 1; deg[v] += 1
        if cls == 'match' and max(deg) > 1: continue
        if cls == 'deg2' and max(deg) > 2: continue
        if cls == 'cherry':
            if max(deg) > 2 or sum(1 for d in deg if d == 2) > 1: continue
            if any(e == f or e == f[::-1] for f in es): continue
        es.append(e)
    return es
rng = random.Random(int(sys.argv[2])); cls = sys.argv[1]; N = int(sys.argv[3])
bad = 0; first = None
for it in range(N):
    n = rng.randint(3, 5); a = [rng.randint(0, 2) for _ in range(n)]
    R = {tuple(a)}; hist = []
    for t in range(rng.randint(1, 4)):
        es = snap(cls, n, rng)
        if not es: continue
        R = step(R, es); hist.append(es)
        if not R: break
        if not mconv(R):
            bad += 1
            if first is None: first = dict(a=a, snaps=hist, R=sorted(R))
            break
print(cls, 'instances', N, 'non-M-convex', bad)
if first: print(json.dumps(first))
