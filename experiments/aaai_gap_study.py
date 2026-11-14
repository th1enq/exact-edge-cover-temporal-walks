#!/usr/bin/env python3
"""Seeded small-instance audit of the unchanged Definition 6.3 reduction.

Condition (ii) is orientation-dependent. Here cond_ii means that SOME orientation
satisfying (i) and the FIX endpoint constraints has no walk-free snapshot component.
It is false by convention if (i) has no witness. We also report (ii) on the initial
chain witness, since testing just that witness can give false negatives. The
existential check enumerates at most 2**7 temporal orientations independently of
solve_pairflow; it is not inferred from the truth bit.

No FREE run: with start terminals only, balance at every other vertex cannot
represent walks with free endpoints. That variant needs a different degree rule.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path
import random
import signal
import sys
import time

STARTED = time.monotonic()
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.aaai_static_check import static_graph  # noqa: E402
from nscover import Instance, Timeline, brute_force, solve_pairflow  # noqa: E402
from nscover.chainflow import ChainNetwork, prefix_caps, walk_counts  # noqa: E402
from nscover.maxflow import orient_with_indegree  # noqa: E402

N = 20_000
CROSSCHECK = 2_000
SEED = 20261030
LIMIT_SECONDS = 245
OUTPUT = ROOT / "results/aaai-gap-20261030/summary.json"


class TimeGuard(Exception):
    pass


def static_feasibility(inst):
    """Return (balanced orientation, terminal per weak component).

    Fix terminal edges first. For every remaining vertex, if d is its number of
    flexible incidences and f_out/f_in count fixed arcs, its required number of
    flexible heads is (d + f_out - f_in)/2. Use bipartite flow to choose heads.
    """
    arcs = static_graph([(i, *e) for i, e in enumerate(inst.edges)],
                        inst.start, inst.end)
    vertices = list(dict.fromkeys(x for p, q, _ in arcs for x in (p, q)))
    ids = {v: i for i, v in enumerate(vertices)}
    size = len(vertices)
    parent = list(range(size))

    def find(v):
        while parent[v] != v:
            parent[v] = parent[parent[v]]
            v = parent[v]
        return v

    def terminal(v):
        z, _ = v
        return z[0] if isinstance(z, tuple) and z[0] in ("s", "e") else None

    balance = [0] * size  # fixed out minus fixed in
    degree = [0] * size
    flexible = []
    for p, q, directed in arcs:
        a, b = ids[p], ids[q]
        parent[find(a)] = find(b)
        tp, tq = terminal(p), terminal(q)
        if tp or tq:
            if tp == "e" or tq == "s":
                a, b = b, a
            directed = True
        if directed:
            balance[a] += 1
            balance[b] -= 1
        else:
            flexible.append((a, b))
            degree[a] += 1
            degree[b] += 1
    covered = {find(ids[v]) for v in vertices if terminal(v)}
    connected = all(find(v) in covered for v in range(size))
    targets = {}
    for v, label in enumerate(vertices):
        if terminal(label):
            targets[v] = 0  # terminal edge was already fixed
            continue
        twice = degree[v] + balance[v]
        if twice % 2 or not 0 <= twice // 2 <= degree[v]:
            return False, connected
        targets[v] = twice // 2
    oriented = orient_with_indegree(list(range(size)), flexible, targets) is not None
    return oriented, connected


def orientation_conditions(inst, tl, tails):
    before, final = walk_counts(inst, tl, tails)
    valid_i = (all(c >= 0 for row in before for c in row.values())
               and min(final) >= 0 and final == inst.end)
    dead = [comp.index for comp, counts in zip(tl.components, before)
            if sum(counts.values()) < 1]
    if valid_i:
        assert all(tl.components[c].even for c in dead), "non-even dead component"
    return valid_i, not dead, dead


def conditions(inst, tl):
    """Expose the chain test; enumerate repairs rather than equating ii with truth."""
    caps = prefix_caps(inst, tl)
    if caps is None:
        return False, False, None, []
    chain = ChainNetwork(inst, tl, caps, backend="augment-bfs")
    if not chain.complete:
        return False, False, None, []
    valid_i, initial_ii, dead = orientation_conditions(inst, tl, chain.tails())
    assert valid_i, "chain witness violates (i) or endpoints"
    if initial_ii:
        return True, True, True, []
    for sides in itertools.product((0, 1), repeat=inst.m):
        tails = [edge[side] for edge, side in zip(inst.edges, sides)]
        valid_i, valid_ii, _ = orientation_conditions(inst, tl, tails)
        if valid_i and valid_ii:
            return True, True, False, dead
    return True, False, False, dead


def random_instance(rng, index):
    n, m, k = rng.randint(2, 5), rng.randint(1, 7), rng.randint(1, 3)
    edges = []
    for _ in range(m):
        u, v = rng.sample(range(n), 2)
        edges.append((u, v, rng.randint(1, 3)))
    start, end = [0] * n, [0] * n
    for _ in range(k):
        start[rng.randrange(n)] += 1
        end[rng.randrange(n)] += 1
    return Instance(n, edges, start, end, f"fix-{index:05d}")


def main():
    summary = {
        "seed": SEED, "requested_instances": N, "completed_instances": 0,
        "time_limit_seconds": LIMIT_SECONDS, "time_guard_triggered": False,
        "truth_solver": "solve_pairflow (augment-bfs)",
        "cond_ii_definition": __doc__.split("Condition (ii)", 1)[1].split("No FREE", 1)[0].strip(),
        "counts": {key: 0 for key in (
            "truth", "static", "cond_i", "cond_ii", "static_orientation_a",
            "static_connectivity_b", "truth_not_static", "static_not_truth",
            "gaps_with_cond_ii_false", "gaps_with_cond_ii_true",
            "truth_ne_static_and_cond_ii", "static_ne_cond_i",
            "static_orientation_a_ne_cond_i", "truth_ne_cond_i_and_cond_ii",
            "initial_chain_ii_false_but_repairable", "brute_crosschecked",
            "brute_pairflow_mismatches")},
        "smallest_mismatches": {}, "smallest_static_not_truth": [],
        "free": {"status": "skipped", "reason":
                 "Start-only terminals require free endpoint imbalance; the specified "
                 "balance-at-every-nonterminal test does not model FREE."},
    }
    counts = summary["counts"]
    rng = random.Random(SEED)
    # Uniformly spread the oracle subset over the entire run, using a separate RNG.
    subset = set(random.Random(SEED + 1).sample(range(N), CROSSCHECK))

    def remember(key, record):
        examples = summary["smallest_mismatches"].setdefault(key, [])
        examples.append(record)
        examples.sort(key=lambda r: (len(r["instance"]["edges"]),
                                    r["instance"]["num_vertices"],
                                    sum(r["instance"]["start"]), r["instance"]["name"]))
        del examples[3:]

    def timeout(signum, frame):
        raise TimeGuard()

    old_handler = signal.signal(signal.SIGALRM, timeout)
    signal.setitimer(signal.ITIMER_REAL, max(.001, LIMIT_SECONDS - (time.monotonic() - STARTED)))
    try:
        for index in range(N):
            inst = random_instance(rng, index)
            tl = Timeline(inst)
            truth = solve_pairflow(inst, tl, backend="augment-bfs").status == "YES"
            cond_i, cond_ii, initial_ii, dead = conditions(inst, tl)
            orientation, connectivity = static_feasibility(inst)
            static = orientation and connectivity
            record = {"instance": inst.to_json(), "truth": truth, "static": static,
                      "cond_i": cond_i, "cond_ii": cond_ii,
                      "initial_chain_cond_ii": initial_ii,
                      "initial_dead_even_components": dead,
                      "static_orientation_a": orientation,
                      "static_connectivity_b": connectivity}
            flags = {
                "truth": truth, "static": static, "cond_i": cond_i, "cond_ii": cond_ii,
                "static_orientation_a": orientation, "static_connectivity_b": connectivity,
                "truth_not_static": truth and not static,
                "static_not_truth": static and not truth,
                "gaps_with_cond_ii_false": static and not truth and not cond_ii,
                "gaps_with_cond_ii_true": static and not truth and cond_ii,
                "truth_ne_static_and_cond_ii": truth != (static and cond_ii),
                "static_ne_cond_i": static != cond_i,
                "static_orientation_a_ne_cond_i": orientation != cond_i,
                "truth_ne_cond_i_and_cond_ii": truth != (cond_i and cond_ii),
                "initial_chain_ii_false_but_repairable": initial_ii is False and cond_ii,
            }
            if index in subset:
                oracle = brute_force(inst)
                flags["brute_crosschecked"] = True
                flags["brute_pairflow_mismatches"] = oracle != truth
                if oracle != truth:
                    remember("brute_pairflow_mismatches", dict(record, brute_force=oracle))
            for key, flag in flags.items():
                counts[key] += int(flag)
            for key in ("truth_not_static", "gaps_with_cond_ii_true",
                        "truth_ne_static_and_cond_ii", "static_ne_cond_i",
                        "static_orientation_a_ne_cond_i", "truth_ne_cond_i_and_cond_ii"):
                if flags[key]:
                    remember(key, record)
            if static and not truth:
                examples = summary["smallest_static_not_truth"]
                examples.append(record)
                examples.sort(key=lambda r: (len(r["instance"]["edges"]),
                                            r["instance"]["num_vertices"],
                                            sum(r["instance"]["start"]),
                                            r["instance"]["name"]))
                del examples[3:]
            summary["completed_instances"] += 1
            if (index + 1) % 5000 == 0:
                print(f"Completed {index + 1}/{N} in {time.monotonic() - STARTED:.2f}s", flush=True)
    except TimeGuard:
        summary["time_guard_triggered"] = True
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)
    summary["elapsed_seconds"] = round(time.monotonic() - STARTED, 6)
    summary["invariants"] = {
        "truth_implies_static": counts["truth_not_static"] == 0,
        "every_static_not_truth_has_cond_ii_false": counts["gaps_with_cond_ii_true"] == 0,
        "truth_equals_static_and_cond_ii": counts["truth_ne_static_and_cond_ii"] == 0,
        "static_equals_cond_i": counts["static_ne_cond_i"] == 0,
        "static_orientation_a_equals_cond_i": counts["static_orientation_a_ne_cond_i"] == 0,
        "truth_equals_cond_i_and_cond_ii": counts["truth_ne_cond_i_and_cond_ii"] == 0,
        "brute_equals_pairflow_on_subset": counts["brute_pairflow_mismatches"] == 0,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Saved {OUTPUT}")
    return 1 if summary["time_guard_triggered"] else 0


if __name__ == "__main__":
    sys.exit(main())
