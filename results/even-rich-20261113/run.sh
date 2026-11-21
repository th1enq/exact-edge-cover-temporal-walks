#!/usr/bin/env bash
# Sequential runs (no concurrent jobs) of experiments/even_rich_bench.py.
set -u
cd "$(dirname "$0")/../.."
OUT=results/even-rich-20261113
run() { m=$1; shift; echo "== m=$m $*"; python3 experiments/even_rich_bench.py --m "$m" --output "$OUT/m$m.jsonl" "$@" > "$OUT/m$m.log" 2>&1; echo "exit=$?" >> "$OUT/m$m.log"; }
run 12    --count 200 --oracle-m 14
run 50    --count 100
run 200   --count 50
run 1000  --count 20 --branch-seconds 5
run 5000  --count 10 --branch-m 0 --static-m 0
run 20000 --count 5  --branch-m 0 --static-m 0 --pf-seconds 900
run 50000 --count 2  --branch-m 0 --static-m 0 --pf-seconds 1500 --seconds 7200
