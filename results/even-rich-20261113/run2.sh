#!/usr/bin/env bash
# Continuation of run.sh with fewer instances at the two largest sizes.
# run.sh was stopped after it had started m=1000; this script waits for that run.
set -u
cd "$(dirname "$0")/../.."
OUT=results/even-rich-20261113
while pgrep -f "even_rich_bench.py --m 1000 " > /dev/null; do sleep 5; done
echo "exit=(m=1000 finished before run2 started)" >> "$OUT/m1000.log"
run() { m=$1; shift; echo "== m=$m $*"; python3 experiments/even_rich_bench.py --m "$m" --output "$OUT/m$m.jsonl" "$@" > "$OUT/m$m.log" 2>&1; echo "exit=$?" >> "$OUT/m$m.log"; }
run 5000  --count 10 --branch-m 0 --static-m 0
run 20000 --count 3  --branch-m 0 --static-m 0 --pf-seconds 900
run 50000 --count 1  --branch-m 0 --static-m 0 --pf-seconds 1800 --seconds 7200
