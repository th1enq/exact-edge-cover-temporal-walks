#!/usr/bin/env python3
"""Executable boundary checks: JSON, batch framing, limits and witness output."""
import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=ROOT / "cpp/build/nscover_solve")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    checks = 0

    def run(options, text="", expected_code=0):
        nonlocal checks
        process = subprocess.run([str(args.binary.resolve()), *options], input=text,
                                 text=True, capture_output=True, timeout=30)
        if process.returncode != expected_code:
            raise AssertionError((options, process.returncode, process.stderr))
        checks += 1
        return process.stdout

    path = (ROOT / "cpp/examples/nonstrict-path.json").read_text()
    aaai = (ROOT / "cpp/examples/aaai-counterexample.json").read_text()
    for backend in ("online", "greedy", "dinic"):
        for solver in ("pair", "branch", "backtrack"):
            options = ["--solver", solver, "--backend", backend]
            assert json.loads(run(options, path))["status"] == "YES"
            assert json.loads(run(options, aaai))["status"] == "NO"
    result = json.loads(run(["--summary", "--verify-branch", "--verify-backtrack"], path))
    assert result["witness"] == "checked" and result["branch_verified"] and result["backtrack_verified"]
    assert "walks" not in result and "tails" not in result
    result = json.loads(run(["--verify-backtrack", "--max-states", "0"], path))
    assert result["status"] == "YES" and result["backtrack"] == "LIMIT" and not result["backtrack_verified"]
    result = json.loads(run(["--solver", "branch", "--max-flows", "0"], path))
    assert result["status"] == "LIMIT"
    result = json.loads(run(["--solver", "backtrack", "--max-states", "0"], path))
    assert result["status"] == "LIMIT"
    lines = "\n".join([json.dumps(json.loads(path)), "", json.dumps(json.loads(aaai))])
    results = [json.loads(line) for line in run(["--batch"], lines).splitlines()]
    assert [r["status"] for r in results] == ["YES", "NO"]
    for options, text in (([], "{"), ([], path + "false"), (["--unknown"], path),
                          (["--max-flows", "-1"], path), (["--seconds", "nan"], path),
                          (["--solver", "bad"], path), (["--backend", "bad"], path),
                          (["--seconds", "3junk"], path)):
        run(options, text, 2)
    result = {"status": "PASS", "checks": checks}
    print(json.dumps(result))
    if args.output:
        args.output.write_text(json.dumps(result) + "\n")


if __name__ == "__main__":
    main()
