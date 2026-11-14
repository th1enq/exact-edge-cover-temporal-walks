#!/usr/bin/env python3
"""Replay available transit networks through C++ pair-flow and branch-and-bound.

Uses the existing data loader to preserve the source data interpretation. All
algorithmic solving and witness construction/checking take place in C++.
Backtracking on all edge orders is intentionally restricted to small test suites.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments"))
import datasets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=ROOT / "cpp/build/nscover_solve")
    parser.add_argument("--data", type=Path, default=ROOT / "data/raw/transit")
    parser.add_argument("--cities", nargs="*")
    parser.add_argument("--window-threshold", type=int, default=250000)
    parser.add_argument("--branch-seconds", type=float, default=2)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = sorted(args.data.glob("*/network_temporal_day.csv"))
    if args.cities:
        paths = [p for p in paths if p.parent.name in args.cities]
    if not paths:
        raise SystemExit("No matching raw transit networks found")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    began = time.perf_counter()
    stats = Counter()
    with args.output.open("w") as out:
        for path in paths:
            trips = datasets.transit_trips(path)
            window = None
            if sum(map(len, trips)) > args.window_threshold:
                t0 = min(trip[0][0] for trip in trips)
                blocks = {}
                for trip in trips:
                    blocks.setdefault((trip[0][0] - t0) // 10800, []).append(trip)
                window, trips = max(blocks.items(), key=lambda item: sum(map(len, item[1])))
            base = datasets.trip_instance(trips, path.parent.name)
            for problem, inst in (("fix", base), ("free", base.free_end())):
                command = [str(args.binary.resolve()), "--summary", "--verify-branch",
                           "--max-flows", "2000", "--seconds", str(args.branch_seconds)]
                process = subprocess.run(command, input=json.dumps(inst.to_json()),
                                         text=True, capture_output=True, timeout=300)
                if process.returncode:
                    failure = args.output.with_suffix(".failure.json")
                    inst.save(failure)
                    raise RuntimeError(f"{path.parent.name}: {process.stderr}; input {failure}")
                result = json.loads(process.stdout)
                # Every real transit input is feasible by construction (one walk/trip).
                if result["status"] != "YES" or result.get("witness") != "checked":
                    raise AssertionError(result)
                row = {"source": path.parent.name, "problem": problem,
                       "n": inst.n, "m": inst.m, "k": inst.k,
                       "window_hours": 3 if window is not None else 0,
                       "window": window, **result}
                out.write(json.dumps(row) + "\n"); out.flush()
                print(json.dumps(row), flush=True)
                stats["instances"] += 1
                stats["branch_checked" if result["branch_verified"] else "branch_limit"] += 1
                stats["augmented"] += result["augmentations"] > 0
        summary = {"complete": True, "sources": len(paths), "seconds": time.perf_counter()-began, **stats}
        out.write(json.dumps(summary) + "\n")
        print(json.dumps(summary))


if __name__ == "__main__":
    main()
