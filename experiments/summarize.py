#!/usr/bin/env python3
"""Summarise census JSONL files: one line per (source, scheme)."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path


def main() -> None:
    groups = defaultdict(list)
    complete = {}
    for path in sys.argv[1:]:
        lines = [json.loads(line) for line in Path(path).read_text().splitlines() if line]
        complete[Path(path).name] = lines[-1].get("complete") if lines else None
        for row in lines:
            if "source" in row:
                groups[(row["source"], row["scheme"])].append(row)
    print("| source | scheme | windows | max m | with even | dead at root | YES | NO (flow) "
          "| NO (pairs) | max aug | max B&B flows | max pair s |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for (source, scheme), rows in sorted(groups.items()):
        pair = [r["pair"] for r in rows]
        flows = [r["branch"]["flows"] for r in rows if "branch" in r]
        print(f"| {source} | {scheme} | {len(rows)} | {max(r['m'] for r in rows)} "
              f"| {sum(r['even'] > 0 for r in rows)} | {sum(p.get('dead', 0) > 0 for p in pair)} "
              f"| {sum(p['status'] == 'YES' for p in pair)} "
              f"| {sum(p.get('reason') in ('chain network', 'counting') for p in pair)} "
              f"| {sum(p.get('reason') == 'no augmenting path' for p in pair)} "
              f"| {max((p.get('augmentations', 0) for p in pair), default=0)} "
              f"| {max(flows, default='-')} | {max(p['seconds'] for p in pair):.2f} |")
    print()
    print("complete:", complete)


if __name__ == "__main__":
    main()
