# Paired NS-FIX baseline benchmark — 2026-11-01

Measured 437 completed instances; 160 answer disagreements.
Brute force checked 120 instances, with 0 pairflow mismatches.
The baseline was faster by median in 4 cells. No performance claim extends beyond this table.

## Measurement scope

Language: Python (both implementations, same interpreter and process for each pair).
Machine and interpreter per command:
- m=5: nproc=4; Python 3.14.4 (main, Aug 20 2026, 10:41:58) [GCC 15.2.0]; Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.43; backend=augment
- m=7: nproc=4; Python 3.14.4 (main, Aug 20 2026, 10:41:58) [GCC 15.2.0]; Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.43; backend=augment
- m=20: nproc=4; Python 3.14.4 (main, Aug 20 2026, 10:41:58) [GCC 15.2.0]; Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.43; backend=augment
- m=50: nproc=4; Python 3.14.4 (main, Aug 20 2026, 10:41:58) [GCC 15.2.0]; Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.43; backend=augment
- m=100: nproc=4; Python 3.14.4 (main, Aug 20 2026, 10:41:58) [GCC 15.2.0]; Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.43; backend=augment
- m=200: nproc=4; Python 3.14.4 (main, Aug 20 2026, 10:41:58) [GCC 15.2.0]; Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.43; backend=augment
- m=400: nproc=4; Python 3.14.4 (main, Aug 20 2026, 10:41:58) [GCC 15.2.0]; Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.43; backend=augment
- m=800: nproc=4; Python 3.14.4 (main, Aug 20 2026, 10:41:58) [GCC 15.2.0]; Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.43; backend=augment
- m=1600: nproc=4; Python 3.14.4 (main, Aug 20 2026, 10:41:58) [GCC 15.2.0]; Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.43; backend=augment

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
all commands used identical source hashes.

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

Seed 20261101; independent SHA-256-derived RNG per cell/index.
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

| Family | m | N/requested | Pairflow med/max ms | S-test med/max ms | S/P median | Diff | Truth for diff |
|---|---:|---:|---:|---:|---:|---:|---|
| planted-YES | 5 | 20/20 | 0.107/0.181 | 0.150/0.282 | 1.40 | 0 | — |
| perturbed | 5 | 20/20 | 0.046/0.769 | 0.100/0.232 | 2.19 | 0 | — |
| many-even-components | 5 | 20/20 | 0.136/0.230 | 0.119/0.193 | 0.88 | 20 | BF: P=20, S=0 |
| counterexample | 5 | 20/20 | 0.193/0.245 | 0.165/0.240 | 0.85 | 20 | BF: P=20, S=0 |
| planted-YES | 7 | 20/20 | 0.157/1.551 | 0.252/0.431 | 1.61 | 0 | — |
| perturbed | 7 | 20/20 | 0.057/0.994 | 0.134/0.293 | 2.33 | 0 | — |
| many-even-components | 7 | 20/20 | 0.240/0.284 | 0.199/0.233 | 0.83 | 20 | P-ref: P=20, S=0 |
| planted-YES | 20 | 20/20 | 0.283/1.368 | 0.651/0.994 | 2.30 | 0 | — |
| perturbed | 20 | 20/20 | 0.139/1.203 | 0.342/0.750 | 2.47 | 0 | — |
| many-even-components | 20 | 20/20 | 0.408/0.618 | 0.391/0.548 | 0.96 | 20 | P-ref: P=20, S=0 |
| planted-YES | 50 | 20/20 | 1.188/1.930 | 2.655/4.356 | 2.23 | 0 | — |
| perturbed | 50 | 20/20 | 0.181/1.445 | 0.799/4.616 | 4.41 | 0 | — |
| many-even-components | 50 | 20/20 | 0.887/1.125 | 0.957/1.255 | 1.08 | 20 | P-ref: P=20, S=0 |
| planted-YES | 100 | 20/20 | 1.678/2.265 | 10.306/15.677 | 6.14 | 0 | — |
| perturbed | 100 | 20/20 | 0.457/3.013 | 3.382/15.917 | 7.41 | 0 | — |
| many-even-components | 100 | 20/20 | 2.483/3.133 | 2.825/3.833 | 1.14 | 20 | P-ref: P=20, S=0 |
| planted-YES | 200 | 20/20 | 2.755/3.925 | 38.939/69.491 | 14.14 | 0 | — |
| perturbed | 200 | 20/20 | 0.833/2.870 | 11.344/54.178 | 13.62 | 0 | — |
| many-even-components | 200 | 20/20 | 3.902/5.690 | 4.925/6.507 | 1.26 | 20 | P-ref: P=20, S=0 |
| planted-YES | 400 | 10/10 | 5.926/9.350 | 210.798/385.127 | 35.57 | 0 | — |
| perturbed | 400 | 10/10 | 2.250/6.090 | 68.090/309.616 | 30.27 | 0 | — |
| many-even-components | 400 | 10/10 | 16.272/18.825 | 22.267/32.574 | 1.37 | 10 | P-ref: P=10, S=0 |
| planted-YES | 800 | 5/5 | 15.512/21.104 | 1161.178/1403.892 | 74.85 | 0 | — |
| perturbed | 800 | 5/5 | 3.538/13.773 | 229.888/1365.654 | 64.98 | 0 | — |
| many-even-components | 800 | 5/5 | 40.948/42.422 | 74.364/80.367 | 1.82 | 5 | P-ref: P=5, S=0 |
| planted-YES | 1600 | 2/5 | 31.502/37.333 | 5361.164/5958.600 | 170.18 | 0 | — |
| perturbed | 1600 | 5/5 | 7.341/24.965 | 767.719/4325.508 | 104.58 | 0 | — |
| many-even-components | 1600 | 5/5 | 161.037/195.115 | 290.282/321.571 | 1.80 | 5 | P-ref: P=5, S=0 |

## Reproduction

Run each size separately, without parallel benchmark jobs:
`python3 experiments/aaai_baseline_bench.py --sizes M`
for M in 5 7 20 50 100 200 400 800 1600, then
`python3 experiments/aaai_baseline_bench.py --report`.
Each size file is checkpointed after each cell; --report only regenerates summaries.
Machine timings can vary between runs. run-m*.json holds exact commands and hashes.
