# Exact strict temporal-walk solver

The S model treats each walk as one token. It traverses at most one edge per
snapshot, may wait, and may be empty. Every input edge occurrence is used exactly
once. FREE prescribes start counts a; FIX also prescribes end counts z. Parallel
edges have distinct input IDs. Only loop-free integer-count instances are supported.

For an orientation let o_t(v) count departures and deg_t(v) count incident edges.
Feasibility is o_t(v) + 2 sum_(s<t) o_s(v) <= a_v + sum_(s<t) deg_s(v), and,
for FIX, a_v + sum_s deg_s(v) - 2 sum_s o_s(v) = z_v.
The implementation uses binary x_e (one iff the first endpoint is the tail),
and continuous auxiliary b(v,t) variables after each incident snapshot:
o_t(v) <= b_previous and b(v,t) = b_previous + deg_t(v) - 2 o_t(v),
starting at a_v. These equalities force b integral. Bounds 0 <= b <= k are
redundant for feasible token walks. Eliminating b recovers the supplied prefix
formulation, while the sparse matrix has O(m) entries. FIX constrains the last
b to z; isolated vertices and empty instances are handled explicitly.

Optional stage 1 calls the existing non-strict pair-flow solver: its NO implies
strict NO. Stage 2 uses SciPy HiGHS MILP with zero objective and a 60 s optimization
limit. A returned incumbent is rounded and checked using exact integer snapshot
counts before acceptance. A feasible incumbent on timeout is YES; no incumbent
on a limit is UNKNOWN. Only a HiGHS infeasibility status or the sound NS filter
produces NO (plus explicit impossible empty/isolated terminal boundaries).
There is no LP feasibility shortcut. SciPy is imported lazily; dependency files
were not changed. time_limit caps optimization, not matrix construction, imports,
NS filtering or witness checking. Timings separate those costs. Witness time
includes construction AND the mandatory independent check; totals include all
solver stages. First-use import overhead appears in build time.

For YES, departures reserve distinct standing tokens before any arrivals are
committed. Witness JSON contains a start vertex and ordered edge IDs per walk,
including empty walks. check_strict_walks independently follows undirected edges,
checks strict time increase, exact use of all IDs, and start/end counts. It uses
no orientation test, solver, or token simulation. Every solver YES asserts this
checker. Each bench JSON contains the full instance, orientation and walks so
witnesses can be checked separately without SciPy.

## Validation

Seed 20261101: 20000 random tiny instances
(n <= 5, m <= 8), evenly alternating FREE/FIX and cycling general, proper, star,
forest, cycle, maxdeg2 classes, sampled with replacement. General uses unchanged
ilp_seed.rand_inst. Proper/star/forest/maxdeg2 use unchanged classes_seed.gen,
rejecting m > 8; proper maps to matching. Actual simple cycles are explicitly
constructed (the seed maxdeg2 class alone also permits paths), with its maxdeg2
predicate checked. Cycle n is 3..5, one or two snapshots, k is 1..4; other seed
classes use their original distributions. No conditioning on feasibility.
Function AST loading avoids running seed modules' top-level benchmark loops.
2000 stratified initial random instances were also
checked with oracle.identity_brute, which assigns edges to distinct labeled
tokens rather than enumerating orientations. 11
additional boundary cases cover zero tokens, empty graphs, unequal terminal
totals, isolated vertices, parallel edges, negative/unsorted times and simultaneous
arrival reuse. Deliberately invalid witnesses test checker rejection.

Every random case compares BOTH the unfiltered ILP and the default filtered solver
against oracle.decide; every YES witness from both calls is independently checked.
Disagreements: 0. NS-YES/strict-NO:
3767 / 20000. NS-YES/strict-YES:
5780; NS orientations already satisfying strict inequalities:
5078 / 5780 = 87.85%.
This measures potential ILP avoidance; the current solver deliberately still runs
stage 2 for NS-YES to measure and validate the ILP. Rates are generator-specific,
not uniform probabilities over graph classes. Per-class counts and small NS gap
examples are in validation.json.

## Scalability

Each benchmark case runs in its own command. Graphs use scale_seed.planted with
seed 20261101 + configuration index. Ordinary move probability is 0.6; the three
last configurations use 0.9, very few tokens, few vertices and long horizons,
creating several incident edges per vertex per snapshot. Perturbation moves one
random edge to the next time (cyclically); this need not destroy feasibility.
FREE/FIX and planted/perturbed cases share their base graphs. Planted YES is
asserted. Each JSON records full data, including the exact perturbation.

