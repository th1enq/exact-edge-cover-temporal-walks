#!/usr/bin/env python3
"""Paired NS-FIX timing/correctness benchmark; no third-party dependencies.

Run one size per command to stay below five minutes, then --report.
The baseline deliberately retains the known false-YES behavior.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import signal
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments import aaai_gap_study as gap
from experiments.aaai_static_check import EDGES, START, END
from nscover import Instance, Timeline, brute_force, solve_pairflow
from nscover.chainflow import DEFAULT_BACKEND

OUT = ROOT / "results/baseline-bench-20261101"
SIZES = (5, 7, 20, 50, 100, 200, 400, 800, 1600)
SEED = 20261101
FAMILIES = ("planted-YES", "perturbed", "many-even-components")


def load_static_graph():
    # Importing aaai_reading_study executes main() unconditionally. Compile ONLY
    # its unchanged function node, avoiding that unrelated 240-second study.
    path = ROOT / "experiments/aaai_reading_study.py"
    tree = ast.parse(path.read_text(), filename=str(path))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                and n.name == "static_graph")
    namespace = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace)
    return namespace["static_graph"]


static_graph = load_static_graph()
# Same binding as the reading study's 'last' experiment. No function logic edited.
gap.static_graph = lambda edges, start, end: static_graph(edges, start, end, "last")


def baseline(inst):
    # static_feasibility constructs S internally exactly once.
    balanced, connected = gap.static_feasibility(inst)
    return balanced and connected


def ours(inst):
    result = solve_pairflow(inst)  # default backend; fresh Timeline inside call
    if result.status not in ("YES", "NO"):
        raise RuntimeError(f"nondecision: {result.status}")
    return result.status == "YES"


def planted(m, rng):
    n = min(5, m) if m <= 7 else max(6, int(m ** .5) + 2)
    k = rng.randint(1, min(5, m))
    starts = [rng.randrange(n) for _ in range(k)]
    positions, stamps = starts[:], [1] * k
    start, end = [0] * n, [0] * n
    for v in starts:
        start[v] += 1
    edges, walks = [], [[] for _ in range(k)]
    for _ in range(m):
        w = rng.randrange(k)
        u = positions[w]
        v = rng.randrange(n - 1)
        v += v >= u
        stamps[w] += rng.choice((0, 0, 1))
        walks[w].append(len(edges))
        edges.append((u, v, stamps[w]))
        positions[w] = v
    for v in positions:
        end[v] += 1
    return Instance(n, edges, start, end), {"walk_edge_ids": walks}


def make_instance(family, m, index, seed):
    # Each cell/index is independent of which other sizes ran or timed out.
    tag = f"{seed}:{family}:{m}:{index}"
    rng = random.Random(int.from_bytes(hashlib.sha256(tag.encode()).digest()[:8]))
    if family in ("planted-YES", "perturbed"):
        # Paired family shares its planted input before perturbation.
        tag = f"{seed}:planted-YES:{m}:{index}"
        rng = random.Random(int.from_bytes(hashlib.sha256(tag.encode()).digest()[:8]))
        inst, detail = planted(m, rng)
        if family == "perturbed":
            detail = {"parent": f"planted-YES-m{m}-{index:02d}"}
            if index % 4 != 3:
                u = rng.choice([v for v, c in enumerate(inst.end) if c])
                v = rng.choice([v for v in range(inst.n) if v != u])
                inst.end[u] -= 1
                inst.end[v] += 1
                detail["perturbation"] = {"end_unit_move": [u, v]}
            else:
                e = rng.randrange(m)
                u, v, t = inst.edges[e]
                new = max(x[2] for x in inst.edges) + 1
                if new == t:
                    new += 1
                inst.edges[e] = (u, v, new)
                detail["perturbation"] = {"edge": e, "old_time": t, "new_time": new}
    elif family == "counterexample":
        inst = Instance(5, [(u, v, t) for _, u, v, t in EDGES], START[:], END[:])
        detail = {"source": "experiments/aaai_static_check.py", "identical_replicate": index}
    else:
        # A time-1 path visits one anchor from each vertex-disjoint triangle.
        # All triangles occur later, at distinct times. The sole token must end
        # at y and cannot access any triangle: k genuinely even dead components.
        k = (m - 1) // 4
        n = 3 * k + 2 + (m - (4 * k + 1))
        anchors = [3 * j for j in range(k)]
        x, y = 3 * k, 3 * k + 1
        path = [x] + anchors + list(range(3 * k + 2, n)) + [y]
        edges = [(a, b, 1) for a, b in zip(path, path[1:])]
        for j, a in enumerate(anchors):
            edges.extend([(a, a + 1, j + 2), (a + 1, a + 2, j + 2),
                          (a + 2, a, j + 2)])
        perm = list(range(n))
        rng.shuffle(perm)
        edges = [(perm[a], perm[b], t) for a, b, t in edges]
        rng.shuffle(edges)
        start, end = [0] * n, [0] * n
        start[perm[x]], end[perm[y]] = 1, 1
        inst = Instance(n, edges, start, end)
        detail = {"triangles": k, "connecting_path_edges": len(path) - 1}
    inst.name = f"{family}-m{m}-{index:02d}"
    assert inst.m == m and inst.end is not None
    return inst, detail


class Deadline(Exception):
    pass


def alarm_handler(signum, frame):
    raise Deadline()


def fingerprint():
    paths = sorted((ROOT / "nscover").glob("*.py")) + [
        ROOT / "experiments" / name for name in
        ("aaai_baseline_bench.py", "aaai_gap_study.py", "aaai_reading_study.py",
         "aaai_static_check.py")]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def metadata(args):
    return {"language": "Python", "python": sys.version, "executable": sys.executable,
            "platform": platform.platform(), "machine": platform.machine(),
            "processor": platform.processor(), "nproc": subprocess.check_output(
                ["nproc"], text=True).strip(), "cpu_count": os.cpu_count(),
            "backend_default": DEFAULT_BACKEND, "seed": args.seed,
            "command": sys.argv, "source_sha256": fingerprint()}


def run_cell(family, m, args, command_deadline):
    requested = args.instances or (5 if m >= 800 else 10 if m >= 400 else 20)
    cell = {"family": family, "m": m, "requested": requested, "records": [],
            "cell_limit_seconds": args.cell_seconds, "stopped": "completed"}
    began = time.perf_counter()
    deadline = min(began + args.cell_seconds, command_deadline)
    old = signal.signal(signal.SIGALRM, alarm_handler)
    signal.setitimer(signal.ITIMER_REAL, max(.001, deadline - time.perf_counter()))
    try:
        for i in range(requested):
            inst, detail = make_instance(family, m, i, args.seed)
            # Both methods receive this very same object on every invocation.
            original = inst.to_json()
            methods = [("pairflow", ours), ("baseline", baseline)]
            if i % 2:
                methods.reverse()
            answers, timings = {}, {"pairflow": [], "baseline": []}
            for name, method in methods:
                answers[name] = method(inst)  # one warm-up per method/instance
            for rep in range(3):
                order = methods if rep % 2 == 0 else methods[::-1]
                for name, method in order:
                    t0 = time.perf_counter()
                    answer = method(inst)
                    elapsed = time.perf_counter() - t0
                    assert answer == answers[name], "nondeterministic decision"
                    timings[name].append(elapsed)
            # Size accounting is outside timing, not a second timed S build.
            arcs = static_graph([(e, *edge) for e, edge in enumerate(inst.edges)],
                                inst.start, inst.end, "last")
            oracle = brute_force(inst) if m <= 7 and inst.n <= 5 else None
            truth = answers["pairflow"] if oracle is None else oracle
            source = "solve_pairflow (reference, not independent)" if oracle is None else "brute_force"
            assert original == inst.to_json(), "input mutated"
            if family == "planted-YES":
                assert answers["pairflow"], "planted walk witness rejected"
            cell["records"].append({"instance": original, "generation": detail,
                "static_vertices": len({v for a, b, _ in arcs for v in (a, b)}),
                "static_arcs": len(arcs), "answers": answers, "brute_force": oracle,
                "truth": truth, "truth_source": source, "seconds": timings,
                "best_seconds": {key: min(vals) for key, vals in timings.items()}})
    except Deadline:
        cell["stopped"] = "cell deadline" if deadline < command_deadline else "command deadline"
        cell["partial_instance_discarded"] = True
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)
    cell["wall_seconds"] = time.perf_counter() - began
    return cell


def summarize(cell):
    records = cell["records"]
    result = {key: cell[key] for key in ("family", "m", "requested", "stopped", "wall_seconds")}
    result["completed"] = len(records)
    for name in ("pairflow", "baseline"):
        vals = [r["best_seconds"][name] for r in records]
        result[name] = {"median_seconds": statistics.median(vals) if vals else None,
                        "max_seconds": max(vals) if vals else None}
    a, b = (result[n]["median_seconds"] for n in ("pairflow", "baseline"))
    result["baseline_over_pairflow_medians"] = b / a if a and b is not None else None
    diff = [r for r in records if r["answers"]["pairflow"] != r["answers"]["baseline"]]
    result["disagreements"] = len(diff)
    result["brute_checked"] = sum(r["brute_force"] is not None for r in records)
    result["brute_pairflow_mismatches"] = sum(r["brute_force"] is not None and
        r["brute_force"] != r["answers"]["pairflow"] for r in records)
    result["disagreement_agreement"] = {source: {name: sum(
        r["truth_source"] == source and r["answers"][name] == r["truth"] for r in diff)
        for name in ("pairflow", "baseline")} for source in sorted({r["truth_source"] for r in diff})}
    result["answers_yes"] = {name: sum(r["answers"][name] for r in records)
                             for name in ("pairflow", "baseline")}
    for key in ("static_vertices", "static_arcs"):
        vals = [r[key] for r in records]
        result[key + "_range"] = [min(vals), max(vals)] if vals else []
    return result


def report(out):
    runs = [json.loads(p.read_text()) for p in sorted(out.glob("run-m*.json"))]
    cells = [summarize(c) for run in runs for c in run["cells"]]
    summary = {"cells": cells, "instances": sum(c["completed"] for c in cells),
               "disagreements": sum(c["disagreements"] for c in cells),
               "brute_checked": sum(c["brute_checked"] for c in cells),
               "brute_pairflow_mismatches": sum(c["brute_pairflow_mismatches"] for c in cells)}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    lines = ["| Family | m | N/requested | Pairflow med/max ms | S-test med/max ms | S/P median | Diff | Truth for diff |",
             "|---|---:|---:|---:|---:|---:|---:|---|"]
    for c in cells:
        def timing(name):
            d = c[name]
            return (f"{1000*d['median_seconds']:.3f}/{1000*d['max_seconds']:.3f}"
                    if d["median_seconds"] is not None else "—")
        ratio = c["baseline_over_pairflow_medians"]
        truth = "; ".join(f"{'BF' if s == 'brute_force' else 'P-ref'}: P={v['pairflow']}, S={v['baseline']}"
                          for s, v in c["disagreement_agreement"].items()) or "—"
        lines.append(f"| {c['family']} | {c['m']} | {c['completed']}/{c['requested']} | "
                     f"{timing('pairflow')} | {timing('baseline')} | "
                     f"{f'{ratio:.2f}' if ratio is not None else '—'} | {c['disagreements']} | {truth} |")
    table = "\n".join(lines) + "\n"
    (out / "table.md").write_text(table)
    machines = "\n".join(f"- m={run['m']}: nproc={run['metadata']['nproc']}; "
        f"Python {run['metadata']['python'].splitlines()[0]}; {run['metadata']['platform']}; "
        f"backend={run['metadata']['backend_default']}" for run in runs)
    hashes = {json.dumps(r['metadata']['source_sha256'], sort_keys=True) for r in runs}
    faster = sum(c["baseline_over_pairflow_medians"] is not None and
                 c["baseline_over_pairflow_medians"] < 1 for c in cells)
    readme = f"""# Paired NS-FIX baseline benchmark — 2026-11-01

