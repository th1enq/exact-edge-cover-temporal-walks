#!/usr/bin/env python3
"""Minimum starts on S by finite degree-box enumeration (NS-FREE).

graph is an Instance; its start/end constraints are ignored. Every vector in
the box 0 <= a_v <= deg(v) is tested. No solver-derived oracle is used here.
Running this file delegates to the reproducible C experiment driver.
"""
from itertools import product
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nscover import Instance, solve_pairflow


def min_walks(graph: Instance, S) -> int | None:
    vertices = sorted(set(S))
    if any(not 0 <= v < graph.n for v in vertices):
        raise ValueError("invalid start vertex")
    degree = [0] * graph.n
    for u, v, _ in graph.edges:
        degree[u] += 1
        degree[v] += 1
    best = None
    for values in product(*(range(degree[v] + 1) for v in vertices)):
        a = [0] * graph.n
        for v, c in zip(vertices, values):
            a[v] = c
        result = solve_pairflow(Instance(graph.n, graph.edges, a))
        if result.status == "YES" and (best is None or sum(a) < best):
            best = sum(a)
    return best


if __name__ == "__main__":
    from endset_study import main
    main(default="C")
