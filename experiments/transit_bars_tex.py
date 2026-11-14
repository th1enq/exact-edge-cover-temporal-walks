#!/usr/bin/env python3
"""Sinh đoạn pgfplots (biểu đồ D và thời gian giải theo thành phố) từ results/transit-more-20261025.

Thành phố chạy cả ngày lấy từ thư mục gốc; thành phố lớn (khung 3 giờ đông nhất) lấy từ
window-3h/ và được đánh dấu *.  In ra stdout; cũng in một dòng tóm tắt lên stderr.
"""
import json
import sys
from pathlib import Path

base = Path(__file__).resolve().parents[1] / "results/transit-more-20261025"


def load(folder: Path, star: str) -> dict:
    rows = {}
    for f in sorted(folder.glob("*.json")):
        r = json.loads(f.read_text())
        rows.setdefault(r["source"] + star, {})[r["problem"]] = r
    return {c: by for c, by in rows.items() if {"fix", "free"} <= by.keys()}


rows = {**load(base, ""), **load(base / "window-3h", "*")}
order = sorted(rows, key=lambda c: (rows[c]["fix"]["pair"]["dead"], c))


def label(c: str) -> str:
    star = "$^*$" if c.endswith("*") else ""
    return f"{c.rstrip('*').capitalize()}{star} ({round(rows[c]['fix']['m'] / 1000)}k)"


names = ",".join("{" + label(c) + "}" for c in order)
fix = " ".join(f"({rows[c]['fix']['pair']['dead']},{i})" for i, c in enumerate(order))
free = " ".join(f"({rows[c]['free']['pair']['dead']},{i})" for i, c in enumerate(order))
print(f"% sinh bởi experiments/transit_bars_tex.py; {len(order)} thành phố")
print(f"\\def\\transitcount{{{len(order) - 1}}}")
print(f"\\def\\transitlabels{{{names}}}")
print(f"\\def\\transitfix{{{fix}}}")
print(f"\\def\\transitfree{{{free}}}")
for prob in ("fix", "free"):
    secs = " ".join(f"({rows[c][prob]['pair']['seconds']},{i})" for i, c in enumerate(order))
    print(f"\\def\\transittime{prob}{{{secs}}}")
full = [c for c in order if not c.endswith("*")]
positive = sum(rows[c]["fix"]["pair"]["dead"] > 0 or rows[c]["free"]["pair"]["dead"] > 0 for c in order)
assert all(by[p]["pair"]["status"] == "YES" for by in rows.values() for p in by)
slowest = max(by[p]["pair"]["seconds"] for by in rows.values() for p in by)
print(f"{len(order)} cities ({len(full)} full day), D>0 in {positive}, "
      f"max m full-day {max(rows[c]['fix']['m'] for c in full)}, slowest {slowest}s",
      file=sys.stderr)