Measured {summary['instances']} completed instances; {summary['disagreements']} answer disagreements.
Brute force checked {summary['brute_checked']} instances, with {summary['brute_pairflow_mismatches']} pairflow mismatches.
The baseline was faster by median in {faster} cells. No performance claim extends beyond this table.

## Measurement scope

Language: Python (both implementations, same interpreter and process for each pair).
Machine and interpreter per command:
{machines}

Timing uses time.perf_counter. Input generation, JSON parsing/serialization,
imports, oracle calls, S size accounting and reporting are excluded. Instance
construction is excluded. Pairflow timing includes fresh Timeline construction
inside solve_pairflow(inst), the default backend, and the full returned decision;
no walk reconstruction is requested. Baseline timing includes building S exactly
once inside static_feasibility(inst), terminal constraints, balanced-orientation
flow and weak-component terminal coverage. Each method receives the exact same
Instance object. Each has one untimed warm-up per instance, then three measured
calls; the best of three is that instance's time. Method order alternates by
instance and repetition. Table median and max are over these per-instance minima;
S/P is the ratio of the two medians, not the median of paired ratios. No process
isolation, CPU pinning or external load control was used.

Each cell has a 60-second wall cap (including generation, warm-ups, size accounting
and oracle); an interrupted partial instance is discarded. Each command has a
240-second work cap. JSON records completion and truncation; timing conclusions
apply to completed instances only. Source hashes are stored per command;
{'all commands used identical source hashes.' if len(hashes) == 1 else 'SOURCE HASHES DIFFER between commands; inspect per-run metadata before comparing.'}

