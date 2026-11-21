# Independent ILP baseline — 2026-11-15

## Material Passport

Artifact: experiment result; mode: run; status: completed and locally verified.
Inputs: user-specified FIX/FREE characterization and repository generators.
Evidence: JSONL instances, statuses, timings, checked witnesses, and the audit below.

## Outcome and agreement

The initial **3,000 random cases** have **zero disagreements** between ILP, PF,
and the operational `nscover.brute.brute_force` oracle. There are 1,500 FIX and
1,500 FREE cases; 1,500 use `random_instance` and 1,500 use `cycle_instance`.
All have at most 10 edges; 484 contain at least one even component.
Answers: 1,853 YES and 1,147 NO. Every ILP/PF YES was built into walks and checked.
Six seeds are 20261115 through 20261120, with 500 cases each. FIX and FREE are
balanced within each generator. Cycle samples exceeding 10 edges are rejected
so every random case receives a full operational oracle check.

A second pass reran the **same 3,000 cases against the current library** with
zero disagreements; these are repeated checks, not 3,000 additional distinct
random draws. Twelve named boundary cases also agree with PF and brute force.
They include empty graphs, isolated vertices, total mismatch, no-token cycles,
parallel edges, same-time traversals, and unsorted/negative labels. ENDSET is
explicitly rejected; a nonpositive time budget returns LIMIT.

All **82 benchmark cases** were attempted with ILP, PF, and BB: 10 shortage
sizes and 72 even-rich cases. ILP and PF resolved all 82 and agree throughout.
BB resolved 74 and agrees on all 74; its other eight results are LIMIT.
Every benchmark YES from all three solvers passed walk construction/checking.

## Encoding

`solve_ilp(inst, time_limit)` returns the library `Result` shape: status
YES/NO/LIMIT and, on YES, the tail vertex for every edge in input order.
It independently constructs snapshot components and affine counters; it does
not call Timeline, chain constraints, PF, or BB to build or decide the model.
The module imports those APIs only for agreement/benchmark orchestration and
uses the required library walk builder/checker to validate each ILP YES.

Binary x_e=1 puts the tail at the first listed endpoint. An earlier incident
edge contributes 1-2*x_e at its first endpoint and 2*x_e-1 at its second.
For every vertex appearance the counter after the entire timestamp is >=0.
For every edge-containing snapshot component the sum of counters before that
timestamp is >=1. FIX additionally equates every final counter to `inst.end`,
including isolated vertices. FREE needs no final constraints: total walks are
conserved by each edge. The objective is identically zero. Empty edge sets
are decided directly. These conventions match chainflow.py and walks.py.
Rounded binary incumbents are checked against the integer constraints before
being converted to independently checked walks. Infeasible HiGHS status yields
NO; a limit without a valid incumbent yields LIMIT; unexpected failures raise.

## Timing protocol and limitations

Each solver gets a fresh forked process and a **60-second wall limit**, including
model/Timeline construction, solving, and one walk validation for YES. Imports
and process startup are excluded from reported solver seconds; startup is
included in the hard wall budget. ILP also receives HiGHS time_limit=60.
The parent terminates a child on the hard deadline. BB uses its 60-second
cooperative limit with max_flows=10**18, so its flow cap is not the restriction.
Raw elapsed times can exceed 60 slightly from scheduling/deadline handling.

Solvers run sequentially within this experiment. PF/BB use default `augment`
with SciPy available. OPENBLAS_NUM_THREADS=1 and OMP_NUM_THREADS=1. There is one
measurement per solver/case, without warm-up or timing repetitions. Tiny times
are noisy. No brute-force claim is made for the large benchmark cases.

**Concurrent-work caveat:** another actor changed `nscover/pairflow.py` during
this run to add optional incremental reorientation, retaining the default
`scratch` path used here. Another actor also created commit `1389c8d59e400a99635e972717f27116681bfcda`,
which captured some in-progress ILP artifacts; this agent did not commit,
change library/tests/manuscripts, or create a branch. The change adds an
optional branch and leaves default orientation reconstruction intact. Initial
rows cannot be individually attributed to before/after that change because
source hashes were not captured at each launch. The current-library agreement
rerun verifies correctness after the change. Other concurrent experiment work
was present in the workspace, so **these are shared-machine observations,
not isolated performance estimates**. Timing ratios should not be generalized.
`source-sha256.txt` captures final source bytes for future reproduction.

## Shortage family

FREE instances use `family(e)` with r=e-1, hence all ten are NO. No size was
skipped after a BB LIMIT. All times below are seconds.

