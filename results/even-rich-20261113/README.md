# Even-rich synthetic benchmark (seed 20261113)

Instances in which every component of every snapshot is even, so that condition (ii)
of the characterization carries the whole difficulty. Generator and solver calls:
`experiments/even_rich_bench.py`; summary used in the paper:
`python3 experiments/summarize_even_rich.py results/even-rich-20261113`.

## Generator

Walks move in pairs. At every time each pair is skipped with probability 0.3, and an
active pair crosses a double edge (0.25), lets one walk traverse a cycle of length 3-6
through its vertex (0.30), or moves along two internally disjoint paths of length 1-3
(0.45). Families: `sparse` (about m/3 vertices) and `dense` (about 2 sqrt(m) vertices),
both with about sqrt(m)/2 pairs. Each graph gives four instances: FIX-yes and FREE-yes
(planted vectors, feasible by construction) and FIX-cut and FREE-cut (one pair removed).

## Runs

| File | Graphs per family | Checks |
|---|---|---|
| m12.jsonl | 200 | oracle (m <= 14), BB, static rule |
| m50.jsonl | 100 | BB, static rule |
| m200.jsonl | 50 | BB, static rule |
| m1000.jsonl | 20 | BB (5 s), static rule |
| m5000.jsonl | 10 | PF only |
| m20000.jsonl | 2 | PF only |

`run.sh`, `run2.sh` and `run3.sh` are the driver scripts. They were chained because
the projected time for m = 50,000 exceeded 30 minutes per run, so that size was
dropped and m = 20,000 was reduced to two graphs per family. The first m = 20,000 run
was interrupted after 9 of 16 rows and was rerun completely with the same arguments.
The 9 overlapping rows were identical; `m20000.log` contains both logs.

Machine: Intel Core i9-9980HK, Linux 6.12, Python 3.13.12, default maximum flow
backend of the library (SciPy not installed). Runs were executed one at a time.
