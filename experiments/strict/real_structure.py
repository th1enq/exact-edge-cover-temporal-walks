"""How 'proper' are real transit snapshots?  Per city, at resolution r seconds:
fraction of snapshots with max degree <=1 (proper), <=2, and fraction of edges that lie in
snapshots containing a vertex of degree >=2; and walks k vs largest snapshot size.
Uses the strict loader (consecutive departures strictly increasing)."""
import json, sys, time
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import datasets
root = Path(sys.argv[1]); out = Path(sys.argv[2]); res_list = [1, 60]
rows = []
for city in sorted(p for p in root.iterdir() if p.is_dir()):
    f = city / "network_temporal_day.csv"
    if not f.exists(): continue
    t0 = time.time()
    trips = datasets.transit_trips(f, strict=True)
    for r in res_list:
        snaps = defaultdict(list)
        for trip in trips:
            for t, a, b in trip:
                snaps[t // r * r].append((a, b))
        ns = len(snaps); m = sum(map(len, snaps.values()))
        dmax_hist = Counter(); edges_bad = 0; conf = 0
        for es in snaps.values():
            deg = Counter()
            for a, b in es: deg[a] += 1; deg[b] += 1
            d = max(deg.values()); dmax_hist[min(d, 5)] += 1
            if d >= 2:
                edges_bad += len(es); conf += sum(1 for x in deg.values() if x >= 2)
        rows.append(dict(city=city.name, res=r, trips=len(trips), edges=m, snapshots=ns,
            proper_snap=dmax_hist[1] / ns, deg_le2_snap=(dmax_hist[1] + dmax_hist[2]) / ns,
            edges_in_nonproper=edges_bad / m, conflict_vertices=conf,
            max_snapshot=max(map(len, snaps.values()))))
        print(rows[-1], flush=True)
    if time.time() - t0 > 100: pass
json.dump(rows, open(out, "w"), indent=1)
