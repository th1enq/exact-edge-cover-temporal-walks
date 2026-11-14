"""Local transition set of an even component in pair units: Gamma = {(-a, q)} with
entry pairs a, exit pairs q (tokens 2a -> 2q through some orientation).  Check that
Gamma and Gamma minus {0} are M-convex (box-truncated a <= A)."""
import itertools, time

def gamma(n, edges, A):
    out = set()
    for bits in itertools.product((0, 1), repeat=len(edges)):
        d = [0] * n
        for b, (u, w) in zip(bits, edges):
            x, y = (u, w) if b else (w, u)
            d[x] += 1; d[y] -= 1
        for a in itertools.product(range(A + 1), repeat=n):
            c2 = [2 * a[v] - d[v] for v in range(n)]
            if min(c2) >= 0:
                out.add(tuple(-x for x in a) + tuple(x // 2 for x in c2))
    return out

def m_violation(S):
    S = set(S)
    for x in S:
        for y in S:
            for i in range(len(x)):
                if x[i] <= y[i]: continue
                ok = False
                for j in range(len(x)):
                    if x[j] >= y[j]: continue
                    xa = list(x); xa[i] -= 1; xa[j] += 1
                    ya = list(y); ya[i] += 1; ya[j] -= 1
                    if tuple(xa) in S and tuple(ya) in S: ok = True; break
                if not ok: return x, y, i
    return None

ALL = {
    "C3": (3, [(0, 1), (1, 2), (2, 0)]),
    "C4": (4, [(0, 1), (1, 2), (2, 3), (3, 0)]),
    "C5": (5, [(0, 1), (1, 2), (2, 3), (3, 4), (4, 0)]),
    "double edge": (2, [(0, 1), (0, 1)]),
    "bowtie": (5, [(0, 1), (1, 2), (2, 0), (0, 3), (3, 4), (4, 0)]),
    "C4 + chord pair": (4, [(0, 1), (1, 2), (2, 3), (3, 0), (0, 2), (0, 2)]),
    "theta-even": (4, [(0, 1), (1, 3), (0, 2), (2, 3), (0, 3), (0, 3)]),
    "K5": (5, [(i, j) for i in range(5) for j in range(i + 1, 5)]),
    "triple+single": (3, [(0, 1), (0, 1), (0, 1), (1, 2), (2, 0)]),
    # negative control: disconnected, so h_K vanishes on a proper subset and the
    # lemma does not apply; Gamma minus 0 is expected NOT to be M-convex
    "two triangles": (6, [(0, 1), (1, 2), (2, 0), (3, 4), (4, 5), (5, 3)]),
}
def legacy_main():
    import sys
    # usage: gamma_mconvex.py [name,name,... [name=A,name=A,...]]; default: every graph,
    # entry box A = 2 for up to 3 vertices and A = 1 otherwise (keeps the run under 5 minutes)
    wanted = sys.argv[1].split(",") if len(sys.argv) > 1 else list(ALL)
    boxes = {k: 2 if ALL[k][0] <= 3 else 1 for k in ALL}
    if len(sys.argv) > 2:
        boxes.update(x.split("=") for x in sys.argv[2].split(","))
    for name, (n, edges) in ((k, ALL[k]) for k in wanted):
        deg = [0] * n
        for u, w in edges: deg[u] += 1; deg[w] += 1
        assert all(x % 2 == 0 for x in deg), name
        A = int(boxes[name])
        began = time.time()
        G = gamma(n, edges, A)
        G0 = G - {tuple([0] * (2 * n))}
        print(f"{name:16s} |Gamma|={len(G):5d}  Gamma M-convex: {m_violation(G) is None}  "
              f"Gamma minus 0 M-convex: {m_violation(G0) is None}  ({time.time() - began:.1f}s)", flush=True)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "audit":
        from gamma_mconvex_audit import main
        main(sys.argv[2:])
    else:
        legacy_main()
