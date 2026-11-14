#!/usr/bin/env python3
"""Benchmark on synthetic instances in which every snapshot component is even.

Walks move in pairs. At every time each pair either (a) crosses a double edge,
(b) lets one of its walks traverse a cycle through its vertex, or (c) moves to a
new vertex along two internally disjoint paths, which together form a cycle. Every
edge set added at a time is a union of closed trails or of two parallel trails, so
every vertex has even degree in every snapshot, and every walk counter stays even.
Hence every component of every snapshot is an even component, and condition (ii)
of Theorem 1 is the whole difficulty: every component is balanced, so the counting
condition (i) alone never rejects a FREE instance.

Families (vertex labels and edge order are shuffled, so the initial maximum flow
does not see the planted orientation):
  sparse   n about m/3, so components of one time rarely touch
  dense    n about 2*sqrt(m), so components of one time often merge
Variants of every generated instance:
  FIX-yes  planted start and end vectors (feasible by construction)
  FREE-yes planted start vector, free ends (feasible by construction)
  FIX-cut  one pair removed from the start and from its planted end
  FREE-cut one pair removed from the start
The cut variants may or may not be feasible; the answer is decided by PF and
cross-checked by exhaustive search (m <= --oracle-m) and by branch and bound where
it finishes. FIX variants are also given to the rule derived from the static graph
of Deligkas et al. (AAAI 2025), as in experiments/aaai_baseline_bench.py.

One JSON line per (instance, variant). Every YES answer of PF is turned into walks
and checked against the definition.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import random
import signal
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nscover import (Instance, Timeline, brute_force, build_walks,  # noqa: E402
                     check_walks, solve_branch, solve_pairflow)

SEED = 20261113


class Deadline(Exception):
    pass


def _alarm(signum, frame):
    raise Deadline


def rng_for(tag: str) -> random.Random:
    return random.Random(int.from_bytes(hashlib.sha256(tag.encode()).digest()[:8]))


def distinct(rng: random.Random, n: int, exclude: int, k: int) -> list[int]:
    chosen: list[int] = []
    seen = {exclude}
    while len(chosen) < k:
        x = rng.randrange(n)
        if x not in seen:
            seen.add(x)
            chosen.append(x)
    return chosen


def paired_instance(family: str, m: int, rng: random.Random):
    if family == "sparse":
        n = max(8, m // 3)
    else:
        n = max(8, int(2 * m ** 0.5))
    pairs = max(1, round(m ** 0.5 / 2))
    pos = [rng.randrange(n) for _ in range(pairs)]
    start_pos = pos[:]
    edges: list[tuple[int, int, int]] = []
    t = 0
    while len(edges) < m:
        t += 1
        order = list(range(pairs))
        rng.shuffle(order)
        for p in order:
            if len(edges) >= m or rng.random() < 0.3:
                continue
            u = pos[p]
            r = rng.random()
            if r < 0.25:                      # (a) both walks cross a double edge
                v = distinct(rng, n, u, 1)[0]
                edges += [(u, v, t), (u, v, t)]
                pos[p] = v
            elif r < 0.55:                    # (b) one walk traverses a cycle
                length = rng.randint(3, 6)
                cyc = [u] + distinct(rng, n, u, length - 1)
                edges += [(cyc[i], cyc[(i + 1) % length], t) for i in range(length)]
            else:                             # (c) two disjoint paths from u to v
                l1, l2 = rng.randint(1, 3), rng.randint(1, 3)
                inner = distinct(rng, n, u, l1 + l2 - 1)
                v, mid1, mid2 = inner[0], inner[1:l1], inner[l1:]
                for path in ([u] + mid1 + [v], [u] + mid2 + [v]):
                    edges += [(a, b, t) for a, b in zip(path, path[1:])]
                pos[p] = v
    perm = list(range(n))
    rng.shuffle(perm)
    edges = [(perm[a], perm[b], tt) for a, b, tt in edges]
    rng.shuffle(edges)
    start, end = [0] * n, [0] * n
    for v in start_pos:
        start[perm[v]] += 2
    for v in pos:
        end[perm[v]] += 2
    cut = rng.randrange(pairs)
    return n, edges, start, end, perm[start_pos[cut]], perm[pos[cut]]


def variants(family: str, m: int, index: int):
    rng = rng_for(f"{SEED}:{family}:{m}:{index}")
    n, edges, start, end, cut_s, cut_e = paired_instance(family, m, rng)
    name = f"{family}-m{m}-{index:03d}"
    cut_start = start[:]
    cut_start[cut_s] -= 2
    cut_end = end[:]
    cut_end[cut_e] -= 2
    yield "FIX-yes", Instance(n, edges, start[:], end[:], name)
    yield "FREE-yes", Instance(n, edges, start[:], None, name)
    yield "FIX-cut", Instance(n, edges, cut_start[:], cut_end, name)
    yield "FREE-cut", Instance(n, edges, cut_start[:], None, name)


_static_rule = None


def static_rule(inst: Instance) -> bool:
    global _static_rule
    if _static_rule is None:
        from experiments import aaai_baseline_bench as bench  # loads only static_graph
        _static_rule = bench.baseline
    return _static_rule(inst)


def timed(fn, seconds: float):
    signal.signal(signal.SIGALRM, _alarm)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    t0 = time.perf_counter()
    try:
        return fn(), time.perf_counter() - t0
    except Deadline:
        return None, time.perf_counter() - t0
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def run(args) -> None:
    out = args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    began = time.time()
    meta = {"meta": True, "seed": SEED, "argv": sys.argv, "python": sys.version,
            "platform": platform.platform(), "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    with out.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps(meta) + "\n")
        for family in args.families:
            for index in range(args.count):
                if time.time() - began > args.seconds:
                    fh.write(json.dumps({"truncated": True, "family": family, "m": args.m,
                                         "index": index}) + "\n")
                    return
                for variant, inst in variants(family, args.m, index):
                    tl = Timeline(inst)
                    row = {"family": family, "m": inst.m, "index": index, "variant": variant,
                           "n": inst.n, "k": inst.k, "times": len({t for *_, t in inst.edges}),
                           "components": len(tl.components),
                           "even": len(tl.even_components())}
                    res, sec = timed(lambda: solve_pairflow(inst), args.pf_seconds)
                    if res is None:
                        row["pf"] = {"status": "TIMEOUT", "seconds": round(sec, 4)}
                    else:
                        row["pf"] = {"status": res.status, "seconds": round(sec, 4),
                                     **{k: v for k, v in res.stats.items()}}
                        if res.status == "YES":
                            check_walks(inst, build_walks(inst, res.tails))
                            row["pf"]["walks_checked"] = True
                    if inst.m <= args.oracle_m:
                        truth = brute_force(inst)
                        row["oracle"] = "YES" if truth else "NO"
                        assert res is None or row["oracle"] == res.status, row
                    if inst.m <= args.branch_m:
                        br, bsec = timed(lambda: solve_branch(
                            inst, max_flows=args.branch_flows,
                            max_seconds=args.branch_seconds), args.branch_seconds + 5)
                        status = "LIMIT" if br is None else br.status
                        row["bb"] = {"status": status, "seconds": round(bsec, 4),
                                     "flows": None if br is None else br.flows}
                        if res is not None and status in ("YES", "NO"):
                            assert status == res.status, row
                    if inst.end is not None and inst.m <= args.static_m:
                        ans, ssec = timed(lambda: static_rule(inst), args.static_seconds)
                        row["static"] = {"answer": None if ans is None else
                                         ("YES" if ans else "NO"), "seconds": round(ssec, 4)}
                    fh.write(json.dumps(row) + "\n")
                    fh.flush()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--m", type=int, required=True)
    p.add_argument("--count", type=int, default=20)
    p.add_argument("--families", nargs="+", default=["sparse", "dense"])
    p.add_argument("--seconds", type=float, default=1800, help="budget per command")
    p.add_argument("--pf-seconds", type=float, default=600)
    p.add_argument("--oracle-m", type=int, default=12)
    p.add_argument("--branch-m", type=int, default=2000)
    p.add_argument("--branch-flows", type=int, default=2000)
    p.add_argument("--branch-seconds", type=float, default=10)
    p.add_argument("--static-m", type=int, default=2000)
    p.add_argument("--static-seconds", type=float, default=60)
    p.add_argument("--output", type=Path, required=True)
    run(p.parse_args())


if __name__ == "__main__":
    main()
