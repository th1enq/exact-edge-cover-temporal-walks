# Pair-flow reorientation benchmark — 2026-11-15

Scratch remains the default. Incremental starts from the current orientation and reverses directed BFS paths. No dependencies were added.

## Machine and method

- Python: `3.13.12 (main, Feb  3 2026, 17:53:27) [GCC 14.3.0]`.
- Platform: `Linux-6.12.93-x86_64-with-glibc2.40`; architecture `x86_64`.
- CPU: Intel(R) Core(TM) i9-9980HK CPU @ 2.40GHz (reported by /proc/cpuinfo).
- Backend: existing default `augment` (SciPy residual completion when available).
- Single process; benchmark commands ran sequentially. Timings are wall seconds for `solve_pairflow`, including Timeline construction and chain initialization; generation and witness checking are excluded.
- Even-rich uses the original generator and seed 20261113, with FIX-yes, FREE-yes, FIX-cut, FREE-cut for each graph. Edge counts can slightly exceed requested m because the generator finishes a gadget.
- A 240-second signal deadline bounds each invocation, including generation and checking. `--count 1000000` is an upper bound; sparse and dense graphs are interleaved until the budget ends. JSONL metadata records the exact invocation; truncation records identify an interrupted final instance.
- Each completed YES result was converted to walks and independently checked. Scratch/incremental answers are asserted equal for completed pairs. Single-run timing differences are not statistical confidence estimates.

## Exact benchmark commands

```sh
PYTHONPATH=. python3 experiments/reorient_bench.py --family even-rich --m 1000 --count 1000000 --seconds 240 --output results/reorient-20261115/even-rich-m1000.jsonl
PYTHONPATH=. python3 experiments/reorient_bench.py --family even-rich --m 200 --count 1000000 --seconds 240 --output results/reorient-20261115/even-rich-m200.jsonl
PYTHONPATH=. python3 experiments/reorient_bench.py --family even-rich --m 5000 --count 1000000 --seconds 240 --output results/reorient-20261115/even-rich-m5000.jsonl
PYTHONPATH=. python3 experiments/reorient_bench.py --family shortage --e 2000 --variants incremental --seconds 240 --output results/reorient-20261115/shortage-2000-incremental.jsonl
PYTHONPATH=. python3 experiments/reorient_bench.py --family shortage --e 50 100 200 500 1000 --seconds 240 --output results/reorient-20261115/shortage.jsonl
```

## Shortage family

| e | m | Answer | Augmentations (each) | Scratch s | Incremental s | Scratch / incremental |
|---:|---:|:---:|---:|---:|---:|---:|
| 50 | 350 | NO | 12 | 0.095188 | 0.074652 | 1.275x |
| 100 | 700 | NO | 24 | 0.290916 | 0.259113 | 1.123x |
| 200 | 1400 | NO | 49 | 1.171705 | 1.023953 | 1.144x |
| 500 | 3500 | NO | 124 | 6.312876 | 4.725912 | 1.336x |
| 1000 | 7000 | NO | 249 | 25.487447 | 19.529895 | 1.305x |
| 2000 | 14000 | NO | 499 | — | 70.028033 | — |

## Even-rich paired results

Only instances with both completed rows enter these timing totals and means. Different valid orientations can change later augmentation counts.

| Family | Requested m | Paired solves per mode | YES / NO | Scratch total s | Incremental total s | Scratch mean s | Incremental mean s | Scratch / incremental |
|:---|---:|---:|:---:|---:|---:|---:|---:|---:|
| dense | 200 | 5068 | 4675 / 393 | 38.079164 | 32.621717 | 0.007514 | 0.006437 | 1.167x |
| dense | 1000 | 320 | 308 / 12 | 35.386643 | 32.059564 | 0.110583 | 0.100186 | 1.104x |
| dense | 5000 | 12 | 12 / 0 | 24.644390 | 22.470648 | 2.053699 | 1.872554 | 1.097x |
| sparse | 200 | 5070 | 3651 / 1419 | 69.521505 | 59.625877 | 0.013712 | 0.011761 | 1.166x |
| sparse | 1000 | 324 | 170 / 154 | 83.601740 | 79.603300 | 0.258030 | 0.245689 | 1.050x |
| sparse | 5000 | 14 | 8 / 6 | 90.376178 | 87.930780 | 6.455441 | 6.280770 | 1.028x |

Completed solver rows: 21629. Matched answer pairs: 10813. Unpaired completed rows: 3.

## Budgets and limitations

- even-rich-m1000.jsonl: budget ended after 1288 rows at 240.007 s; final instance may be unpaired.
- even-rich-m200.jsonl: budget ended after 20277 rows at 240.007 s; final instance may be unpaired.
- even-rich-m5000.jsonl: budget ended after 53 rows at 240.006 s; final instance may be unpaired.

The e=2000 shortage case was run only with incremental. NO answers on large benchmark graphs have no independent exhaustive oracle; agreement is checked between modes. Random small-instance comparisons and witness checks are executable evidence, not a proof for all inputs.

## Validation

```sh
PYTHONPATH=. python3 tests/test_reorient.py
PYTHONPATH=. python3 tests/test_unit.py
PYTHONPATH=. python3 tests/test_endset.py
```

All passed: 5 reorientation tests (2000 random bases, each FIX and FREE, 4000 answer comparisons, all YES witnesses checked), 10 existing unit tests, and 7 existing end-set tests. Targeted checks cover parallel edges, multi-edge path reversals, no-op targets, unreachable and invalid targets, mode validation, and shared box/even assertions.

Repository workflow friction: AGENTS.md references docs/WORKFLOW.md, which is absent in this checkout. Guidance was not changed.
