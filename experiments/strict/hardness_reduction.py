"""Computer check of the NP-hardness reduction for exact edge cover by STRICT walks.

Source problem: CNF formulas in which every clause has two or three literals on
distinct variables and every literal occurs at most twice (NP-complete; see Section 5
of the manuscript for a reduction from 3-SAT).

Two instances are built from a formula with n variables and m clauses.

FIX (six labels, every start and end vertex is a leaf, every walk is non-empty):
  label 1: one start leaf at every literal vertex, s_j - 1 at clause C_j, 4n at the hub H
  label 2: the edge {x_i, not x_i}
  label 3: the edge {C_j, l} for every literal l of C_j
  labels 4, 5: one edge {l, H} at each label, for every literal vertex l
  label 6: d(l) end leaves at l, one at C_j, 6n - 2m at H
FREE (two labels, start counts 1 at literal vertices and s_j - 1 at C_j, free ends):
  label 1: the edge {x_i, not x_i};  label 2: the edges {C_j, l}.

Claim: the formula is satisfiable  <=>  the FIX instance is feasible
                                    <=>  the FREE instance is feasible.

Three solvers that share no code decide the temporal side:
  * solve_strict (HiGHS on the orientation inequalities); every YES is turned into
    walks and checked against the definition by check_strict_walks;
  * oracle.identity_brute, a labelled-token search that never enumerates orientations
    (used where it is fast enough: the FREE instances);
  * a count-vector depth-first search written for this file (FIX and FREE).

Usage: python experiments/strict/hardness_reduction.py [--trials 1941] [--seed 20261113]
"""
from __future__ import annotations

import argparse
from functools import lru_cache
import itertools
import json
from pathlib import Path
import random
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from nscover.instance import Instance
from experiments.strict import oracle
from experiments.strict.solver import solve_strict

OUT = ROOT / 'results/strict-hardness-20261113'


def satisfiable(n, clauses):
    return any(all(any((lit > 0) == bits[abs(lit) - 1] for lit in clause) for clause in clauses)
               for bits in itertools.product((False, True), repeat=n))


def check_formula(n, clauses):
    occurrences = {}
    for clause in clauses:
        assert 2 <= len(clause) <= 3
        assert len({abs(lit) for lit in clause}) == len(clause)
        for lit in clause:
            assert 1 <= abs(lit) <= n
            occurrences[lit] = occurrences.get(lit, 0) + 1
    assert all(count <= 2 for count in occurrences.values())
    return occurrences


def build_fix(n, clauses):
    occurrences = check_formula(n, clauses)
    m = len(clauses)
    start, end, edges = [], [], []

    def vertex(a=0, z=0):
        start.append(a)
        end.append(z)
        return len(start) - 1

    literal = {}
    for i in range(1, n + 1):
        literal[i], literal[-i] = vertex(), vertex()
    clause_vertex = [vertex() for _ in clauses]
    hub = vertex()

    def feed(v, count):
        for _ in range(count):
            edges.append((vertex(a=1), v, 1))

    def drain(v, count):
        for _ in range(count):
            edges.append((v, vertex(z=1), 6))

    for i in range(1, n + 1):
        edges.append((literal[i], literal[-i], 2))
    for lit, v in literal.items():
        feed(v, 1)
        edges.append((v, hub, 4))
        edges.append((v, hub, 5))
        drain(v, occurrences.get(lit, 0))
    for j, clause in enumerate(clauses):
        feed(clause_vertex[j], len(clause) - 1)
        drain(clause_vertex[j], 1)
        for lit in clause:
            edges.append((clause_vertex[j], literal[lit], 3))
    assert 6 * n - 2 * m >= 0
    feed(hub, 4 * n)
    drain(hub, 6 * n - 2 * m)
    assert sum(start) == sum(end)
    return Instance(len(start), edges, start, end)


def build_free(n, clauses):
    check_formula(n, clauses)
    start = [1] * (2 * n) + [len(clause) - 1 for clause in clauses]

    def lit_vertex(lit):
        return 2 * (abs(lit) - 1) + (lit < 0)

    edges = [(2 * i, 2 * i + 1, 1) for i in range(n)]
    for j, clause in enumerate(clauses):
        edges += [(2 * n + j, lit_vertex(lit), 2) for lit in clause]
    return Instance(len(start), edges, start, None)


