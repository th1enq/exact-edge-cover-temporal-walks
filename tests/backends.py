#!/usr/bin/env python3
"""The four chain-network backends agree on random networks with tightened caps.

Caps are tightened at random (also non-monotonically, as in branch and bound), and every
complete orientation is checked against the caps directly.
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

from nscover import Instance, Timeline  # noqa: E402
from nscover.chainflow import ChainNetwork, prefix_caps  # noqa: E402

BACKENDS = ("augment", "augment-bfs", "python", "scipy")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=120)
    parser.add_argument("--seed", type=int, default=8)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rng = random.Random(args.seed)
    stats: Counter = Counter()
    began = time.time()
    while time.time() - began < args.seconds:
        n, m, horizon = rng.randint(2, 12), rng.randint(1, 80), rng.randint(1, 30)
        edges = [(*rng.sample(range(n), 2), rng.randint(1, horizon)) for _ in range(m)]
        inst = Instance(n, edges, [rng.randint(0, 3) for _ in range(n)])
        tl = Timeline(inst)
        caps = prefix_caps(inst, tl)
        rate = rng.choice((0.0, 0.03, 0.3))
        for row in caps:
            for j in range(len(row)):
                if rng.random() < rate:
                    row[j] = max(0, row[j] - rng.randint(1, 3))
        nets = [ChainNetwork(inst, tl, caps, b) for b in BACKENDS]
        assert len({net.complete for net in nets}) == 1, inst
        stats["cases"] += 1
        stats["complete"] += nets[0].complete
        for net in nets:
            if not net.complete:
                continue
            tails = net.tails()
            for v in range(n):
                prefix = 0
                for j, t in enumerate(tl.appear_times[v]):
                    prefix += sum(1 for e, (a, b, s) in enumerate(edges)
                                  if s == t and tails[e] == v)
                    assert prefix <= caps[v][j], (inst, v, j)
    stats["seconds"] = round(time.time() - began, 1)
    print(json.dumps(dict(stats), sort_keys=True))
    if args.output:
        args.output.write_text(json.dumps(dict(stats), sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
