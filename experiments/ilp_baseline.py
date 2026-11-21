#!/usr/bin/env python3
"""Independent binary orientation ILP, agreement checks, and bounded benchmarks.

Run with SciPy available; no dependency is installed by this module.
Only FIX and FREE are supported. x[e]=1 chooses the first endpoint as tail.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import multiprocessing as mp
import platform
from pathlib import Path
import random
import sys
import time
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import scipy
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix

from nscover import (Instance, Result, Timeline, brute_force, build_walks,
                     check_walks, solve_branch, solve_pairflow)
from nscover.generators import cycle_instance, random_end, random_instance


def solve_ilp(inst: Instance, time_limit: float = 60) -> Result:
    """Return Result(YES/NO/LIMIT), with tail vertices and checked walks on YES.

    Model building is independent of Timeline and all library solver machinery.
    The HiGHS time limit covers optimization; the benchmark additionally enforces
    a wall limit around model building and optimization in an isolated process.
    Numerical incumbents are rounded, then checked using exact integer counters
    and the independent operational walk checker. Unexpected errors propagate.
    """
    if inst.end_set is not None:
        raise ValueError("ENDSET is outside this baseline's scope")
    if time_limit <= 0:
        return Result("LIMIT")
    if not inst.m:
        if inst.end is not None and inst.end != inst.start:
            return Result("NO")
        check_walks(inst, build_walks(inst, []))
        return Result("YES", [], stats={"walks_checked": True})

    # c[v] = constant[v] + sum(coeff[v][e] * x[e]).
    constant = list(inst.start)
    coeff = [{} for _ in range(inst.n)]
    rows, cols, values, lower, upper = [], [], [], [], []

    def constrain(terms, base, lo, hi=np.inf):
        row = len(lower)
        for e, val in terms.items():
            if val:
                rows.append(row)
                cols.append(e)
                values.append(val)
        lower.append(lo - base)
        upper.append(hi - base)

    snapshots = defaultdict(list)
    for e, (_, _, t) in enumerate(inst.edges):
        snapshots[t].append(e)
    for t in sorted(snapshots):
        adjacency = defaultdict(set)
        for e in snapshots[t]:
            u, v, _ = inst.edges[e]
            adjacency[u].add(v)
            adjacency[v].add(u)
        unseen = set(adjacency)
        while unseen:
            root = min(unseen)
            unseen.remove(root)
            stack, component = [root], []
            while stack:
                v = stack.pop()
                component.append(v)
                for w in sorted(adjacency[v]):
                    if w in unseen:
                        unseen.remove(w)
                        stack.append(w)
            terms = Counter()
            for v in component:
                terms.update(coeff[v])
            constrain(terms, sum(constant[v] for v in component), 1)
        # At u: in-out=1-2x; at v: in-out=2x-1.
        for e in snapshots[t]:
            u, v, _ = inst.edges[e]
            constant[u] += 1
            coeff[u][e] = -2
            constant[v] -= 1
            coeff[v][e] = 2
        for v in sorted(adjacency):
            constrain(coeff[v], constant[v], 0)
    if inst.end is not None:
        for v in range(inst.n):
            constrain(coeff[v], constant[v], inst.end[v], inst.end[v])
    matrix = coo_matrix((np.asarray(values, dtype=float), (rows, cols)),
                        shape=(len(lower), inst.m)).tocsc()
    answer = milp(np.zeros(inst.m), integrality=np.ones(inst.m),
                  bounds=Bounds(0, 1),
                  constraints=LinearConstraint(matrix, lower, upper),
                  options={"time_limit": float(time_limit), "mip_rel_gap": 0.0})
    stats = {"highs_status": int(answer.status), "message": answer.message,
             "variables": inst.m, "constraints": len(lower), "nonzeros": matrix.nnz}
    if answer.x is not None:
        bits = np.rint(answer.x).astype(int)
        if (np.any(np.abs(answer.x - bits) > 1e-6)
                or np.any(bits < 0) or np.any(bits > 1)):
            raise AssertionError("non-binary HiGHS incumbent")
        lhs = matrix @ bits
        if np.any(lhs < np.asarray(lower)) or np.any(lhs > np.asarray(upper)):
            raise AssertionError("rounded incumbent violates integer constraints")
        tails = [u if bit else v for (u, v, _), bit in zip(inst.edges, bits)]
        check_walks(inst, build_walks(inst, tails))
        return Result("YES", tails, stats={**stats, "walks_checked": True})
    if answer.status == 2:
        return Result("NO", stats=stats)
    if answer.status == 1:
        return Result("LIMIT", stats=stats)
    raise RuntimeError(f"unexpected HiGHS outcome: {answer}")


def metadata(args):
    return {"meta": True, "argv": sys.argv, "python": sys.version,
            "scipy": scipy.__version__, "numpy": np.__version__,
            "platform": platform.platform(), "seed": args.seed,
            "clock": "perf_counter", "limit_seconds": 60}


def write(fh, row):
    fh.write(json.dumps(row, sort_keys=True) + "\n")
    fh.flush()


def agreement(args, fh):
    rng = random.Random(args.seed)
    counts = Counter()
    for i in range(args.count):
        kind = "random" if i % 2 == 0 else "cycle"
        if kind == "random":
            base = random_instance(rng, max_m=10)
        else:
            # Rejection bounds the operational oracle, including dense snapshots.
            while True:
                base = cycle_instance(rng, max_snapshots=2)
                if base.m <= 10:
                    break
        inst = base if (i // 2) % 2 == 0 else base.with_end(random_end(rng, base))
        ilp = solve_ilp(inst, 60)
        pf = solve_pairflow(inst)
        oracle = "YES" if brute_force(inst) else "NO"
        if pf.status == "YES":
            check_walks(inst, build_walks(inst, pf.tails))
        even = len(Timeline(inst).even_components())
        row = {"case": i, "kind": kind, "mode": "FREE" if inst.end is None else "FIX",
               "instance": inst.to_json(), "even": even,
               "ilp": ilp.status, "pf": pf.status, "oracle": oracle,
               "ilp_tails": ilp.tails, "pf_tails": pf.tails}
        row["agreement"] = ilp.status == pf.status == oracle
        write(fh, row)
        counts[row["mode"]] += 1
        counts[kind] += 1
        counts[oracle] += 1
        counts["with_even_component"] += bool(even)
        counts["disagreements"] += not row["agreement"]
        if not row["agreement"]:
            print("DISAGREEMENT " + json.dumps(row), flush=True)
    write(fh, {"summary": True, "count": args.count, **counts})
    print(json.dumps(dict(counts)), flush=True)
    if counts["disagreements"]:
        raise AssertionError("agreement failures saved in JSONL")


def _worker(conn, inst, algorithm):
    try:
        began = time.perf_counter()
        if algorithm == "ilp":
            result = solve_ilp(inst, 60)
        elif algorithm == "pf":
            result = solve_pairflow(inst)
        else:
            result = solve_branch(inst, max_seconds=60, max_flows=10**18)
        if result.status == "YES" and algorithm != "ilp":
            check_walks(inst, build_walks(inst, result.tails))
        elapsed = time.perf_counter() - began
        conn.send({"status": result.status, "seconds": elapsed,
                   "flows": result.flows, **result.stats,
                   "walks_checked": result.status == "YES"})
    except BaseException:
        conn.send({"status": "ERROR", "traceback": traceback.format_exc()})
    finally:
        conn.close()


def bounded(inst, algorithm):
    # Fork after imports, before any solver call, to exclude interpreter/import
    # startup and avoid forking a previously initialized HiGHS thread pool.
    ctx = mp.get_context("fork")
    parent, child = ctx.Pipe(duplex=False)
    process = ctx.Process(target=_worker, args=(child, inst, algorithm))
    began = time.perf_counter()
    process.start()
    child.close()
    try:
        if parent.poll(max(0, 60 - (time.perf_counter() - began))):
            row = parent.recv()
        else:
            row = {"status": "LIMIT", "seconds": time.perf_counter() - began,
                   "hard_wall_limit": True}
    finally:
        if process.is_alive():
            process.terminate()
        process.join(timeout=1)
        if process.is_alive():
            process.kill()
            process.join()
        parent.close()
    return row


def benchmark(args, fh):
    if args.family == "shortage":
        from experiments.family import family
        inst = family(args.e)
    else:
        from experiments.even_rich_bench import variants
        inst = dict(variants(args.family, args.m, args.index))[args.variant]
    tl = Timeline(inst)
    row = {"family": args.family, "e": args.e, "target_m": args.m,
           "index": args.index, "variant": args.variant, "n": inst.n,
           "m": inst.m, "k": inst.k, "even": len(tl.even_components()),
           "components": len(tl.components), "instance": inst.to_json(),
           "sha256": hashlib.sha256(json.dumps(inst.to_json(), sort_keys=True).encode()).hexdigest()}
    for algorithm in ("ilp", "pf", "bb"):
        row[algorithm] = bounded(inst, algorithm)
        print(algorithm, json.dumps(row[algorithm]), flush=True)
    statuses = {row[a]["status"] for a in ("ilp", "pf", "bb")} - {"LIMIT"}
    row["agreement"] = len(statuses) == 1 and "ERROR" not in statuses
    write(fh, row)
    if not row["agreement"]:
        raise AssertionError("benchmark disagreement/error saved in JSONL")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=["agreement", "bench"])
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--seed", type=int, default=20261115)
    p.add_argument("--count", type=int, default=500)
    p.add_argument("--family", choices=["shortage", "sparse", "dense"], default="shortage")
    p.add_argument("--e", type=int, default=2)
    p.add_argument("--m", type=int, default=50)
    p.add_argument("--index", type=int, default=0)
    p.add_argument("--variant", choices=["FIX-yes", "FREE-yes", "FIX-cut", "FREE-cut"], default="FREE-cut")
    args = p.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as fh:
        write(fh, metadata(args))
        (agreement if args.mode == "agreement" else benchmark)(args, fh)


if __name__ == "__main__":
    main()
