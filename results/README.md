# Results

Each directory holds one experiment run: the command or script used, summary files and, where small enough, raw JSONL outputs. Every command ran with a 300-second limit unless the directory README states otherwise. Machines and Python versions are recorded in the directory READMEs and in Section 6 of the manuscript.

| Directory | Content | Manuscript |
|---|---|---|
| `mconvex-20261101/`, `certify-no-20261101/`, `ext-20261101/`, `cpp17-20261026/`, `baseline-bench-20261101/` | Exhaustive-oracle agreement, M-convexity checks, certificates, Python--C++ agreement | Section 6, validation (Table 1) |
| `even-rich-20261113/` | Even-rich benchmark (`experiments/even_rich_bench.py`) | Section 6, Table 2 |
| `scaling-20261118/` | Shortage family, scratch and incremental re-orientation, two repetitions | Section 6, scaling |
| `reorient-20261115/` | Paired scratch/incremental comparison (`experiments/reorient_bench.py`) | Section 6, scaling |
| `ilp-baseline-20261115/` | Integer programming baseline (`experiments/ilp_baseline.py`) | Section 6, ILP baseline |
| `census-20261025/`, `transit-full-20261025/`, `transit-more-20261025/`, `mink-20261030/` | Contact and transit data | Section 6, real data |
| `aaai-gap-20261030/`, `aaai-reading-20261101/` | Five-vertex instance and the reconstructed static rule | Section 3 |
| `strict-hardness-20261113/`, `strict-20261101/`, `strict-dp-20261101/`, `strict-solver-20261101/`, `strict-real-20261101/` | Reduction check and strict-walk solvers | Section 5 |
