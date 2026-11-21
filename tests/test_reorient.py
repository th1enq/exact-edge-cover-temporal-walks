#!/usr/bin/env python3
"""Equivalence and path-reversal checks for optional incremental reorientation."""
from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nscover import Instance, Timeline, build_walks, check_walks, solve_pairflow
from nscover.generators import cycle_instance, random_end, random_instance
from nscover.pairflow import PairFlow


class Reorientation(unittest.TestCase):
    def test_random_fix_and_free(self):
        rng = random.Random(20261115)
        reversals = 0
        answers = set()
        for index in range(2000):
            generator = cycle_instance if index % 2 else random_instance
            base = generator(rng)
            for inst in (base.free_end(), base.with_end(random_end(rng, base))):
                with self.subTest(index=index, fixed=inst.end is not None):
                    scratch = solve_pairflow(inst, reorient="scratch")
                    incremental = solve_pairflow(inst, reorient="incremental")
                    self.assertEqual(incremental.status, scratch.status, inst.to_json())
                    answers.add(incremental.status)
                    reversals += incremental.stats["path_reversals"]
                    self.assertNotIn("path_reversals", scratch.stats)
                    for result in (scratch, incremental):
                        if result.status == "YES":
                            check_walks(inst, build_walks(inst, result.tails))
        self.assertEqual(answers, {"YES", "NO"})
        self.assertGreater(reversals, 0)

    def test_default_and_invalid_mode(self):
        inst = Instance(2, [], [1, 0], [0, 1])
        self.assertEqual(solve_pairflow(inst), solve_pairflow(inst, reorient="scratch"))
        with self.assertRaises(ValueError):
            solve_pairflow(inst, reorient="invalid")
        with self.assertRaises(ValueError):
            PairFlow(inst, Timeline(inst), [], reorient="invalid")

    def test_parallel_edges_multiple_paths_and_noop(self):
        inst = Instance(3, [(0, 1, 1)] * 2 + [(1, 2, 1)] * 2, [4, 0, 0])
        pf = PairFlow(inst, Timeline(inst), [0, 0, 1, 1], reorient="incremental")
        pf._reorient_incremental(0, {0: 2, 1: 2, 2: 0})
        self.assertEqual(pf.heads[0], [0, 0, 1, 1])
        self.assertEqual(pf.path_reversals, 2)
        pf._reorient_incremental(0, {0: 2, 1: 2, 2: 0})
        self.assertEqual(pf.path_reversals, 2)

    def test_unreachable_target(self):
        inst = Instance(3, [(0, 1, 1), (1, 2, 1)], [2, 0, 0])
        pf = PairFlow(inst, Timeline(inst), [0, 1], reorient="incremental")
        for target in ({0: 2, 1: 0, 2: 0}, {0: 0, 1: 0, 2: 0},
                       {0: -1, 1: 1, 2: 2}):
            with self.assertRaisesRegex(AssertionError, "realisable set"):
                pf._reorient_incremental(0, target)

    def test_shared_box_and_even_checks(self):
        inst = Instance(2, [(0, 1, 1)] * 2, [2, 0])
        for mode in ("scratch", "incremental"):
            pf = PairFlow(inst, Timeline(inst), [0, 1], reorient=mode)
            pf.x[pf.port(0, 0, 0)] = 1
            with self.assertRaisesRegex(AssertionError, "alpha, beta"):
                pf._reorient(0)
            for v in (0, 1):
                for side in (0, 1):
                    pf.x[pf.port(0, v, side)] = 0
            with self.assertRaisesRegex(AssertionError, "even component"):
                pf._reorient(0)


if __name__ == "__main__":
    unittest.main()