## Procedure and correctness

This benchmarks the repository implementation of the Deligkas et al. AAAI 2025
Thm 6.3 / Def. 6.3 S-test, using the `last` reading for end terminals. The unchanged
static_graph function is loaded from aaai_reading_study.py via its AST to avoid
that module's unconditional main(). It is bound to aaai_gap_study.static_feasibility,
whose algorithm is unchanged. The baseline answer is balanced AND terminal-covered.
This is a faithful benchmark of the specified procedure, including its known
false YES behavior; it is not presented as a correct NS-FIX solver. NS-FREE is excluded.

For m <= 7 and n <= 5, brute_force is the independent ground truth. Else pairflow
is the reference, so reported baseline errors at larger sizes are relative to
pairflow, not independently certified truth. Per-cell disagreement columns identify
BF (brute force) or P-ref (pairflow reference), and counts agreeing with each.
The JSON retains every input, both answers, all three samples, S vertices/arcs,
generation details, and oracle/reference source. A mismatch with brute force is
reported even if both solvers agree with each other.

## Deterministic families

Seed {runs[0]['metadata']['seed'] if runs else SEED}; independent SHA-256-derived RNG per cell/index.
Planted-YES generates random walks with nondecreasing integer times on a temporal
multigraph; their starts and final positions give the vectors. Saved walk edge IDs
provide a constructive witness. Perturbed uses the same planted parent: three of
four indices move one end unit to another vertex (violating degree parity, hence
NO); every fourth changes one edge to a later time and may remain YES. Actual
answer counts are in summary.json; this is a mostly-NO family, not a promise.
Many-even-components has k=floor((m-1)/4) vertex-disjoint triangles at distinct
times 2..k+1 plus a time-1 connecting path, padded by path subdivisions to exactly
m edges. Its sole token starts/ends at the path endpoints, so each later triangle
is an even component with no token. Replicates permute vertex labels and edge order.
The counterexample is exactly the five-vertex/five-edge instance from
aaai_static_check.py; its 20 replicates are identical, not independent examples.
Extra m=5,7 cells support small independent checks. Requested counts: 20 through
m=200, 10 at 400, 5 at 800 and 1600, subject to the wall cap.

