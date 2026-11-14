#!/usr/bin/env python3
"""Real-data census: pair-flow solver and branch and bound on windows of real networks.

For every window and terminal scheme (see datasets.py) the row records the instance
size, the number of even components, and per solver the status, the number of maximum
flows / augmentations and the time.  Every YES of the pair-flow solver is turned into
explicit walks and checked.  The run stops cleanly after --seconds (default 270), so
one invocation stays under 5 minutes; the last line of the output says whether every
window was processed.

Example:
  census.py --sociopatterns highschool_2012.csv --durations 300 3600 0 \
            --schemes greedy tight1 --output hs2012.jsonl
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import datasets  # noqa: E402
from nscover import Timeline, build_walks, check_walks, solve_branch, solve_pairflow  # noqa: E402


def instances(args):
    """(source, scale, window index, scheme, instance)."""
    groups = []
    for path in args.sociopatterns or []:
        groups.append((Path(path).name, "contacts", datasets.sociopatterns(Path(path))))
    for path in args.copenhagen or []:
        groups.append((Path(path).name, "contacts", datasets.copenhagen(Path(path), args.min_rssi)))
    for path in args.transit or []:
        groups.append((Path(path).parent.name, "trips", datasets.transit_trips(Path(path))))
    for source, kind, data in groups:
        for duration in args.durations:
            scale = "full" if duration == 0 else f"{duration}s"
            if kind == "contacts":
                items = datasets.windows(data, duration or None)
            else:
                items = trip_windows(data, duration or None)
            for index, values in items:
                if kind == "contacts":
                    base = datasets.greedy_instance(values)
                else:
                    base = datasets.trip_instance(values)
                if base.m > args.max_edges:
                    continue
                for scheme in args.schemes:
                    if scheme == "greedy":
                        yield source, scale, index, "fix", base
                        yield source, scale, index, "free", base.free_end()
                    elif scheme.startswith("tight"):
                        pct = scheme.endswith("pct")
                        r = int(scheme[5:-3] if pct else scheme[5:])
                        remove = max(1, math.ceil(base.k * r / 100)) if pct else r
                        inst = datasets.tight_instance(base, remove, seed=index)
                        if inst is not None:
                            yield source, scale, index, scheme, inst


def trip_windows(trips, duration):
    if duration is None:
        yield 0, trips
        return
    t0 = min(trip[0][0] for trip in trips)
    groups: dict[int, list] = {}
    for trip in trips:
        first, last = (trip[0][0] - t0) // duration, (trip[-1][0] - t0) // duration
        if first == last:
            groups.setdefault(first, []).append(trip)
    yield from sorted(groups.items())


def row_for(inst, args) -> dict:
    tl = Timeline(inst)
    row = {"n": inst.n, "m": inst.m, "k": inst.k, "components": len(tl.components),
           "even": len(tl.even_components())}
    began = time.perf_counter()
    pair = solve_pairflow(inst, tl)
    row["pair"] = {"status": pair.status, "seconds": round(time.perf_counter() - began, 4),
                   **pair.stats}
    if pair.status == "YES":
        began = time.perf_counter()
        check_walks(inst, build_walks(inst, pair.tails, tl))
        row["witness_seconds"] = round(time.perf_counter() - began, 4)
    if inst.m <= args.branch_max_edges:
        began = time.perf_counter()
        branch = solve_branch(inst, max_flows=args.branch_max_flows, tl=tl)
        row["branch"] = {"status": branch.status, "flows": branch.flows,
                         "seconds": round(time.perf_counter() - began, 4)}
        if branch.status != "LIMIT":
            assert branch.status == pair.status, ("solvers disagree", row)
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sociopatterns", nargs="*")
    parser.add_argument("--copenhagen", nargs="*")
    parser.add_argument("--min-rssi", type=int)
    parser.add_argument("--transit", nargs="*")
    parser.add_argument("--durations", type=int, nargs="+", default=[300, 3600, 0],
                        help="window lengths in seconds; 0 = the whole source")
    parser.add_argument("--schemes", nargs="+", default=["greedy", "tight1"],
                        help="greedy, tightR (remove R walks), tightRpct (remove R%%)")
    parser.add_argument("--max-edges", type=int, default=250_000)
    parser.add_argument("--branch-max-edges", type=int, default=50_000)
    parser.add_argument("--branch-max-flows", type=int, default=200)
    parser.add_argument("--seconds", type=float, default=270)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    began = time.time()
    done = True
    with args.output.open("w", encoding="utf-8") as out:
        for source, scale, index, scheme, inst in instances(args):
            if time.time() - began > args.seconds:
                done = False
                break
            row = {"source": source, "scale": scale, "window": index, "scheme": scheme}
            row.update(row_for(inst, args))
            out.write(json.dumps(row) + "\n")
            out.flush()
        out.write(json.dumps({"complete": done, "seconds": round(time.time() - began, 1)}) + "\n")
    print("complete" if done else "stopped at the time budget", args.output)


if __name__ == "__main__":
    main()
