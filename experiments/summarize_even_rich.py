#!/usr/bin/env python3
"""Summarize results/even-rich-*/m*.jsonl into the numbers used in the paper."""

from __future__ import annotations

import collections
import json
import statistics
import sys
from pathlib import Path


def load(folder: Path):
    rows, truncated = [], []
    paths = [p for p in folder.glob("m*.jsonl") if p.stem[1:].isdigit()]
    for path in sorted(paths, key=lambda p: int(p.stem[1:])):
        for line in path.open(encoding="utf-8"):
            r = json.loads(line)
            if r.get("meta"):
                continue
            if r.get("truncated"):
                truncated.append(r)
                continue
            rows.append(r)
    return rows, truncated


def main() -> None:
    folder = Path(sys.argv[1] if len(sys.argv) > 1 else "results/even-rich-20261113")
    rows, truncated = load(folder)
    out = {"rows": len(rows), "truncated": truncated, "cells": [], "totals": {}}
    # group by family and requested size; generated m exceeds the target by at most 7
    groups = collections.defaultdict(list)
    for r in rows:
        size = min((12, 50, 200, 1000, 5000, 20000, 50000), key=lambda s: abs(s - r["m"]))
        groups[(r["family"], size)].append(r)
    tot = collections.Counter()
    for (family, size), rs in sorted(groups.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        inst = {r["index"] for r in rs}
        yes_rows = [r for r in rs if r["variant"].endswith("yes")]
        cut_rows = [r for r in rs if r["variant"].endswith("cut")]
        solved = [r for r in rs if r["pf"]["status"] in ("YES", "NO")]
        dead = [r["pf"].get("dead", 0) for r in solved]
        even = [r["even"] for r in solved]
        frac = [d / e for d, e in zip(dead, even) if e]
        times = [r["pf"]["seconds"] for r in solved]
        bb = [r for r in rs if "bb" in r]
        st = [r for r in rs if "static" in r and r["static"]["answer"] is not None]
        cell = {
            "family": family, "size": size, "instances": len(inst), "runs": len(rs),
            "m_max": max(r["m"] for r in rs),
            "all_even": all(r["components"] == r["even"] for r in rs),
            "even_mean": round(statistics.mean(even), 1) if even else None,
            "dead_mean": round(statistics.mean(dead), 1) if dead else None,
            "dead_max": max(dead) if dead else None,
            "dead_frac_mean": round(statistics.mean(frac), 3) if frac else None,
            "dead_positive_runs": sum(d > 0 for d in dead),
            "aug_max": max((r["pf"].get("augmentations", 0) for r in solved), default=None),
            "yes_planted_ok": all(r["pf"]["status"] == "YES" for r in yes_rows),
            "cut_yes": sum(r["pf"]["status"] == "YES" for r in cut_rows),
            "cut_no": sum(r["pf"]["status"] == "NO" for r in cut_rows),
            "no_reasons": dict(collections.Counter(r["pf"].get("reason") for r in rs
                                                   if r["pf"]["status"] == "NO")),
            "pf_timeout": sum(r["pf"]["status"] == "TIMEOUT" for r in rs),
            "pf_median_s": round(statistics.median(times), 4) if times else None,
            "pf_max_s": round(max(times), 4) if times else None,
            "oracle_runs": sum("oracle" in r for r in rs),
            "oracle_disagree": sum("oracle" in r and r["oracle"] != r["pf"]["status"] for r in rs),
            "bb_runs": len(bb),
            "bb_limit": sum(r["bb"]["status"] == "LIMIT" for r in bb),
            "bb_disagree": sum(r["bb"]["status"] in ("YES", "NO") and
                               r["bb"]["status"] != r["pf"]["status"] for r in bb),
            "static_runs": len(st),
            "static_wrong_yes": sum(r["static"]["answer"] == "YES" and r["pf"]["status"] == "NO"
                                    for r in st),
            "static_wrong_no": sum(r["static"]["answer"] == "NO" and r["pf"]["status"] == "YES"
                                   for r in st),
            "static_on_pf_no": sum(r["pf"]["status"] == "NO" for r in st),
            "walks_checked": sum(r["pf"].get("walks_checked", False) for r in rs),
            "pf_yes": sum(r["pf"]["status"] == "YES" for r in rs),
        }
        out["cells"].append(cell)
        for key in ("instances", "runs", "dead_positive_runs", "cut_yes", "cut_no",
                    "pf_timeout", "oracle_runs", "oracle_disagree", "bb_runs", "bb_limit",
                    "bb_disagree", "static_runs", "static_wrong_yes", "static_wrong_no",
                    "static_on_pf_no", "walks_checked", "pf_yes"):
            tot[key] += cell[key]
    out["totals"] = dict(tot)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
