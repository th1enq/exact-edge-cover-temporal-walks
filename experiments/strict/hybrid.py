"""NS filter, count-vector DP for small state spaces, otherwise strict ILP."""
from __future__ import annotations

import argparse
import json
from math import comb
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from experiments.strict.dp import solve_strict_dp
from experiments.strict.solver import solve_strict, check_strict_walks
# solver.py imports this same NS filter inside solve_strict, not at module scope.
from nscover.pairflow import solve_pairflow


def solve_strict_hybrid(inst, time_limit=60, max_states=200000):
    """Reserve half the post-filter budget for a possible alternate solver.

    NS, ILP construction and witness checks are not preemptible. Remaining wall
    time is passed to optimization; no search is started after it is exhausted.
    method names the answering solver; attempts records UNKNOWN fallback too.
    """
    if inst.end_set is not None:
        raise ValueError('Only strict S-FREE and S-FIX are supported')
    if time_limit <= 0 or max_states < 1:
        raise ValueError('time_limit and max_states must be positive')
    began = time.perf_counter()
    ns = solve_pairflow(inst)
    ns_seconds = time.perf_counter() - began
    bound = comb(inst.k + inst.n - 1, inst.n - 1) if inst.n else 1
    first = 'dp' if bound <= max_states else 'ilp'
    attempts = []

    def finish(answer, method):
        answer = dict(answer)
        answer.update(method=method, selected=first, attempts=attempts,
                      count_vectors=bound, ns_status=ns.status,
                      ns_seconds=ns_seconds, seconds=time.perf_counter() - began)
        if answer['status'] == 'YES' and not check_strict_walks(inst, answer['walks']):
            raise AssertionError('invalid hybrid witness')
        return answer

    if ns.status == 'NO':
        return finish(dict(status='NO', orientation=None, walks=None, reason='ns-filter'), 'ns-filter')
    answer = dict(status='UNKNOWN', orientation=None, walks=None, reason='time-limit')
    for j, method in enumerate((first, 'ilp' if first == 'dp' else 'dp')):
        remaining = time_limit - (time.perf_counter() - began)
        if remaining <= 0:
            break
        budget = remaining / 2 if j == 0 else remaining
        answer = (solve_strict_dp(inst, max_states, budget) if method == 'dp'
                  else solve_strict(inst, use_ns_filter=False, time_limit=budget))
        attempts.append(dict(method=method, status=answer['status'], seconds=answer['seconds'],
                             reason=answer['reason'], budget=budget,
                             states_max=answer.get('states_max')))
        if answer['status'] != 'UNKNOWN':
            return finish(answer, method)
    return finish(answer, attempts[-1]['method'] if attempts else 'budget')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--instance', type=Path)
    parser.add_argument('--time-limit', type=float, default=60)
    args = parser.parse_args()
    if args.self_test:
        from experiments.strict.dp_study import validate, boundaries
        boundaries()
        data = validate(600, 100, hybrid=True)
        print(json.dumps(data, indent=2))
        print('0 disagreements')
    elif args.instance:
        from nscover import Instance
        print(json.dumps(solve_strict_hybrid(Instance.load(args.instance), args.time_limit), indent=2))
    else:
        parser.error('choose --self-test or --instance')


if __name__ == '__main__':
    main()