## Results

{table}
## Reproduction

Run each size separately, without parallel benchmark jobs:
`python3 experiments/aaai_baseline_bench.py --sizes M`
for M in 5 7 20 50 100 200 400 800 1600, then
`python3 experiments/aaai_baseline_bench.py --report`.
Each size file is checkpointed after each cell; --report only regenerates summaries.
Machine timings can vary between runs. run-m*.json holds exact commands and hashes.
"""
    (out / "README.md").write_text(readme)
    print(f"Saved {out}: {summary['instances']} instances, {summary['disagreements']} disagreements", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", nargs="+", type=int, choices=SIZES, default=[20],
                        help="run sizes; use one size per command (default: 20)")
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--instances", type=int, help="override count per cell")
    parser.add_argument("--cell-seconds", type=float, default=60,
                        help="cell wall cap, at most 60 seconds")
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--report", action="store_true", help="only aggregate existing run JSON")
    args = parser.parse_args()
    if not 0 < args.cell_seconds <= 60 or (args.instances is not None and args.instances < 1):
        parser.error("cell-seconds must be in (0,60]; instances must be positive")
    args.output.mkdir(parents=True, exist_ok=True)
    if args.report:
        report(args.output)
        return
    command_deadline = time.perf_counter() + 240
    for m in args.sizes:
        run = {"m": m, "metadata": metadata(args), "cells": []}
        families = FAMILIES + (("counterexample",) if m == 5 else ())
        for family in families:
            if time.perf_counter() >= command_deadline:
                break
            cell = run_cell(family, m, args, command_deadline)
            run["cells"].append(cell)
            run["source_sha256_after"] = fingerprint()
            run["source_changed_during_command"] = run["source_sha256_after"] != run["metadata"]["source_sha256"]
            path = args.output / f"run-m{m:04d}.json"
            path.write_text(json.dumps(run, indent=2) + "\n")
            print(f"m={m} {family}: {len(cell['records'])}/{cell['requested']} "
                  f"in {cell['wall_seconds']:.2f}s ({cell['stopped']})", flush=True)
        if time.perf_counter() >= command_deadline:
            break
    report(args.output)


if __name__ == "__main__":
    main()
