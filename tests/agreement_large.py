#!/usr/bin/env python3
"""Pair-flow solver vs branch and bound on instances too large for the oracle.

Instances are dense in even components (cycle snapshots on few vertices), so the
chain network often leaves several components without a walk.  Branch and bound is
exact but exponential; cases where it hits --max-flows are skipped and counted.
Every YES is checked through explicit walks.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nscover import Timeline, build_walks, check_walks, solve_branch, solve_pairflow  # noqa: E402
from nscover.generators import cycle_instance, random_end  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=240)
    parser.add_argument("--seed", type=int, default=2)
    parser.add_argument("--max-flows", type=int, default=2000)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rng = random.Random(args.seed)
    stats: Counter = Counter()
    began = time.time()
    while time.time() - began < args.seconds:
        base = cycle_instance(rng, max_n=rng.randint(4, 9), max_snapshots=rng.randint(4, 14))
        for kind, inst in (("free", base.free_end()), ("fix", base.with_end(random_end(rng, base)))):
            tl = Timeline(inst)
            pair = solve_pairflow(inst, tl)
            branch = solve_branch(inst, max_flows=args.max_flows, tl=tl)
            if branch.status == "LIMIT":
                stats[f"{kind}_branch_limit"] += 1
                if pair.status == "YES":
                    check_walks(inst, build_walks(inst, pair.tails, tl))
                continue
            assert pair.status == branch.status, (inst, pair, branch)
            if pair.status == "YES":
                check_walks(inst, build_walks(inst, pair.tails, tl))
            stats[f"{kind}_cases"] += 1
            stats[f"{kind}_yes"] += pair.status == "YES"
            stats[f"{kind}_edges_total"] += inst.m
            dead = pair.stats.get("dead", 0)
            stats[f"{kind}_dead_ge2"] += dead >= 2
            stats[f"{kind}_max_dead"] = max(stats[f"{kind}_max_dead"], dead)
            stats[f"{kind}_max_augmentations"] = max(stats[f"{kind}_max_augmentations"],
                                                     pair.stats.get("augmentations", 0))
            stats[f"{kind}_max_branch_flows"] = max(stats[f"{kind}_max_branch_flows"], branch.flows)
    stats["seconds"] = round(time.time() - began, 1)
    print(json.dumps(dict(stats), indent=1, sort_keys=True))
    if args.output:
        args.output.write_text(json.dumps(dict(stats), indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
