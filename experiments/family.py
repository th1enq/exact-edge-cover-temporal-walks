#!/usr/bin/env python3
"""An explicit family on which branch and bound grows exponentially.

A hub h holds 2r walks (r pairs).  Gadget i (vertices u_i, v_i, w_i, times 2i-1 and
2i): at time 2i-1 the double edges h-u_i and h-v_i form an even component, which needs a
walk at h; at time 2i the triangle u_i v_i w_i is an even component, which has a walk
only if one pair moved from h to u_i or v_i at time 2i-1.  Pairs never return to the
hub, so the instance (end vertices free) is feasible iff r >= e.  With r = e - 1 it is
infeasible, but no single component shows it: the root max-flow ignores condition (ii),
and branch and bound learns the shortage one triangle at a time, two children each.
The pair-flow solver needs at most one augmentation per dead component.

Rows: e (number of gadgets), m, branch flows / status / seconds, pair status /
augmentations / seconds.  Stops after --seconds; branch and bound is capped per
instance by --branch-seconds and is skipped after its first LIMIT.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nscover import Instance, Timeline, solve_branch, solve_pairflow  # noqa: E402


def family(e: int, r: int | None = None) -> Instance:
    r = e - 1 if r is None else r
    h, edges = 0, []
    for i in range(e):
        u, v, w = 3 * i + 1, 3 * i + 2, 3 * i + 3
        t = 2 * i + 1
        edges += [(h, u, t), (h, u, t), (h, v, t), (h, v, t)]
        edges += [(u, v, t + 1), (v, w, t + 1), (w, u, t + 1)]
    start = [2 * r] + [0] * (3 * e)
    return Instance(3 * e + 1, edges, start, name=f"family-{e}-{r}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--e", type=int, nargs="+",
                        default=list(range(1, 21)) + [50, 100, 200, 500, 1000, 2000])
    parser.add_argument("--seconds", type=float, default=270)
    parser.add_argument("--branch-seconds", type=float, default=60)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    began = time.time()
    branch_alive = True
    with args.output.open("w", encoding="utf-8") as out:
        for e in args.e:
            if time.time() - began > args.seconds:
                break
            inst = family(e)
            tl = Timeline(inst)
            row = {"e": e, "n": inst.n, "m": inst.m, "k": inst.k,
                   "even": len(tl.even_components())}
            t0 = time.perf_counter()
            pair = solve_pairflow(inst, tl)
            row["pair"] = {"status": pair.status, "seconds": round(time.perf_counter() - t0, 4),
                           **pair.stats}
            if branch_alive:
                left = args.seconds - (time.time() - began)
                t0 = time.perf_counter()
                branch = solve_branch(inst, tl=tl, max_seconds=min(args.branch_seconds, left))
                row["branch"] = {"status": branch.status, "flows": branch.flows,
                                 "seconds": round(time.perf_counter() - t0, 4)}
                if branch.status == "LIMIT":
                    branch_alive = False
                else:
                    assert branch.status == pair.status, row
            out.write(json.dumps(row) + "\n")
            out.flush()
            print(json.dumps(row), flush=True)


if __name__ == "__main__":
    main()
