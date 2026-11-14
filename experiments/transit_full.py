#!/usr/bin/env python3
"""Full-day transit networks: pair-flow solver vs branch and bound under a time limit.

One walk per vehicle trip (NS-FIX: trip ends fixed; NS-FREE: free ends).  Branch and
bound gets --branch-seconds; LIMIT means it did not finish; --branch-seconds 0 skips it.
--resolution rounds departure times down to multiples of that many seconds (a coarser
timetable); trips stay non-decreasing in time, so they remain non-strict walks.
--window-hours H keeps only the trips that start in the busiest H-hour block of the day
(blocks counted from the first departure, busiest = most trip segments), for cities too
large to solve in one run.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import datasets  # noqa: E402
from nscover import Timeline, build_walks, check_walks, solve_branch, solve_pairflow  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--problem", choices=("fix", "free"), default="fix")
    parser.add_argument("--branch-seconds", type=float, default=150)
    parser.add_argument("--resolution", type=int, default=0)
    parser.add_argument("--window-hours", type=float, default=0)
    parser.add_argument("--keep-duplicates", action="store_true",
                        help="keep trips identical to an earlier trip (feed artefacts)")
    parser.add_argument("--strict-times", action="store_true",
                        help="drop trips with equal consecutive departures (old loader)")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    trips = datasets.transit_trips(args.path, strict=args.strict_times,
                                    dedupe=not args.keep_duplicates)
    if args.resolution > 1:
        step = args.resolution
        trips = [[(t // step * step, a, b) for t, a, b in trip] for trip in trips]
    window = None
    if args.window_hours > 0:
        size = int(args.window_hours * 3600)
        t0 = min(trip[0][0] for trip in trips)
        blocks: dict[int, list] = {}
        for trip in trips:
            blocks.setdefault((trip[0][0] - t0) // size, []).append(trip)
        window, trips = max(blocks.items(), key=lambda kv: sum(map(len, kv[1])))
    inst = datasets.trip_instance(trips, args.path.parent.name)
    if args.problem == "free":
        inst = inst.free_end()
    tl = Timeline(inst)
    row = {"source": inst.name, "problem": args.problem, "resolution": args.resolution,
           "loader": "strict" if args.strict_times else "nonstrict",
           "window_hours": args.window_hours, "window": window,
           "dedupe": not args.keep_duplicates,
           "n": inst.n, "m": inst.m, "k": inst.k,
           "even": len(tl.even_components())}
    t0 = time.perf_counter()
    pair = solve_pairflow(inst, tl)
    row["pair"] = {"status": pair.status, "seconds": round(time.perf_counter() - t0, 2), **pair.stats}
    if pair.status == "YES":
        check_walks(inst, build_walks(inst, pair.tails, tl))
        row["witness"] = "checked"
    if args.branch_seconds > 0:
        t0 = time.perf_counter()
        branch = solve_branch(inst, tl=tl, max_seconds=args.branch_seconds)
        row["branch"] = {"status": branch.status, "flows": branch.flows,
                         "seconds": round(time.perf_counter() - t0, 2)}
    args.output.write_text(json.dumps(row) + "\n")
    print(json.dumps(row))


if __name__ == "__main__":
    main()
