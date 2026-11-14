#!/usr/bin/env python3
"""Bảng tóm tắt các kết quả transit_full.py trong một thư mục (mặc định transit-more-20261025)."""
import glob
import json
import sys
from pathlib import Path

folder = Path(sys.argv[1] if len(sys.argv) > 1 else
              Path(__file__).resolve().parents[1] / "results/transit-more-20261025")
rows = {}
for f in sorted(glob.glob(str(folder / "*.json"))):
    r = json.loads(Path(f).read_text())
    rows.setdefault(r["source"], {})[r["problem"]] = r
print("| city | n | m | k | even | D fix | s fix | D free | s free |")
print("|---|---|---|---|---|---|---|---|---|")
for city, by in sorted(rows.items(), key=lambda kv: -next(iter(kv[1].values()))["m"]):
    any_ = next(iter(by.values()))
    cell = []
    for p in ("fix", "free"):
        if p in by:
            q = by[p]["pair"]
            mark = "" if q["status"] == "YES" else f" {q['status']}"
            cell += [f"{q.get('dead')}{mark}", f"{q['seconds']}"]
        else:
            cell += ["-", "-"]
    print(f"| {city} | {any_['n']} | {any_['m']} | {any_['k']} | {any_['even']} | " + " | ".join(cell) + " |")
