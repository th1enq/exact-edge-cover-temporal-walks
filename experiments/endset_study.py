#!/usr/bin/env python3
"""Reproduce experiments A--D, each with a <300 second command watchdog.

Examples: python3 experiments/endset_study.py A
          python3 experiments/endset_study.py C --cases 2000
Outputs are written only beneath results/ext-20261101 (or --output).
"""
from __future__ import annotations

import argparse
from collections import Counter
from itertools import combinations_with_replacement, product
import json
import multiprocessing as mp
from pathlib import Path
import random
import signal
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nscover import Instance, brute_force, solve_pairflow, build_walks, check_walks
from min_walks_small_S import min_walks

SEED = 20261101


def random_instance(rng, max_m=7):
    n = rng.randint(1, 5)
    edges = [(*rng.sample(range(n), 2), rng.randint(1, 3))
             for _ in range(rng.randint(0, max_m))] if n > 1 else []
    start = [0] * n
    for _ in range(rng.randint(0, 3)):
        start[rng.randrange(n)] += 1
    return Instance(n, edges, start)


def experiment_a(cases):
    rng = random.Random(SEED)
    counts, kinds = Counter(), Counter()
    mismatches, free_mismatches = [], []
    for i in range(cases):
        base = random_instance(rng)
        # Deliberately cover full, singleton, empty, and arbitrary sets equally.
        kind = ("full", "singleton", "empty", "random")[i % 4]
        t = (list(range(base.n)) if kind == "full" else
             [rng.randrange(base.n)] if kind == "singleton" else
             [] if kind == "empty" else
             [v for v in range(base.n) if rng.randrange(2)])
        inst = Instance(base.n, base.edges, base.start, end_set=t)
        expected = brute_force(inst)
        res = solve_pairflow(inst)
        counts[res.status] += 1
        kinds[kind] += 1
        if (res.status == "YES") != expected:
            mismatches.append({"instance": inst.to_json(), "oracle": expected,
                               "solver": res.status})
        if res.status == "YES":
            check_walks(inst, build_walks(inst, res.tails))
        full = Instance(base.n, base.edges, base.start, end_set=list(range(base.n)))
        if solve_pairflow(base) != solve_pairflow(full):
            free_mismatches.append(base.to_json())
    return dict(cases=cases, counts=dict(counts), set_modes=dict(kinds),
                disagreements=mismatches, full_set_result_disagreements=free_mismatches)


def vectors(n, max_total):
    """All nonnegative vectors of total <= max_total, no degree restriction."""
    if n == 0:
        yield ()
    else:
        for first in range(max_total + 1):
            for rest in vectors(n - 1, max_total - first):
                yield (first,) + rest


def smallest_monotonicity_counterexample():
    # Order: (number of edges, number of vertices, sum(a), lexicographic data).
    # n=1: no edges are possible; for empty edges a YES has support in T and
    # adding at an excluded vertex fails. This is the absolute smallest case.
    # Also exhaustively search a nonempty-edge example with nonempty proper T.
    trivial = Instance(1, [], [0], end_set=[])
    added = Instance(1, [], [1], end_set=[])
    assert brute_force(trivial) and not brute_force(added)
    examined = 0
    for m in range(0, 3):
        for n in range(2, 4):
            choices = [(u, v, t) for u in range(n) for v in range(u + 1, n)
                       for t in (1, 2, 3)]
            for edge_ids in combinations_with_replacement(range(len(choices)), m):
                edges = [choices[e] for e in edge_ids]
                for total in range(4):
                    for a in vectors(n, total):
                        if sum(a) != total:
                            continue
                        for mask in range(1, (1 << n) - 1):
                            t = [v for v in range(n) if mask >> v & 1]
                            x = Instance(n, edges, list(a), end_set=t)
                            examined += 1
                            if not brute_force(x):
                                continue
                            for v in range(n):
                                b = list(a)
                                b[v] += 1
                                y = Instance(n, edges, b, end_set=t)
                                if not brute_force(y) and m:
                                    return dict(absolute={"yes": trivial.to_json(),
                                                          "no": added.to_json(), "v": 0},
                                                nonempty={"yes": x.to_json(),
                                                          "no": y.to_json(), "v": v},
                                                examined=examined,
                                                minimality="absolute: (m,n,k)=(0,1,0); "
                                                "nonempty edges/nonempty proper T: "
                                                "(m,n,k)=(1,2,1), minimal since k=0 "
                                                "cannot traverse a nonempty edge set")
    raise AssertionError("no counterexample found")


def experiment_b(cases):
    rng = random.Random(SEED + 1)
    counts = Counter()
    implications = 0
    violations, solver_disagreements = [], []
    for _ in range(cases):
        x = random_instance(rng)
        yes = brute_force(x)
        counts["YES" if yes else "NO"] += 1
        if (solve_pairflow(x).status == "YES") != yes:
            solver_disagreements.append(x.to_json())
        if yes:
            for v in range(x.n):
                a = x.start[:]
                a[v] += 1
                y = Instance(x.n, x.edges, a)
                implications += 1
                expected = brute_force(y)
                if not expected:
                    violations.append({"yes": x.to_json(), "no": y.to_json(), "v": v})
                if (solve_pairflow(y).status == "YES") != expected:
                    solver_disagreements.append(y.to_json())
    return dict(cases=cases, base_counts=dict(counts), implications=implications,
                violations=violations, solver_disagreements=solver_disagreements,
                counterexample=smallest_monotonicity_counterexample())