Status counts: {'NO': 14, 'YES': 22, 'UNKNOWN': 4}. Limit-status instances:
4. Maximum observed ILP optimization time:
69.148 s.
Planted-YES assertions that failed because optimization returned UNKNOWN:
4.
These are unsolved known-feasible stress cases, not false NO answers. For these
cases the benchmark files also retain independently checked ground_truth_walks
from the generator, separate from the solver's null witness. Ordinary planted
benchmarks (configuration indices 0..6) must all assert YES. HiGHS' time limit
is best effort: observed optimization time can exceed 60 seconds before control
returns to Python. The outer command timeout is below five minutes.
The planted ground truth is not given to the optimizer as an incumbent, hint,
or objective; the solver still searches with the same zero objective.

| n/k/T | m | Mode/type | Status | NS s | Build s | ILP s | Witness s | Total s |
|---|---:|---|---|---:|---:|---:|---:|---:|
| 20/5/12 | 37 | FIX/perturbed | NO | 0.0057 | 0.2979 | 0.0043 | 0.0000 | 0.3081 |
| 20/5/12 | 37 | FIX/planted | YES | 0.0033 | 0.2467 | 0.0046 | 0.0001 | 0.2547 |
| 20/5/12 | 37 | FREE/perturbed | NO | 0.0084 | 0.2146 | 0.0049 | 0.0000 | 0.2281 |
| 20/5/12 | 37 | FREE/planted | YES | 0.0049 | 0.2983 | 0.0053 | 0.0002 | 0.3089 |
| 50/15/20 | 172 | FIX/perturbed | NO | 0.0074 | 0.2057 | 0.0067 | 0.0000 | 0.2201 |
| 50/15/20 | 172 | FIX/planted | YES | 0.0072 | 0.2346 | 0.0090 | 0.0003 | 0.2514 |
| 50/15/20 | 172 | FREE/perturbed | NO | 0.0100 | 0.3048 | 0.0086 | 0.0000 | 0.3236 |
| 50/15/20 | 172 | FREE/planted | YES | 0.0069 | 0.2687 | 0.0095 | 0.0002 | 0.2855 |
| 100/30/30 | 531 | FIX/perturbed | NO | 0.0212 | 0.3505 | 0.0288 | 0.0000 | 0.4009 |
| 100/30/30 | 531 | FIX/planted | YES | 0.0314 | 0.4903 | 0.0626 | 0.0011 | 0.5864 |
| 100/30/30 | 531 | FREE/perturbed | NO | 0.0788 | 0.6935 | 0.0484 | 0.0000 | 0.8215 |
| 100/30/30 | 531 | FREE/planted | YES | 0.0212 | 0.3337 | 0.0416 | 0.0010 | 0.3979 |
| 200/60/40 | 1466 | FIX/perturbed | YES | 0.0623 | 0.2787 | 0.0986 | 0.0015 | 0.4434 |
| 200/60/40 | 1466 | FIX/planted | YES | 0.0824 | 0.4290 | 0.0482 | 0.0014 | 0.5656 |
| 200/60/40 | 1466 | FREE/perturbed | YES | 0.1030 | 0.5766 | 0.1456 | 0.0023 | 0.8286 |
| 200/60/40 | 1466 | FREE/planted | YES | 0.1007 | 0.3729 | 0.1155 | 0.0017 | 0.5932 |
| 400/120/60 | 4326 | FIX/perturbed | YES | 0.3065 | 0.4414 | 0.4674 | 0.0091 | 1.2278 |
| 400/120/60 | 4326 | FIX/planted | YES | 0.1756 | 0.2743 | 0.3235 | 0.0120 | 0.7876 |
| 400/120/60 | 4326 | FREE/perturbed | YES | 0.2858 | 0.3151 | 0.3859 | 0.0051 | 0.9945 |
| 400/120/60 | 4326 | FREE/planted | YES | 0.2099 | 0.3422 | 0.4410 | 0.0053 | 1.0016 |
| 800/250/80 | 12005 | FIX/perturbed | YES | 1.5470 | 0.6789 | 1.6215 | 0.0327 | 3.9004 |
| 800/250/80 | 12005 | FIX/planted | YES | 1.0905 | 1.0078 | 2.1064 | 0.0257 | 4.2369 |
| 800/250/80 | 12005 | FREE/perturbed | YES | 0.9790 | 0.5690 | 1.3920 | 0.0154 | 2.9640 |
| 800/250/80 | 12005 | FREE/planted | YES | 0.8389 | 0.4081 | 1.6574 | 0.0184 | 2.9333 |
| 1200/500/100 | 29768 | FIX/perturbed | NO | 4.5241 | 0.9379 | 10.3298 | 0.0000 | 15.8120 |
| 1200/500/100 | 29768 | FIX/planted | YES | 4.4619 | 1.0045 | 7.1725 | 0.0734 | 12.7410 |
| 1200/500/100 | 29768 | FREE/perturbed | NO | 5.5881 | 0.9942 | 9.3830 | 0.0000 | 15.9974 |
| 1200/500/100 | 29768 | FREE/planted | YES | 5.1649 | 1.2625 | 16.7335 | 0.0792 | 23.2696 |
| 4/4/500 | 1795 | FIX/perturbed | NO | 0.0572 | 0.2824 | 0.3115 | 0.0000 | 0.6523 |
| 4/4/500 | 1795 | FIX/planted | YES | 0.0384 | 0.2544 | 5.1368 | 0.0033 | 5.4344 |
| 4/4/500 | 1795 | FREE/perturbed | NO | 0.1006 | 0.5170 | 0.5916 | 0.0000 | 1.2127 |
| 4/4/500 | 1795 | FREE/planted | YES | 0.1261 | 0.6723 | 7.4791 | 0.0049 | 8.2848 |
| 6/8/1000 | 7213 | FIX/perturbed | NO | 0.1553 | 0.3051 | 1.7769 | 0.0000 | 2.2417 |
| 6/8/1000 | 7213 | FIX/planted | UNKNOWN | 0.2310 | 0.4296 | 61.0428 | 0.0000 | 61.7070 |
| 6/8/1000 | 7213 | FREE/perturbed | NO | 0.2451 | 0.5040 | 1.4864 | 0.0000 | 2.2418 |
| 6/8/1000 | 7213 | FREE/planted | UNKNOWN | 0.3684 | 0.7095 | 69.1475 | 0.0000 | 70.2348 |
| 6/8/4000 | 28839 | FIX/perturbed | NO | 1.1329 | 0.9548 | 15.9606 | 0.0000 | 18.1506 |
| 6/8/4000 | 28839 | FIX/planted | UNKNOWN | 0.6763 | 0.6821 | 65.3137 | 0.0000 | 66.6867 |
| 6/8/4000 | 28839 | FREE/perturbed | NO | 0.7876 | 0.6239 | 14.8846 | 0.0000 | 16.3136 |
| 6/8/4000 | 28839 | FREE/planted | UNKNOWN | 0.9989 | 0.7068 | 60.6990 | 0.0000 | 62.4399 |

