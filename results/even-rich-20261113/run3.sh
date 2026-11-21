#!/usr/bin/env bash
# Continuation of run2.sh: m=50000 dropped (projected over 30 minutes per run),
# m=20000 reduced to 2 graphs per family. Waits for the m=5000 run of run2.sh.
set -u
cd "$(dirname "$0")/../.."
OUT=results/even-rich-20261113
while pgrep -f "even_rich_bench.py --m 5000 " > /dev/null; do sleep 5; done
echo "exit=(m=5000 finished before run3 started)" >> "$OUT/m5000.log"
run() { m=$1; shift; echo "== m=$m $*"; python3 experiments/even_rich_bench.py --m "$m" --output "$OUT/m$m.jsonl" "$@" > "$OUT/m$m.log" 2>&1; echo "exit=$?" >> "$OUT/m$m.log"; }
run 20000 --count 2 --branch-m 0 --static-m 0 --pf-seconds 900 --seconds 7200
