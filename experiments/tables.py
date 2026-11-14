#!/usr/bin/env python3
"""LaTeX tables of the thesis, generated from the result files.

Usage: tables.py <results dir> <output dir>; writes census.tex, transit.tex,
family.tex, family-plot.tex and adversarial.tex, each a tabular (or the coordinates of a
plot) that the thesis inputs.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

SOURCES = [  # (file stem prefix or source name, label, citation)
    ("HighSchool2013_proximity_net.csv", "Trung học 2013", "mastrandrea2015"),
    ("highschool_2012.csv", "Trung học 2012", "fournet2014"),
    ("primaryschool.csv", "Tiểu học", "stehle2011"),
    ("hospital_lyon_contacts.dat", "Bệnh viện", "vanhems2013"),
    ("bt_symmetric.csv", "CNS Bluetooth", "sapiezynski2019"),
    ("calls.csv", "CNS cuộc gọi", "sapiezynski2019"),
    ("sms.csv", "CNS tin nhắn", "sapiezynski2019"),
    ("kuopio", "Kuopio", "kujala2018"),
    ("turku", "Turku", "kujala2018"),
    ("grenoble", "Grenoble", "kujala2018"),
    ("adelaide", "Adelaide", "kujala2018"),
]


def grouped(x) -> str:
    """Thousands separated by a thin space, as in the thesis text (math mode)."""
    return f"{x:,}".replace(",", "\\,")


def num(x) -> str:
    s = grouped(x)
    return f"\\({s}\\)" if "\\," in s else s


def sec(x: float) -> str:
    return f"{x:.2f}".replace(".", "{,}") if x < 10 else f"{x:.1f}".replace(".", "{,}")


def rows_of(path: Path):
    for line in path.read_text().splitlines():
        if line:
            row = json.loads(line)
            if "source" in row:
                yield row


def census(results: Path) -> str:
    groups = defaultdict(list)
    for path in sorted((results / "census-20261025").glob("*.jsonl")):
        for row in rows_of(path):
            groups[row["source"]].append(row)
    lines = []
    totals = defaultdict(int)
    for key, label, cite in SOURCES:
        rows = groups[key]
        base = [r for r in rows if r["scheme"] == "fix"]
        yes = sum(r["pair"]["status"] == "YES" for r in rows)
        dead = sum(r["pair"].get("dead", 0) > 0 for r in rows)
        even = sum(r["even"] > 0 for r in rows)
        aug = max(r["pair"].get("augmentations", 0) for r in rows)
        flows = max((r["branch"]["flows"] for r in rows if "branch" in r), default=0)
        secs = max(r["pair"]["seconds"] for r in rows)
        lines.append(f"{label} \\cite{{{cite}}} & {num(len(base))} & {num(len(rows))} & "
                     f"{num(max(r['m'] for r in rows))} & {num(even)} & {num(dead)} & {aug} & "
                     f"{flows} & {num(yes)}/{num(len(rows) - yes)} & {sec(secs)} \\\\")
        totals["windows"] += len(base)
        totals["rows"] += len(rows)
        totals["even"] += even
        totals["dead"] += dead
        totals["yes"] += yes
    lines.append("\\midrule")
    lines.append(f"Tổng & {num(totals['windows'])} & {num(totals['rows'])} & & "
                 f"{num(totals['even'])} & {num(totals['dead'])} & & & "
                 f"{num(totals['yes'])}/{num(totals['rows'] - totals['yes'])} & \\\\")
    return "\n".join(lines) + "\n"


def transit(results: Path) -> str:
    lines = []
    for city in ("turku", "grenoble"):
        for problem in ("fix", "free"):
            path = results / "transit-full-20261025" / f"{city}-{problem}.json"
            row = json.loads(path.read_text())
            pair, branch = row["pair"], row["branch"]
            status = "vượt giới hạn" if branch["status"] == "LIMIT" else branch["status"]
            name = "\\FIX" if problem == "fix" else "\\FREE"
            lines.append(f"{city.capitalize()} & {name} & "
                         f"{num(row['m'])} & {num(row['even'])} & {pair['dead']} & "
                         f"{pair['augmentations']} & {sec(pair['seconds'])} & {pair['status']} & "
                         f"{branch['flows']} & {sec(branch['seconds'])} & {status} \\\\")
    return "\n".join(lines) + "\n"


def family(results: Path) -> tuple[str, str]:
    rows = list(rows_of_family(results / "family-20261025" / "family.jsonl"))
    lines, branch_pts, pair_pts = [], [], []
    for r in rows:
        b = r.get("branch")
        bf = "--" if b is None else (f"\\(>{grouped(b['flows'])}\\)" if b["status"] == "LIMIT"
                                     else num(b["flows"]))
        bs = "--" if b is None else sec(b["seconds"])
        lines.append(f"{r['e']} & {num(r['m'])} & {bf} & {bs} & {r['pair']['augmentations']} & "
                     f"{sec(r['pair']['seconds'])} \\\\")
        if b is not None and b["status"] != "LIMIT":
            branch_pts.append(f"({r['e']},{b['flows']})")
        if r["e"] <= 20:
            pair_pts.append(f"({r['e']},{r['pair']['augmentations'] + 1})")
    plot = ("\\addplot+[mark=*] coordinates {" + " ".join(branch_pts) + "};\n"
            "\\addplot+[mark=square*] coordinates {" + " ".join(pair_pts) + "};\n")
    return "\n".join(lines) + "\n", plot


def rows_of_family(path: Path):
    for line in path.read_text().splitlines():
        if line:
            yield json.loads(line)


def adversarial(results: Path) -> str:
    lines = []
    for path in sorted((results / "adversarial-20261025").glob("seed*.jsonl")):
        rows = [json.loads(line) for line in path.read_text().splitlines() if line]
        if not rows:
            continue
        best = max(rows, key=lambda r: r["branch_flows"])
        lines.append(f"{path.stem[4:]} & {len(rows)} & {best['m']} & {best['even']} & "
                     f"{num(best['branch_flows'])} & {best['branch_status']} & "
                     f"{best['dead']} & {best['augmentations']} \\\\")
    return "\n".join(lines) + "\n"


def main() -> None:
    results, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    (out / "census.tex").write_text(census(results))
    (out / "transit.tex").write_text(transit(results))
    table, plot = family(results)
    (out / "family.tex").write_text(table)
    (out / "family-plot.tex").write_text(plot)
    (out / "adversarial.tex").write_text(adversarial(results))


if __name__ == "__main__":
    main()