## Scope and reproduction

The finite random study is not exhaustive and does not establish the formulation
for all inputs. Large YES answers have independently checked witnesses; large NO
answers have NOT been checked with an exact oracle or an independently verified
infeasibility certificate. NO depends on the existing NS solver or HiGHS. The
independent checker certifies YES only. No external theorem or complexity result
was checked. Timings describe this environment and these seeds, with one trial
per case, no repeated-run confidence intervals, no real datasets and no memory
profiling. Sparse extended formulation equivalence is explained above and tested
against tiny oracles; it is not a new general complexity proof.

worst-case complexity of strict is open; the ILP carries no polynomial guarantee

Environment: Python 3.14.4, SciPy 1.16.3, NumPy
2.3.5; Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.43. Full metadata: summary.json.
Measured commands set OPENBLAS_NUM_THREADS=1 and OMP_NUM_THREADS=1. Source
SHA256 hashes are recorded in summary.json. Some small benchmark runs overlapped
the tiny validation workload; timings are observations, not isolated CPU trials.

Run reduced validation (does not overwrite these results):
`python3 experiments/strict/solver.py --self-test`.
Full validation: `python3 experiments/strict/solver_study.py --validate 20000 --identity 2000`.
One benchmark: `python3 experiments/strict/solver_study.py --benchmark 0-FREE-planted`.
Configuration indices 0..9, modes FREE/FIX, variants planted/perturbed.
Rebuild report: `python3 experiments/strict/solver_study.py --report`.
Standalone witness check (stdlib and existing nscover imports only):
`python3 experiments/strict/solver_study.py --check results/strict-solver-20261101/bench-0-FREE-planted.json`.
