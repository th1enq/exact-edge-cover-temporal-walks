"""Loaders for the real temporal networks and terminal schemes.

Sources (raw files are not in the repository; pass their paths):
  * SocioPatterns contact files: "t i j [Ci Cj]" per line, 20 s bins;
  * Copenhagen Networks Study (Sapiezynski et al. 2019): bt_symmetric.csv (5 min bins,
    optional RSSI filter), calls.csv, sms.csv (directed in the source, used undirected);
  * public transport (Kujala et al. 2018): network_temporal_day.csv, one edge per trip
    segment at its departure time.
Duplicate contacts (same time, same pair) are merged; self-contacts are dropped.

Terminal schemes for a window:
  * ``greedy``: scan snapshots in time order; an edge is taken by a walk standing at one
    endpoint, and a new walk is created at an endpoint when none stands there.  The
    created walks are the start vector and the final positions the end vector, so the
    instance is feasible by construction (both NS-FREE and NS-FIX).
  * ``trips`` (transit only): one walk per vehicle trip, from its first to its last stop.
  * ``tight``: the greedy start vector with ``r`` walks removed at random (seeded); the
    end vector is dropped (NS-FREE).  These instances are feasible only when the greedy
    scan wasted walks, so they exercise NO answers and walk-free components.
"""

from __future__ import annotations

import csv
import gzip
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nscover import Instance  # noqa: E402

Contact = tuple[int, str, str]


def _open(path: Path):
    return gzip.open(path, "rt", encoding="utf-8") if str(path).endswith(".gz") else \
        open(path, encoding="utf-8")


def sociopatterns(path: Path) -> list[Contact]:
    out = set()
    with _open(path) as handle:
        for line in handle:
            fields = line.split()
            if len(fields) < 3 or line.startswith("#") or fields[1] == fields[2]:
                continue
            a, b = sorted(fields[1:3])
            out.add((int(fields[0]), a, b))
    return sorted(out)


def copenhagen(path: Path, min_rssi: int | None = None) -> list[Contact]:
    """bt_symmetric.csv, calls.csv or sms.csv; the layer is read from the header."""
    out = set()
    with _open(path) as handle:
        header = handle.readline()
        bluetooth = "rssi" in header
        for line in handle:
            fields = line.rstrip().split(",")
            t, a, b = int(fields[0]), fields[1], fields[2]
            if a == b or int(b) < 0 or int(a) < 0:
                continue
            if bluetooth and min_rssi is not None and int(fields[3]) < min_rssi:
                continue
            out.add((t, *sorted((a, b))))
    return sorted(out)


def transit_trips(path: Path, strict: bool = False,
                  dedupe: bool = True) -> list[list[Contact]]:
    """Trips as lists of (departure, from_stop, to_stop); inconsistent trips are dropped.

    Departures along a trip must be non-decreasing (a non-strict walk); ``strict=True``
    also drops trips with two consecutive segments at the same departure time, which is
    what the census of 2026-10-25 did.  Trips identical to an earlier one (same segments at
    the same times, a feed artefact) are dropped unless ``dedupe=False``.
    """
    trips: dict[str, list] = defaultdict(list)
    with _open(path) as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            trips[row["trip_I"]].append((int(row["seq"]), int(row["dep_time_ut"]),
                                         row["from_stop_I"], row["to_stop_I"]))
    kept = []
    for trip in trips.values():
        trip.sort()
        if all((b[1] > a[1] if strict else b[1] >= a[1]) and a[3] == b[2]
               for a, b in zip(trip, trip[1:])) and \
                all(c[2] != c[3] for c in trip):
            kept.append([(dep, a, b) for _, dep, a, b in trip])
    if dedupe:
        seen: set[tuple] = set()
        kept = [t for t in kept if not (tuple(t) in seen or seen.add(tuple(t)))]
    return kept


def windows(contacts: list[Contact], duration: int | None):
    """(index, contacts) per window of ``duration`` seconds; None = one full window."""
    if duration is None:
        yield 0, contacts
        return
    t0 = min(t for t, _, _ in contacts)
    buckets: dict[int, list[Contact]] = defaultdict(list)
    for c in contacts:
        buckets[(c[0] - t0) // duration].append(c)
    yield from sorted(buckets.items())


def _index(contacts):
    people = sorted({p for _, a, b in contacts for p in (a, b)})
    vid = {p: i for i, p in enumerate(people)}
    rank = {t: i + 1 for i, t in enumerate(sorted({t for t, _, _ in contacts}))}
    return vid, rank


def greedy_instance(contacts: list[Contact], name: str = "") -> Instance:
    vid, rank = _index(contacts)
    n = len(vid)
    edges = [(vid[a], vid[b], rank[t]) for t, a, b in sorted(contacts)]
    start, tokens = [0] * n, [0] * n
    for u, v, _ in edges:
        if not tokens[u] and not tokens[v]:
            start[u] += 1
            tokens[u] += 1
        x, y = (u, v) if tokens[u] else (v, u)
        tokens[x] -= 1
        tokens[y] += 1
    return Instance(n, edges, start, tokens, name)


def trip_instance(trips: list[list[Contact]], name: str = "") -> Instance:
    vid, rank = _index([c for trip in trips for c in trip])
    n = len(vid)
    start, end, edges = [0] * n, [0] * n, []
    for trip in trips:
        start[vid[trip[0][1]]] += 1
        end[vid[trip[-1][2]]] += 1
        edges += [(vid[a], vid[b], rank[t]) for t, a, b in trip]
    return Instance(n, edges, start, end, name)


def tight_instance(inst: Instance, remove: int, seed: int) -> Instance | None:
    """Remove ``remove`` walks from the start vector (NS-FREE); None if too few walks."""
    if inst.k <= remove:
        return None
    rng = random.Random(seed)
    pool = [v for v, c in enumerate(inst.start) for _ in range(c)]
    start = list(inst.start)
    for v in rng.sample(pool, remove):
        start[v] -= 1
    return Instance(inst.n, inst.edges, start, None, inst.name)
