#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p results/mink-20261030/state results/mink-20261030/logs
# A round is bounded even if a worker stalls in loading or saving.
# Nine batches of 40 seconds cannot fit in 280 seconds; later rounds resume
# unfinished cities. Skip converged cities and prioritize least elapsed work.
timeout --signal=TERM --kill-after=2s 277s bash -c '
set -euo pipefail
python3 - <<'"'"'PY'"'"' | xargs -r -P 3 -n 1 bash -c '\''
city="$1"
exec cpp/build/nscover_mink "results/mink-20261030/inst/$city.json" \
  --out "results/mink-20261030/state/$city.json" --seconds 40 --seed 20261030 \
  > "results/mink-20261030/logs/$city.log" 2>&1
'\'' _
import json
from pathlib import Path
out = Path("results/mink-20261030")
pending = []
for path in sorted((out / "inst").glob("*.json")):
    state = out / "state" / path.name
    s = json.loads(state.read_text()) if state.exists() else {}
    if not s.get("converged", False):
        pending.append((s.get("seconds", 0), path.stem))
for _, city in sorted(pending):
    print(city)
PY
' 