def count_dfs(inst):
    """Orientation search snapshot by snapshot, memoised on the count vector."""
    layers = oracle.snapshots(inst)
    target = None if inst.end is None else tuple(inst.end)
    n = inst.n

    @lru_cache(maxsize=None)
    def run(step, counts):
        if step == len(layers):
            return target is None or counts == target
        edges = layers[step]
        out, arrive = [0] * n, [0] * n

        def assign(j):
            if j == len(edges):
                return run(step + 1, tuple(counts[v] - out[v] + arrive[v] for v in range(n)))
            u, v = edges[j]
            for tail, head in ((u, v), (v, u)):
                if out[tail] < counts[tail]:
                    out[tail] += 1
                    arrive[head] += 1
                    found = assign(j + 1)
                    out[tail] -= 1
                    arrive[head] -= 1
                    if found:
                        return True
            return False

        return assign(0)

    return run(0, tuple(inst.start))


def milp(inst):
    answer = solve_strict(inst, use_ns_filter=False, time_limit=30)
    assert answer['status'] in ('YES', 'NO'), answer['reason']
    return answer['status'] == 'YES'  # a YES carries walks checked against the definition


def random_formula(rng, n):
    slots = [lit for i in range(1, n + 1) for lit in (i, i, -i, -i)]
    rng.shuffle(slots)
    clauses = []
    while len(slots) >= 2 and len(clauses) < 2 * n:
        size = rng.choice((2, 2, 2, 3))
        clause = []
        for lit in list(slots):
            if len(clause) == size:
                break
            if all(abs(lit) != abs(other) for other in clause):
                clause.append(lit)
                slots.remove(lit)
        if len(clause) < 2:
            break
        clauses.append(tuple(clause))
        if rng.random() < 0.02:
            break
    return clauses


def exhaustive_formulas(n):
    """Every clause multiset on n variables that respects the occurrence bound."""
    literals = [lit for i in range(1, n + 1) for lit in (i, -i)]
    pool = [c for size in (2, 3) for c in itertools.combinations(literals, size)
            if len({abs(lit) for lit in c}) == size]

    def extend(index, chosen, used):
        yield tuple(chosen)
        for j in range(index, len(pool)):
            clause = pool[j]
            if all(used.get(lit, 0) < 2 for lit in clause):
                for lit in clause:
                    used[lit] = used.get(lit, 0) + 1
                chosen.append(clause)
                yield from extend(j, chosen, used)
                chosen.pop()
                for lit in clause:
                    used[lit] -= 1

    yield from extend(0, [], {})


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--trials', type=int, default=1941)
    parser.add_argument('--seed', type=int, default=20261113)
    args = parser.parse_args()
    began = time.perf_counter()
    rng = random.Random(args.seed)
    stats = dict(seed=args.seed, formulas=0, satisfiable=0, unsatisfiable=0,
                 exhaustive_n2=0, random=0, fix_milp=0, fix_dfs=0, free_milp=0,
                 free_dfs=0, free_token_search=0, mismatches=0,
                 largest_fix_edges=0, largest_fix_walks=0)

    def check(n, clauses, use_milp):
        truth = satisfiable(n, clauses)
        fix, free = build_fix(n, clauses), build_free(n, clauses)
        answers = {'fix_dfs': count_dfs(fix), 'free_dfs': count_dfs(free),
                   'free_token_search': oracle.identity_brute(free)}
        if use_milp:
            answers['fix_milp'] = milp(fix)
            answers['free_milp'] = milp(free)
        for name, value in answers.items():
            stats[name] += 1
            if value != truth:
                stats['mismatches'] += 1
                print('MISMATCH', name, n, clauses, truth, value)
        stats['formulas'] += 1
        stats['satisfiable' if truth else 'unsatisfiable'] += 1
        stats['largest_fix_edges'] = max(stats['largest_fix_edges'], fix.m)
        stats['largest_fix_walks'] = max(stats['largest_fix_walks'], fix.k)

    for clauses in exhaustive_formulas(2):
        check(2, clauses, use_milp=True)
        stats['exhaustive_n2'] += 1
    done = 0
    while done < args.trials:
        n = rng.randint(3, 6)
        clauses = random_formula(rng, n)
        if not clauses:
            continue
        check(n, clauses, use_milp=done % 10 == 0)
        stats['random'] += 1
        done += 1
    stats['seconds'] = round(time.perf_counter() - began, 1)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'summary.json').write_text(json.dumps(stats, indent=2) + '\n')
    print(json.dumps(stats, indent=2))
    return 1 if stats['mismatches'] else 0


if __name__ == '__main__':
    sys.exit(main())
