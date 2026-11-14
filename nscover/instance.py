"""Instances of exact edge cover by non-strict temporal walks.

An instance is an undirected temporal multigraph on vertices 0..n-1, a start vector
``start`` (start[v] walks begin at v) and, for the fixed-end problem NS-FIX, an end
vector ``end``. With neither end constraint this is NS-FREE; ``end_set`` restricts
all final tokens to that set (NS-ENDSET), with free distribution inside it. A walk may be empty
and may use several edges with the same time stamp, in any order.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Instance:
    n: int
    edges: list[tuple[int, int, int]]  # (u, v, time), u != v
    start: list[int]
    end: list[int] | None = None
    name: str = field(default="", compare=False)
    end_set: list[int] | set[int] | None = None

    def __post_init__(self) -> None:
        if self.end is not None and self.end_set is not None:
            raise ValueError("end and end_set are mutually exclusive")
        if self.end_set is not None:
            if any(not isinstance(v, int) or not 0 <= v < self.n for v in self.end_set):
                raise ValueError("end_set contains an invalid vertex")
            self.end_set = sorted(set(self.end_set))
        if len(self.start) != self.n:
            raise ValueError("start vector has the wrong length")
        if self.end is not None and len(self.end) != self.n:
            raise ValueError("end vector has the wrong length")
        if min(self.start, default=0) < 0 or min(self.end or [0]) < 0:
            raise ValueError("start and end counts must be non-negative")
        for u, v, _ in self.edges:
            if u == v or not (0 <= u < self.n and 0 <= v < self.n):
                raise ValueError(f"bad edge {(u, v)}")

    @property
    def m(self) -> int:
        return len(self.edges)

    @property
    def k(self) -> int:
        return sum(self.start)

    def free_end(self) -> "Instance":
        return Instance(self.n, self.edges, self.start, None, self.name)

    def with_end(self, end: list[int]) -> "Instance":
        return Instance(self.n, self.edges, self.start, list(end), self.name)

    def to_json(self) -> dict:
        data = {"num_vertices": self.n, "start": self.start,
                "edges": [{"u": u, "v": v, "time": t} for u, v, t in self.edges]}
        if self.end is not None:
            data["end"] = self.end
        if self.end_set is not None:
            data["end_set"] = list(self.end_set)
        if self.name:
            data["name"] = self.name
        return data

    @staticmethod
    def from_json(data: dict) -> "Instance":
        edges = [(e["u"], e["v"], e["time"]) for e in data["edges"]]
        return Instance(data["num_vertices"], edges, list(data["start"]),
                        list(data["end"]) if data.get("end") is not None else None,
                        data.get("name", ""), data.get("end_set"))

    def save(self, path: Path) -> None:
        Path(path).write_text(json.dumps(self.to_json()), encoding="utf-8")

    @staticmethod
    def load(path: Path) -> "Instance":
        return Instance.from_json(json.loads(Path(path).read_text(encoding="utf-8")))