| e | m | ILP s | PF s | BB s / status |
|---:|---:|---:|---:|---:|
| 2 | 14 | 0.0084 | 0.0013 | 0.0058 |
| 4 | 28 | 0.0046 | 0.0007 | 0.0101 |
| 8 | 56 | 0.0075 | 0.0023 | 0.3498 |
| 12 | 84 | 0.0109 | 0.0052 | 7.8441 |
| 16 | 112 | 0.0124 | 0.0080 | LIMIT (60 s) |
| 20 | 140 | 0.0147 | 0.0116 | LIMIT (60 s) |
| 30 | 210 | 0.0210 | 0.0250 | LIMIT (60 s) |
| 50 | 350 | 0.0268 | 0.0471 | LIMIT (60 s) |
| 100 | 700 | 0.0754 | 0.1655 | LIMIT (60 s) |
| 200 | 1400 | 0.2606 | 0.6681 | LIMIT (60 s) |

## Even-rich family

Seed **20261113**, sparse/dense, target m=50,200,1000, graph indices 0,1,2.
Each graph has FIX-yes, FREE-yes, FIX-cut, FREE-cut variants (12 rows per group).
The existing generator can overshoot the target edge count; each JSONL records
both target_m and actual m, the full instance, and its SHA-256. Cut does not
imply infeasible. Every generated snapshot component is even (audited).

The table pools the four variants and three graph indices per group. It reports
median / maximum seconds. BB LIMITs enter this descriptive table as 60 seconds;
the raw JSONL retains actual elapsed times and flags hard deadline terminations.
All ILP and PF limit counts are zero.

| Family | Target m | Cases | ILP median / max s | PF median / max s | BB median / max s | BB limits |
|---|---:|---:|---:|---:|---:|---:|
| sparse | 50 | 12 | 0.0116 / 0.0146 | 0.0023 / 0.0072 | 0.0037 / 0.0102 | 0 |
| sparse | 200 | 12 | 0.0213 / 0.0251 | 0.0196 / 0.0272 | 0.0475 / 27.7710 | 0 |
| sparse | 1000 | 12 | 0.1105 / 1.4752 | 0.2523 / 0.3438 | 0.6097 / 60.0000 | 2 |
| dense | 50 | 12 | 0.0116 / 0.0161 | 0.0041 / 0.0059 | 0.0045 / 0.0062 | 0 |
| dense | 200 | 12 | 0.0283 / 0.0329 | 0.0137 / 0.0196 | 0.0173 / 0.0263 | 0 |
| dense | 1000 | 12 | 0.3732 / 3.0998 | 0.1544 / 0.2277 | 0.2195 / 0.3833 | 0 |

## Environment and exact commands

Python: `3.13.12 (main, Feb  3 2026, 17:53:27) [GCC 14.3.0]`. SciPy: **1.16.3**; NumPy:
**2.3.4**; bundled HiGHS: **1.8.0**.
Platform: `Linux-6.12.93-x86_64-with-glibc2.40`.

The requested environment command was attempted:

```sh
nix shell nixpkgs#python3Packages.scipy nixpkgs#python3Packages.numpy -c python3 ...
```

It failed because the sandbox denied connection to the local Nix daemon socket.
No dependency was installed. `run.sh` instead uses the default `python3` plus
already-cached Nix SciPy/NumPy site-packages through PYTHONPATH; its exact store
paths are recorded in that script. Every JSONL metadata row records argv and
Python/SciPy/NumPy versions. `commands.sh` lists **every exact successful run
command**, including the current-library reruns, each as a separate command.
Each benchmark command runs one instance (at most 180 solver seconds), and each
agreement command runs 500 small cases. `run.sh` enforces 240 seconds per command,
below five minutes. Outputs are opened exclusively to prevent silent overwrites.
Run from the repository root using fresh output filenames/a fresh result target.

To re-audit and regenerate this README, boundary results, summary, command list,
and final source hashes, run from the repository root:

```sh
PYTHONPATH=/nix/store/2zn0v1k3nnc25snk47mf5vjimwdva4sm-python3.13-scipy-1.16.3/lib/python3.13/site-packages:/nix/store/bvcpg8ny128rrnkzhw5wmkakp06hpm62-python3.13-numpy-2.3.4/lib/python3.13/site-packages OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 timeout 240 python3 results/ilp-baseline-20261115/verify.py
```

The audit checks exact grid coverage, all statuses, absence of disagreement,
instance hashes, planted feasibility, even-component coverage, witness flags,
and the correspondence of the initial/current random instances. Source authority
was the supplied task plus instance.py, chainflow.py, and walks.py;
`docs/WORKFLOW.md` was absent. No external service was contacted.

A separate regression check, `python3 -m unittest discover -s tests -p test_unit.py`,
passed all 10 existing unit tests. No test files were changed by this task.
