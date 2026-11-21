#!/usr/bin/env bash
set -eu
# Cached Nix packages: daemon access is unavailable in the execution sandbox.
export PYTHONPATH="/nix/store/2zn0v1k3nnc25snk47mf5vjimwdva4sm-python3.13-scipy-1.16.3/lib/python3.13/site-packages:/nix/store/bvcpg8ny128rrnkzhw5wmkakp06hpm62-python3.13-numpy-2.3.4/lib/python3.13/site-packages${PYTHONPATH:+:$PYTHONPATH}"
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
exec timeout 240 python3 experiments/ilp_baseline.py "$@"
