#!/usr/bin/env python3
"""Does the static reduction (AAAI 2025, Def. 6.3) decide NS-FIX correctly under EITHER reading?

Decision rule under test (their Thm 6.3): YES iff the mixed multigraph S has a balanced
orientation and every component of S touches a terminal.  Two readings of where the END
terminal edge goes:
  last  - attached to the largest label, time t_max + 1 (preprocessing text, Fig. 3)
  first - attached to v_0, i.e. time 0 (the literal sentence for end terminals)
Truth is solve_pairflow, which agreed with brute force on 6,864 + 2,000 small instances.
Same instance distribution and seed as aaai_gap_study.py.  FIX only.
"""
import json, random, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments import aaai_gap_study as g  # noqa: E402
from nscover import Timeline, solve_pairflow  # noqa: E402

N, SEED, LIMIT = 20_000, 20261030, 240
OUT = ROOT / "results/aaai-reading-20261101/summary.json"


def static_graph(edges, start, end, reading):
    last = max(t for *_, t in edges) + 1
    end_time = last if reading == "last" else 0
    temporal = list(edges)
    for v, c in enumerate(start):
        temporal += [(None, ("s", v, i), v, 0) for i in range(c)]
    for v, c in enumerate(end):
        temporal += [(None, v, ("e", v, i), end_time) for i in range(c)]
    labels = {}
    for _, a, b, t in temporal:
        for z in (a, b):
            labels.setdefault(z, set()).add(t)
    arcs = [((a, t), (b, t), False) for _, a, b, t in temporal]
    for z, times in labels.items():
        times = sorted(times)
        for t, nxt in zip(times, times[1:]):
            before = sum(1 for _, a, b, s in temporal if z in (a, b) and s <= t)
            after = sum(1 for _, a, b, s in temporal if z in (a, b) and s > t)
            alpha = min(before, after)
            arcs += [((z, t), (z, nxt), i < (alpha + 1) // 2) for i in range(alpha)]
    return arcs


def main():
    t0 = time.monotonic()
    rng = random.Random(SEED)
    res = {r: {"false_yes": 0, "false_no": 0, "agree": 0} for r in ("last", "first")}
    ex = {r: {"false_yes": [], "false_no": []} for r in res}
    done = 0
    for i in range(N):
        if time.monotonic() - t0 > LIMIT:
            break
        inst = g.random_instance(rng, i)
        truth = solve_pairflow(inst, Timeline(inst), backend="augment-bfs").status == "YES"
        for r in res:
            g.static_graph = lambda e, s, en, r=r: static_graph(e, s, en, r)
            orient, conn = g.static_feasibility(inst)
            s = orient and conn
            key = "agree" if s == truth else ("false_yes" if s else "false_no")
            res[r][key] += 1
            if key != "agree":
                ex[r][key].append(inst.to_json())
                ex[r][key].sort(key=lambda d: (len(d["edges"]), d["num_vertices"]))
                del ex[r][key][2:]
        done += 1
    out = {"seed": SEED, "instances": done, "requested": N, "seconds": round(time.monotonic() - t0, 1),
           "counts": res, "smallest_examples": ex}
    OUT.write_text(json.dumps(out, indent=1))
    print(json.dumps({"instances": done, "counts": res}, indent=1))


main()
