#!/usr/bin/env python3
"""Build full-day FREE instances and linear-time graph lower bounds."""
from collections import defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/mink-20261030'
sys.path.insert(0, str(ROOT / 'experiments'))
from datasets import transit_trips, trip_instance


def components(adj):
    seen = set()
    count = 0
    for v in adj:
        if v in seen:
            continue
        count += 1
        seen.add(v)
        stack = [v]
        while stack:
            for w in adj[stack.pop()]:
                if w not in seen:
                    seen.add(w)
                    stack.append(w)
    return count


def lower_bounds(inst):
    adj = defaultdict(list)
    snapshots = defaultdict(list)
    degree = [0] * inst.n
    for u, v, t in inst.edges:
        degree[u] += 1
        degree[v] += 1
        adj[u].append(v)
        adj[v].append(u)
        snapshots[t].append((u, v))
    static = max((sum(d % 2 for d in degree) + 1) // 2, components(adj))
    del adj
    snapshot = 0
    for edges in snapshots.values():
        adj = defaultdict(list)
        for u, v in edges:
            adj[u].append(v)
            adj[v].append(u)
        snapshot = max(snapshot, components(adj))
    return static, snapshot


def main():
    paths = sorted((ROOT / 'data/raw/transit').glob('*/network_temporal_day.csv'))
    if len(paths) != 25:
        raise ValueError(f'expected 25 cities, found {len(paths)}')
    (OUT / 'inst').mkdir(parents=True, exist_ok=True)
    rows = []
    for path in paths:
        inst = trip_instance(transit_trips(path, strict=False, dedupe=True), path.parent.name).free_end()
        static, snapshot = lower_bounds(inst)
        inst.save(OUT / 'inst' / f'{inst.name}.json')
        row = dict(city=inst.name, n=inst.n, m=inst.m, given_k=inst.k,
                   static_LB=static, snapshot_LB=snapshot, LB=max(static, snapshot))
        rows.append(row)
        print(json.dumps(row), flush=True)
    (OUT / 'lb.json').write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main()
