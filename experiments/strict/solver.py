"""Exact S-FREE/S-FIX solver; SciPy/HiGHS is needed only when ILP is used.

Orientation is a list of tail vertices in input edge order. A witness is a list
of {'start': vertex, 'edges': [input edge IDs in traversal order]}; edge IDs
identify parallel occurrences unambiguously. Waiting is implicit.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def check_strict_walks(inst, walks):
    """Independent definition-only checker; return bool, including malformed input.

    No orientation, token simulation, inequalities, NS solver, or SciPy is used.
    """
    try:
        if inst.end_set is not None:
            return False
        starts, ends, seen = [0] * inst.n, [0] * inst.n, set()
        for walk in walks:
            v = walk['start']
            if type(v) is not int or not 0 <= v < inst.n:
                return False
            starts[v] += 1
            previous_time = None
            for e in walk['edges']:
                if type(e) is not int or not 0 <= e < inst.m or e in seen:
                    return False
                u, w, stamp = inst.edges[e]
                if previous_time is not None and stamp <= previous_time:
                    return False
                if v == u:
                    v = w
                elif v == w:
                    v = u
                else:
                    return False
                previous_time = stamp
                seen.add(e)
            ends[v] += 1
        return (starts == list(inst.start) and len(seen) == inst.m
                and (inst.end is None or ends == list(inst.end)))
    except (TypeError, KeyError, IndexError, ValueError):
        return False


def strict_orientation_ok(inst, tails):
    """Exact integer evaluation of departures <= pre-snapshot population."""
    if tails is None or len(tails) != inst.m:
        return False
    groups = defaultdict(list)
    for e, (u, v, t) in enumerate(inst.edges):
        if tails[e] not in (u, v):
            return False
        groups[t].append(e)
    counts = list(inst.start)
    for t in sorted(groups):
        out, delta = defaultdict(int), defaultdict(int)
        for e in groups[t]:
            u, v, _ = inst.edges[e]
            tail = tails[e]
            head = v if tail == u else u
            out[tail] += 1
            delta[tail] -= 1
            delta[head] += 1
        if any(c > counts[v] for v, c in out.items()):
            return False
        for v, d in delta.items():
            counts[v] += d
    return inst.end is None or counts == list(inst.end)


def build_strict_walks(inst, tails):
    """Reserve all departures before committing any snapshot arrivals."""
    standing = [[] for _ in range(inst.n)]
    walks = []
    for v, count in enumerate(inst.start):
        for _ in range(count):
            standing[v].append(len(walks))
            walks.append(dict(start=v, edges=[]))
    groups = defaultdict(list)
    for e, (_, _, t) in enumerate(inst.edges):
        groups[t].append(e)
    for t in sorted(groups):
        arrivals = []
        for e in groups[t]:
            u, v, _ = inst.edges[e]
            tail = tails[e]
            token = standing[tail].pop()
            walks[token]['edges'].append(e)
            arrivals.append((v if tail == u else u, token))
        for v, token in arrivals:
            standing[v].append(token)
    return walks


def _milp(inst, time_limit):
    try:
        import numpy as np
        from scipy.optimize import milp, LinearConstraint, Bounds
        from scipy.sparse import coo_matrix
    except ImportError as exc:
        raise RuntimeError('Strict ILP requires SciPy with scipy.optimize.milp '
                           '(SciPy >= 1.9); install it in your environment. '
                           'No repository dependencies are changed.') from exc
    # b(v,t) = token count AFTER the vertex's incident snapshot t.
    # o(v,t) <= b(v,previous), b(v,t) = b(v,previous)+deg(v,t)-2o(v,t).
    # Eliminating b gives exactly the prefix inequalities in the seed model.
    incident = [defaultdict(list) for _ in range(inst.n)]
    for e, (u, v, t) in enumerate(inst.edges):
        incident[u][t].append((e, 1, 0))
        incident[v][t].append((e, -1, 1))
    rows, cols, values, lower, upper = [], [], [], [], []
    variables = inst.m
    final_vars = {}

    def row(terms, lo, hi):
        r = len(lower)
        for c, value in terms:
            rows.append(r); cols.append(c); values.append(value)
        lower.append(lo); upper.append(hi)

    for v, layers in enumerate(incident):
        previous = None
        for t in sorted(layers):
            items = layers[t]
            current = variables
            variables += 1
            constant = sum(c for _, _, c in items)
            prev_terms = [] if previous is None else [(previous, -1)]
            initial = inst.start[v] if previous is None else 0
            row([(e, co) for e, co, _ in items] + prev_terms,
                -np.inf, initial - constant)
            rhs = initial + len(items) - 2 * constant
            row([(current, 1)] + prev_terms + [(e, 2 * co) for e, co, _ in items], rhs, rhs)
            previous = current
        if previous is not None:
            final_vars[v] = previous
    if inst.end is not None:
        for v, var in final_vars.items():
            row([(var, 1)], inst.end[v], inst.end[v])
    matrix = coo_matrix((values, (rows, cols)), shape=(len(lower), variables)).tocsc()
    integrality = np.zeros(variables)
    integrality[:inst.m] = 1  # balance variables are forced integral by equalities
    hi = np.full(variables, inst.k, dtype=float)
    hi[:inst.m] = 1
    start = time.perf_counter()
    res = milp(np.zeros(variables), integrality=integrality,
               bounds=Bounds(np.zeros(variables), hi),
               constraints=LinearConstraint(matrix, lower, upper),
               options={'time_limit': float(time_limit)})
    solve_seconds = time.perf_counter() - start
    tails = None
    if res.x is not None:
        tails = [u if res.x[e] >= 0.5 else v for e, (u, v, _) in enumerate(inst.edges)]
        if not strict_orientation_ok(inst, tails):
            tails = None
    return res, tails, solve_seconds, dict(variables=variables, rows=len(lower), nonzeros=len(values))


def solve_strict(inst, use_ns_filter=True, time_limit=60):
    """Return status, orientation, walks, reason, seconds, and stage timings.

    time_limit caps HiGHS optimization (not Python construction or the optional
    NS filter). A feasible incumbent on timeout is a certified YES. Infeasibility
    uses HiGHS' status; NO has no independently checkable certificate here.
    """
    if inst.end_set is not None:
        raise ValueError('Only strict S-FREE and S-FIX are supported')
    if time_limit <= 0:
        raise ValueError('time_limit must be positive')
    began = time.perf_counter()
    timing = dict(ns_filter=0.0, ilp=0.0, ilp_build=0.0, witness=0.0)
    extra = {}

    def result(status, reason, tails=None):
        walks = None
        if status == 'YES':
            t = time.perf_counter()
            walks = build_strict_walks(inst, tails)
            assert check_strict_walks(inst, walks), 'invalid strict witness'
            timing['witness'] = time.perf_counter() - t
        return dict(status=status, orientation=tails, walks=walks, reason=reason,
                    seconds=time.perf_counter() - began, timings=timing, **extra)

    if use_ns_filter:
        from nscover.pairflow import solve_pairflow
        t = time.perf_counter()
        ns = solve_pairflow(inst)
        timing['ns_filter'] = time.perf_counter() - t
        extra['ns_status'] = ns.status
        extra['ns_orientation_strict'] = ns.status == 'YES' and strict_orientation_ok(inst, ns.tails)
        if ns.status == 'NO':
            return result('NO', 'ns-filter')
    # Explicit boundaries also handle zero-column MILPs and isolated vertices.
    active = {v for u, w, _ in inst.edges for v in (u, w)}
    if inst.end is not None and (sum(inst.end) != inst.k or any(
            inst.start[v] != inst.end[v] for v in range(inst.n) if v not in active)):
        return result('NO', 'ilp-infeasible')
    if not inst.m:
        return result('YES', 'empty', [])
    t = time.perf_counter()
    res, tails, solve_seconds, size = _milp(inst, time_limit)
    timing['ilp'] = solve_seconds
    timing['ilp_build'] = time.perf_counter() - t - solve_seconds
    extra.update(ilp_status=int(res.status), ilp_message=str(res.message), matrix=size)
    if tails is not None:
        return result('YES', 'ilp-feasible', tails)
    if res.status == 2:
        return result('NO', 'ilp-infeasible')
    return result('UNKNOWN', 'ilp-limit' if res.status == 1 else 'ilp-error')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--instance', type=Path)
    parser.add_argument('--no-ns-filter', action='store_true')
    parser.add_argument('--time-limit', type=float, default=60)
    args = parser.parse_args()
    if args.self_test:
        from experiments.strict.solver_study import validate
        data = validate(600, 200, 20261101)
        print(json.dumps({key: value for key, value in data.items()
                          if key not in ('rows', 'examples')}, indent=2))
        print('0 disagreements')
    elif args.instance:
        from nscover import Instance
        print(json.dumps(solve_strict(Instance.load(args.instance),
                                     not args.no_ns_filter, args.time_limit), indent=2))
    else:
        parser.error('choose --self-test or --instance')


if __name__ == '__main__':
    main()
