#!/usr/bin/env python3
"""Randomised agreement: pair-flow solver vs branch and bound vs exhaustive oracle.

Every YES answer of both solvers is turned into explicit walks and checked by
check_walks.  The run stops after --seconds (default 240) so it stays under 5 minutes.
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

from nscover import (Timeline, brute_force, build_walks, check_walks,  # noqa: E402
                     solve_branch, solve_pairflow)
from nscover.chainflow import ChainNetwork, prefix_caps  # noqa: E402
from nscover.generators import cycle_instance, random_end, random_instance  # noqa: E402

BACKENDS = ("augment", "augment-bfs", "python", "scipy")


def check_one(inst, stats: Counter, kind: str) -> None:
    tl = Timeline(inst)
    truth = brute_force(inst)
    caps = prefix_caps(inst, tl)
    if caps is not None:  # the three max-flow backends agree on completeness
        done = {ChainNetwork(inst, tl, caps, b).complete for b in BACKENDS}
        assert len(done) == 1, ("backends", inst)
    pair = solve_pairflow(inst, tl)
    branch = solve_branch(inst, tl=tl)
    assert (pair.status == "YES") == truth, ("pairflow", inst, pair)
    assert (branch.status == "YES") == truth, ("branch", inst, branch)
    for res in (pair, branch):
        if res.status == "YES":
            check_walks(inst, build_walks(inst, res.tails, tl))
    stats[f"{kind}_cases"] += 1
    stats[f"{kind}_yes"] += truth
    stats[f"{kind}_with_even"] += bool(tl.even_components())
    stats[f"{kind}_augmented"] += pair.stats.get("augmentations", 0) > 0
    stats[f"{kind}_no_after_augment"] += pair.stats.get("reason") == "no augmenting path"
    stats[f"{kind}_max_branch_flows"] = max(stats[f"{kind}_max_branch_flows"], branch.flows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=240)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rng = random.Random(args.seed)
    stats: Counter = Counter()
    began = time.time()
    while time.time() - began < args.seconds:
        family = "cycle" if rng.random() < 0.6 else "random"
        inst = cycle_instance(rng) if family == "cycle" else random_instance(rng)
        if len(inst.edges) > 11:
            continue
        check_one(inst.free_end(), stats, f"{family}_free")
        check_one(inst.with_end(random_end(rng, inst)), stats, f"{family}_fix")
    stats["seconds"] = round(time.time() - began, 1)
    print(json.dumps(dict(stats), indent=1, sort_keys=True))
    if args.output:
        args.output.write_text(json.dumps(dict(stats), indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
