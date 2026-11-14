# Exact edge cover by temporal walks: code, data and benchmarks

Companion repository for the manuscript on exact edge cover by strict and non-strict temporal walks (Optimization Letters).

## Contents

- `main.tex`, `main.pdf`: manuscript (English). `main-vi.tex`, `main-vi.pdf`: Vietnamese parallel version, for reading only.
- `nscover/`: Python library. Exact solver for non-strict walks (pair flow, branch and bound baseline, certificates).
- `experiments/`: experiment scripts. `experiments/strict/` contains the strict-walk solvers and the NP-hardness reduction check (`hardness_reduction.py`).
- `tests/`: unit tests and agreement tests.
- `cpp/`: C++17 implementation (`apps/`, `src/`, `include/`), examples, and differential tests. Build with CMake (`cpp/CMakeLists.txt`).
- `data/`: instructions for obtaining the raw datasets. The raw data are not included.
- `results/`: small summary files and READMEs for each experiment run. Large raw outputs are not included.

## Requirements

- Python 3.14 (the version used for the experiments).
- SciPy for the maximum-flow backend and the integer-programming check; NumPy.
- CMake and a C++17 compiler for `cpp/`.

## Run the tests

From the repository root:

    PYTHONPATH=. python3 tests/test_unit.py
    PYTHONPATH=. python3 tests/test_endset.py

## Reproduce the reduction check (Section 5)

    python3 experiments/strict/hardness_reduction.py --trials 1941 --seed 20261113

Writes `results/strict-hardness-20261113/summary.json`. The expected counts are 1967 formulas, 578 unsatisfiable, and 221 checked with the integer program.

## Data

See `data/README.md`. The transit data are fetched with `experiments/fetch_transit.sh`. The contact data must be obtained from their providers.

## Build the manuscript

    pdflatex main
    bibtex main
    pdflatex main
    pdflatex main

Both the manuscript and the reduction check need the packages listed in the manuscript source (TikZ, pgfplots).

## Status

Public repository: https://github.com/th1enq/exact-edge-cover-temporal-walks
