#!/usr/bin/env python3
"""Adversarial search: instances on which branch and bound needs many maximum flows.

Hill climbing over instances made of short cycles (the source of even components):
a mutation adds or removes a cycle snapshot, rewires an edge or moves a walk; it is
kept when branch and bound needs at least as many flows (capped at --cap).  For every
improvement the pair-flow solver is run on the same instance and must agree; the row
records both costs.  Stops after --seconds.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nscover import Instance, Timeline, solve_branch, solve_pairflow  # noqa: E402


def cycle(rng: random.Random, n: int, t: int) -> list[tuple[int, int, int]]:
    size = rng.randint(2, min(5, n))
    nodes = rng.sample(range(n), size)
    if size == 2:
        return [(nodes[0], nodes[1], t)] * 2
    return [(nodes[i], nodes[(i + 1) % size], t) for i in range(size)]


def mutate(rng: random.Random, inst: Instance) -> Instance:
    n, edges, start = inst.n, list(inst.edges), list(inst.start)
    horizon = max((t for *_, t in edges), default=0)
    op = rng.random()
    if op < 0.35 or not edges:
        edges += cycle(rng, n, rng.randint(1, horizon + 1))
    elif op < 0.5:
        t = rng.choice(sorted({t for *_, t in edges}))
        edges = [e for e in edges if e[2] != t]
    elif op < 0.75:
        i = rng.randrange(len(edges))
        u, v, t = edges[i]
        edges[i] = (*rng.sample(range(n), 2), t)
    elif op < 0.9:
        i = rng.randrange(len(edges))
        u, v, _ = edges[i]
        edges[i] = (u, v, rng.randint(1, horizon + 1))
    else:
        if sum(start) > 1 and rng.random() < 0.5:
            v = rng.choice([v for v in range(n) if start[v]])
            start[v] -= 1
        start[rng.randrange(n)] += 1
    return Instance(n, edges, start)


def cost(inst: Instance, cap: int) -> tuple[int, str]:
    res = solve_branch(inst, max_flows=cap)
    return res.flows, res.status


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=240)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--n", type=int, default=8)
    parser.add_argument("--max-edges", type=int, default=120)
    parser.add_argument("--cap", type=int, default=20000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rng = random.Random(args.seed)
    began = time.time()
    best = Instance(args.n, cycle(rng, args.n, 1), [1] + [0] * (args.n - 1))
    best_cost, _ = cost(best, args.cap)
    with args.output.open("w", encoding="utf-8") as out:
        while time.time() - began < args.seconds:
            cand = mutate(rng, best)
            if cand.m > args.max_edges or cand.m == 0:
                continue
            flows, status = cost(cand, args.cap)
            if flows < best_cost:
                continue
            improved = flows > best_cost
            best, best_cost = cand, flows
            if improved:
                tl = Timeline(cand)
                t0 = time.perf_counter()
                branch = solve_branch(cand, max_flows=args.cap, tl=tl)
                tb = time.perf_counter() - t0
                t0 = time.perf_counter()
                pair = solve_pairflow(cand, tl)
                tp = time.perf_counter() - t0
                if branch.status != "LIMIT":
                    assert branch.status == pair.status, cand
                row = {"seconds": round(time.time() - began, 1), "m": cand.m, "k": cand.k,
                       "even": len(tl.even_components()), "branch_flows": branch.flows,
                       "branch_status": branch.status, "branch_seconds": round(tb, 4),
                       "pair_status": pair.status, "pair_seconds": round(tp, 4), **pair.stats,
                       "instance": cand.to_json()}
                out.write(json.dumps(row) + "\n")
                out.flush()
    print("best branch flows", best_cost)


if __name__ == "__main__":
    main()
