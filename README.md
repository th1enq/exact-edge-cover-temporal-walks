# Exact edge cover by temporal walks: code, data and benchmarks

Companion repository for the manuscript on exact edge cover by strict and non-strict temporal walks (Optimization Letters).

## Contents

- `submission/`: manuscript as submitted (English): `main.tex`, `main.pdf`, `references.bib`, the Springer Nature template, `sections/`, and `figures/` (`FigN.pdf` with TikZ source `FigN.tex`).
- `vi/`: Vietnamese parallel version (`main-vi.tex`, `main-vi.pdf`), for reading only.
- `nscover/`: Python library. Exact solver for non-strict walks (pair flow with scratch or path-reversing re-orientation, branch and bound baseline, certificates).
- `experiments/`: experiment scripts, including `even_rich_bench.py` (even-rich benchmark), `reorient_bench.py` (scaling and re-orientation comparison) and `ilp_baseline.py` (integer programming baseline). `experiments/strict/` contains the strict-walk solvers and the NP-hardness reduction check (`hardness_reduction.py`).
- `tests/`: unit tests and agreement tests.
- `cpp/`: C++17 implementation (`apps/`, `src/`, `include/`), examples, and differential tests. Build with CMake (`cpp/CMakeLists.txt`).
- `data/`: instructions for obtaining the raw datasets. The raw data are not included.
- `results/`: summary files and READMEs for each experiment run; `results/README.md` maps runs to the manuscript. Large raw outputs are not included.

## Requirements

- Python 3.13 (3.13.12 was used for the experiments).
- SciPy for the maximum-flow backend and the integer-programming check; NumPy.
- CMake and a C++17 compiler for `cpp/`.

## Run the tests

From the repository root:

    PYTHONPATH=. python3 tests/test_unit.py
    PYTHONPATH=. python3 tests/test_endset.py
    PYTHONPATH=. python3 tests/test_reorient.py

## Reproduce the reduction check (Section 5)

    python3 experiments/strict/hardness_reduction.py --trials 1941 --seed 20261113

Writes `results/strict-hardness-20261113/summary.json`. The expected counts are 1967 formulas, 578 unsatisfiable, and 221 checked with the integer program.

## Data

See `data/README.md`. The transit data are fetched with `experiments/fetch_transit.sh`. The contact data must be obtained from their providers.

## Build the manuscript

    cd submission
    pdflatex main
    bibtex main
    pdflatex main
    pdflatex main

The figures are included as PDF files. To rebuild one from its TikZ source:

    cd submission/figures && TEXINPUTS=..: pdflatex FigN.tex

The Vietnamese version uses the template and bibliography in `submission/`:

    cd vi && TEXINPUTS=../submission: BIBINPUTS=../submission: BSTINPUTS=../submission: latexmk -pdf main-vi.tex

## Status

Public repository: https://github.com/th1enq/exact-edge-cover-temporal-walks
