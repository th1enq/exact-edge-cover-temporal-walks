#!/usr/bin/env python3
"""Cross-language verification, including independent Python witness checks.

Small cases compare C++ pair/branch/backtracking, all three C++ chain backends, and
Python pair/branch/backtracking. Larger cases compare pair/branch and witnesses.
This script is a test driver; the C++ executables do not invoke Python.
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from nscover import brute_force, build_walks, check_walks, solve_branch, solve_pairflow
from nscover.generators import cycle_instance, random_end, random_instance


class Client:
    def __init__(self, binary, backend, small):
        args = [str(binary), "--batch", "--backend", backend,
                "--verify-branch", "--max-flows", "2000", "--seconds", "2"]
        if small:
            args += ["--verify-backtrack", "--max-states", "5000000"]
        self.process = subprocess.Popen(args, stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, text=True)

    def solve(self, inst):
        self.process.stdin.write(json.dumps(inst.to_json()) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError(f"C++ process exited: {self.process.poll()}")
        return json.loads(line)

    def close(self):
        self.process.stdin.close()
        self.process.stdout.close()
        code = self.process.wait(timeout=10)
        if code:
            raise RuntimeError(f"C++ process exited with {code}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=ROOT / "cpp/build/nscover_solve")
    parser.add_argument("--cases", type=int, default=2000, help="base graphs, each FIX and FREE")
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--large", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rng = random.Random(args.seed)
    clients = [Client(args.binary.resolve(), backend, not args.large)
               for backend in ("online", "greedy", "dinic")]
    stats = Counter()
    try:
        for index in range(args.cases):
            if args.large:
                base = cycle_instance(rng, max_n=9, max_snapshots=10)
            elif rng.random() < .6:
                base = cycle_instance(rng)
                while base.m > 11:
                    base = cycle_instance(rng)
            else:
                base = random_instance(rng)
            for inst in (base.free_end(), base.with_end(random_end(rng, base))):
                try:
                    pair = solve_pairflow(inst)
                    branch = solve_branch(inst, max_flows=2000, max_seconds=2)
                    if branch.status != "LIMIT":
                        assert pair.status == branch.status
                        stats["python_branch_checked"] += 1
                    else:
                        stats["python_branch_limit"] += 1
                    if not args.large:
                        assert (pair.status == "YES") == brute_force(inst)
                        stats["python_oracle_checked"] += 1
                    if pair.status == "YES":
                        check_walks(inst, build_walks(inst, pair.tails))
                    for client in clients:
                        result = client.solve(inst)
                        assert result["status"] == pair.status, result
                        if not args.large:
                            assert result["backtrack_verified"], result
                        if result["branch_verified"]:
                            stats["cpp_branch_checked"] += 1
                        else:
                            stats["cpp_branch_limit"] += 1
                        if result["status"] == "YES":
                            # Two independent witness paths: C++ walk sequences and
                            # Python reconstruction from C++ orientation.
                            check_walks(inst, [(w["start"], w["edges"]) for w in result["walks"]])
                            check_walks(inst, build_walks(inst, result["tails"]))
                            stats["cpp_witnesses_python_checked"] += 1
                        stats["cpp_augmented"] += result["augmentations"] > 0
                        stats["cpp_no_path"] += result["reason"] == "no augmenting path"
                    stats["instances"] += 1
                    stats["yes"] += pair.status == "YES"
                except BaseException:
                    failure = ROOT / "cpp/failure.json"
                    inst.save(failure)
                    print(f"Replay failing instance: {failure}", file=sys.stderr)
                    raise
    finally:
        for client in clients:
            client.close()
    result = {"status": "PASS", "seed": args.seed, "large": args.large, **stats}
    text = json.dumps(result, sort_keys=True)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n")


if __name__ == "__main__":
    main()