def brute_min(graph, s):
    # Any feasible cover can discard all empty walks. At most m nonempty walks
    # remain; for m=0 the all-zero vector is optimal. Thus total<=m exhausts
    # all relevant vectors, including counts above the proposed degree bound.
    best = None
    checked = 0
    for values in vectors(len(s), graph.m):
        a = [0] * graph.n
        for v, c in zip(s, values):
            a[v] = c
        yes = brute_force(Instance(graph.n, graph.edges, a))
        checked += 1
        if yes and (best is None or sum(a) < best):
            best = sum(a)
    return best, checked


def scaling_worker(graph, s, queue):
    began = time.perf_counter()
    answer = min_walks(graph, s)
    queue.put(dict(answer=answer, seconds=time.perf_counter() - began))


def scaling_c():
    rows = []
    rng = random.Random(SEED + 3)
    ctx = mp.get_context("spawn")
    for size in (1, 2, 3):
        for m in (10, 30, 100, 300):
            # Fixed n, same-time random multigraph. S contains the first size
            # vertices. Degrees grow with m, exercising the complete box.
            n = 6
            edges = [(*rng.sample(range(n), 2), 1) for _ in range(m)]
            graph = Instance(n, edges, [0] * n)
            degrees = [sum(v in e[:2] for e in edges) for v in range(size)]
            box = 1
            for d in degrees:
                box *= d + 1
            q = ctx.Queue()
            p = ctx.Process(target=scaling_worker, args=(graph, list(range(size)), q))
            began = time.perf_counter()
            p.start()
            p.join(12)
            row = dict(m=m, size_S=size, degrees_S=degrees, vectors=box,
                       limit_seconds=12)
            if p.is_alive():
                p.terminate()
                p.join()
                row.update(status="TIMEOUT", seconds_at_least=12)
            elif p.exitcode != 0:
                row.update(status="ERROR", exitcode=p.exitcode)
            else:
                row.update(status="OK", **q.get(timeout=1))
            row["wall_seconds"] = time.perf_counter() - began
            q.close()
            rows.append(row)
            print("C scaling", json.dumps(row), flush=True)
    return rows


def experiment_c(cases):
    rng = random.Random(SEED + 2)
    counts, mismatches, checked = Counter(), [], 0
    for i in range(cases):
        size = 1 + i % 3
        n = rng.randint(max(2, size), 5)
        edges = [(*rng.sample(range(n), 2), rng.randint(1, 3))
                 for _ in range(rng.randint(0, 5))]
        graph = Instance(n, edges, [0] * n)
        s = sorted(rng.sample(range(n), size))
        answer = min_walks(graph, s)
        expected, num = brute_min(graph, s)
        checked += num
        counts[str(size)] += 1
        if answer != expected:
            mismatches.append(dict(graph=graph.to_json(), S=s, answer=answer,
                                   oracle=expected))
    print("C correctness", cases, "cases,", checked, "oracle vectors,",
          len(mismatches), "disagreements", flush=True)
    return dict(cases=cases, cases_by_size=dict(counts), oracle_vectors=checked,
                disagreements=mismatches, scaling=scaling_c())


def experiment_d():
    # A two-parallel-edge even component at time 2 is initially walk-free.
    # Each disjoint copy requires one pair rerouting; shifted times keep all
    # copies distinct. The urgency ratios of the old warm start are unchanged.
    gadget = [(3, 0, 2), (3, 4, 1), (1, 4, 1), (0, 3, 2),
              (4, 0, 3), (2, 1, 1), (3, 0, 1)]
    rows = []
    for copies in (1, 2, 5, 10, 20, 50, 100, 200, 428):
        edges = [(u + 5 * i, v + 5 * i, t + 3 * i)
                 for i in range(copies) for u, v, t in gadget]
        inst = Instance(5 * copies, edges, [1, 0, 1, 0, 0] * copies)
        began = time.perf_counter()
        res = solve_pairflow(inst)
        elapsed = time.perf_counter() - began
        assert res.status == "YES"
        check_walks(inst, build_walks(inst, res.tails))
        if copies == 1:
            assert brute_force(inst)
        row = dict(m=inst.m, n=inst.n, copies=copies, status=res.status,
                   D=res.stats.get("augmentations", 0), dead=res.stats.get("dead", 0),
                   seconds=elapsed)
        rows.append(row)
        print("D", json.dumps(row), flush=True)
    return dict(gadget=Instance(5, gadget, [1, 0, 1, 0, 0]).to_json(), rows=rows,
                linear=all(r["D"] == r["copies"] for r in rows),
                note="D counts pair-flow augmentations, excluding chain max-flow work")


def main(default=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", choices=list("ABCD"), nargs="?", default=default)
    parser.add_argument("--cases", type=int)
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).resolve().parents[1] / "results/ext-20261101")
    args = parser.parse_args()
    if args.experiment is None:
        parser.error("choose A, B, C, or D")
    # Hard watchdog for the full command, including all child scaling runs.
    signal.alarm(290)
    began = time.perf_counter()
    fn = {"A": experiment_a, "B": experiment_b, "C": experiment_c, "D": experiment_d}[args.experiment]
    cases = args.cases if args.cases is not None else (2000 if args.experiment == "C" else 20000)
    result = fn() if args.experiment == "D" else fn(cases)
    result.update(experiment=args.experiment, seed=SEED,
                  total_seconds=time.perf_counter() - began)
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / (args.experiment.lower() + ".json")
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2), flush=True)
    print("Saved", path, flush=True)
    signal.alarm(0)


if __name__ == "__main__":
    main()
