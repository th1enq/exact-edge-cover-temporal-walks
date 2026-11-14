#!/usr/bin/env python3
"""Inventory local transit files; offline, stdlib only, JSON on stdout.

Run from any directory: python3 -I experiments/transit_manifest.py
Rows exclude the CSV header. Times retain the input Unix-second values, without
rounding or filtering. This inventories raw rows, not deduplicated solver edges.
No files are written by this script. Redirect stdout to a new manifest to save it.
"""

import csv
import hashlib
import json
from pathlib import Path
import re
import sys
import time


ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def inspect_file(path, deadline):
    item = {"file_name": path.name, "path": path.relative_to(ROOT).as_posix(),
            "size_bytes": path.stat().st_size, "sha256": digest(path),
            "row_count": None, "time_range": None}
    if path.suffix.lower() != ".csv":
        item["note"] = "Row count/time range not applicable to non-CSV file."
        return item
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream, delimiter=";")
        columns = next(reader)
        time_columns = [c for c in ("dep_time_ut", "arr_time_ut") if c in columns]
        indices = [(c, columns.index(c)) for c in time_columns]
        ranges = {c: [None, None] for c in time_columns}
        rows = 0
        for row in reader:
            if len(row) != len(columns):
                raise ValueError(f"{path}:{reader.line_num}: unexpected field count")
            rows += 1
            for name, index in indices:
                value = int(row[index])
                bounds = ranges[name]
                if bounds[0] is None or value < bounds[0]:
                    bounds[0] = value
                if bounds[1] is None or value > bounds[1]:
                    bounds[1] = value
            if rows % 65536 == 0 and time.monotonic() > deadline:
                raise TimeoutError("Manifest scan exceeded internal 110-second budget")
    item["row_count"] = rows
    item["time_range"] = {
        "unit": "Unix seconds, as stored", "columns": {
            c: {"min": bounds[0], "max": bounds[1]} for c, bounds in ranges.items()},
        "min": min((v[0] for v in ranges.values() if v[0] is not None), default=None),
        "max": max((v[1] for v in ranges.values() if v[1] is not None), default=None)}
    if not indices:
        item["note"] = "chưa có: recognized timestamp columns"
    return item


def main():
    began = time.monotonic()
    raw = ROOT / "data/raw/transit"
    fetch = ROOT / "experiments/fetch_transit.sh"
    text = fetch.read_text(encoding="utf-8")
    record = re.search(r"^record=(\d+)$", text, re.MULTILINE).group(1)
    url_template = re.search(r'https://zenodo\.org/api/records/\$record', text).group()
    record_url = url_template.replace("$record", record)
    metadata_path = raw / f"record-{record}.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    archives = {f["key"].lower(): f for f in metadata["files"]}
    # These are repository declarations, not independently verified permissions.
    # Keep attribution explicit; do not infer a city's licence from the record's
    # generic "other-at" identifier or a licence used by a different city.
    licence_source = "thesis/chapters/appendix-tai-lap.tex"
    declarations = {"kuopio": "CC BY 4.0", "turku": "CC BY 4.0",
                    "adelaide": "CC BY 4.0", "grenoble": "ODbL 1.0"}
    licence_text = (ROOT / licence_source).read_text(encoding="utf-8")
    declared = ("CC BY 4.0 (Kuopio, Turku, Adelaide)" in licence_text
                and "ODbL 1.0 (Grenoble)" in licence_text)
    cities = []
    for directory in sorted(p for p in raw.iterdir() if p.is_dir()):
        archive = archives.get(directory.name.lower() + ".zip")
        files = [inspect_file(p, began + 110) for p in sorted(directory.rglob("*"))
                 if p.is_file()]
        licence = declarations.get(directory.name) if declared else None
        cities.append({
            "city": directory.name,
            "source_urls": [record_url] + ([archive["links"]["self"]] if archive else []),
            "source_url_evidence": ["experiments/fetch_transit.sh",
                                    metadata_path.relative_to(ROOT).as_posix()],
            "archive_key": archive["key"] if archive else None,
            "licence": licence or "chưa xác nhận",
            "licence_evidence": f"{licence_source}:8" if licence else None,
            "licence_status": "repo declaration only; chưa xác minh điều khoản gốc"
                              if licence else "chưa xác nhận",
            "files": files})
    result = {
        "schema_version": 1, "scope": "raw local transit files; offline inventory",
        "source_url_template": url_template,
        "source_record": {"path": metadata_path.relative_to(ROOT).as_posix(),
                          "size_bytes": metadata_path.stat().st_size,
                          "sha256": digest(metadata_path),
                          "licence_identifier_as_stored": metadata.get("metadata", {}).get("license")},
        "notes": ["URLs are local provenance strings; no network request was made.",
                  "Archive URLs come from the cached record used by fetch_transit.sh.",
                  "CSV header excluded; duplicate rows and equal timestamps retained.",
                  "Time range is the union of departure and arrival ranges, in stored Unix seconds.",
                  "Licences are unverified repository declarations where explicitly stated; otherwise chưa xác nhận.",
                  "Raw row counts are not solver edge counts or trip counts."],
        "city_count": len(cities), "file_count": sum(len(c["files"]) for c in cities),
        "total_rows": sum(f["row_count"] or 0 for c in cities for f in c["files"]),
        "cities": cities}
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
