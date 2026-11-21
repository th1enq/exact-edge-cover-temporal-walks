#!/usr/bin/env python3
"""Compare scratch and incremental PF; flush one JSON line per solver call.

A hard wall-clock budget covers generation, solving, and witness validation.
Even-rich graphs use the original generator's deterministic seed (20261113).
"""
from __future__ import annotations

import argparse
import json
import platform
import signal
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.even_rich_bench import SEED, variants
from experiments.family import family
from nscover import build_walks, check_walks, solve_pairflow


class Deadline(Exception):
    pass


def alarm(signum, frame):
    raise Deadline


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--family", choices=("shortage", "sparse", "dense", "even-rich"),
                   default="even-rich")
    p.add_argument("--m", type=int, default=200)
    p.add_argument("--count", type=int, default=1000000, help="maximum graphs per family")
    p.add_argument("--e", type=int, nargs="+", default=[50, 100, 200, 500, 1000])
    p.add_argument("--variants", nargs="+", choices=("scratch", "incremental"),
                   default=["scratch", "incremental"])
    p.add_argument("--seconds", type=float, default=240)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if not 0 < args.seconds <= 280 or args.count < 1 or args.m < 1:
        p.error("require 0 < seconds <= 280, count >= 1 and m >= 1")
    args.output.parent.mkdir(parents=True, exist_ok=True)

    def instances():
        if args.family == "shortage":
            for e in args.e:
                yield {"family": "shortage", "e": e, "index": 0, "problem": "FREE-shortage"}, family(e)
        else:
            families = ["sparse", "dense"] if args.family == "even-rich" else [args.family]
            # Interleave families so a budget cutoff samples both.
            for index in range(args.count):
                for name in families:
                    for problem, inst in variants(name, args.m, index):
                        yield {"family": name, "requested_m": args.m, "index": index,
                               "problem": problem}, inst

    began = time.perf_counter()
    rows = 0
    context = {}
    with args.output.open("w", encoding="utf-8") as out:
        def write(row):
            out.write(json.dumps(row) + "\n")
            out.flush()

        write({"meta": True, "seed": SEED, "argv": sys.argv, "python": sys.version,
               "platform": platform.platform(), "machine": platform.machine(),
               "timing": "solve_pairflow including Timeline; witness checks excluded"})
        old_handler = signal.signal(signal.SIGALRM, alarm)
        signal.setitimer(signal.ITIMER_REAL, args.seconds)
        try:
            for context, inst in instances():
                answer = None
                for variant in args.variants:
                    context = {**context, "variant": variant}
                    t0 = time.perf_counter()
                    result = solve_pairflow(inst, reorient=variant)
                    elapsed = time.perf_counter() - t0
                    if answer is not None:
                        assert result.status == answer, (context, result.status, answer)
                    answer = result.status
                    if result.status == "YES":
                        check_walks(inst, build_walks(inst, result.tails))
                    write({**context, "m": inst.m, "n": inst.n, "answer": result.status,
                           "augmentations": result.stats.get("augmentations", 0),
                           "seconds": elapsed, "walks_checked": result.status == "YES",
                           **({"path_reversals": result.stats["path_reversals"]}
                              if variant == "incremental" else {})})
                    rows += 1
        except Deadline:
            write({"truncated": True, "context": context, "rows": rows,
                   "elapsed": time.perf_counter() - began})
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_handler)
    print(json.dumps({"output": str(args.output), "rows": rows,
                      "seconds": time.perf_counter() - began}), flush=True)


if __name__ == "__main__":
    main()
