#!/usr/bin/env python3
"""Deterministic unit tests (python3 -m unittest discover -s tests)."""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nscover import (Instance, Timeline, brute_force, build_walks, check_walks,  # noqa: E402
                     solve_branch, solve_pairflow)
from nscover.maxflow import orient_with_indegree  # noqa: E402
from nscover.walks import InfeasibleOrientation  # noqa: E402

X, U, Y, V, W = range(5)
# AAAI 2025 Thm 6.3 counterexample: x-u, u-y at time 1, triangle u, v, w at time 2,
# one walk from x to y.  The walk must leave u at time 1, so the triangle has no walk.
AAAI = Instance(5, [(X, U, 1), (U, Y, 1), (U, V, 2), (V, W, 2), (W, U, 2)],
                [1, 0, 0, 0, 0], [0, 0, 1, 0, 0])


def solved(inst: Instance) -> bool:
    res = solve_pairflow(inst)
    if res.status == "YES":
        check_walks(inst, build_walks(inst, res.tails))
    return res.status == "YES"


class Characterisation(unittest.TestCase):
    def test_aaai_counterexample_is_infeasible(self):
        self.assertFalse(brute_force(AAAI))
        self.assertFalse(solved(AAAI))
        self.assertEqual(solve_branch(AAAI).status, "NO")
        # free end: the only walk still has to take x-u and u-y at time 1
        self.assertFalse(solved(AAAI.free_end()))

    def test_even_component_found(self):
        tl = Timeline(AAAI)
        self.assertEqual([(c.time, c.vertices) for c in tl.even_components()], [(2, [U, V, W])])

    def test_second_walk_makes_it_feasible(self):
        inst = Instance(5, AAAI.edges, [1, 0, 0, 1, 0], [0, 0, 1, 1, 0])
        self.assertTrue(brute_force(inst))
        self.assertTrue(solved(inst))

    def test_nonstrict_uses_two_edges_of_one_snapshot(self):
        path = Instance(3, [(0, 1, 5), (1, 2, 5)], [1, 0, 0], [0, 0, 1])
        self.assertTrue(solved(path))

    def test_empty_instance(self):
        self.assertTrue(solved(Instance(2, [], [1, 0], [1, 0])))
        self.assertFalse(solved(Instance(2, [], [1, 0], [0, 1])))

    def test_isolated_vertex_keeps_its_walks(self):
        self.assertFalse(solved(Instance(3, [(0, 1, 1)], [1, 0, 2], [0, 1, 0])))

    def test_pairflow_needs_augmentation(self):
        # root flow can strand the triangle; the pair flow must reroute a pair
        rng = random.Random(3)
        from nscover.generators import cycle_instance, random_end
        hits = 0
        for _ in range(4000):
            base = cycle_instance(rng)
            inst = base.with_end(random_end(rng, base))
            res = solve_pairflow(inst)
            if res.stats.get("augmentations", 0) and len(inst.edges) <= 10:
                hits += 1
                self.assertEqual(res.status == "YES", brute_force(inst))
        self.assertGreater(hits, 0)


class Witness(unittest.TestCase):
    def test_closed_trail_needs_a_walk(self):
        inst = Instance(3, [(0, 1, 1), (1, 2, 1), (2, 0, 1)], [0, 0, 0])
        with self.assertRaises(InfeasibleOrientation):
            build_walks(inst, [0, 1, 2])

    def test_check_walks_rejects_time_reversal(self):
        inst = Instance(3, [(0, 1, 2), (1, 2, 1)], [1, 0, 0])
        with self.assertRaises(AssertionError):
            check_walks(inst, [(0, [0, 1])])


class Orientation(unittest.TestCase):
    def test_prescribed_indegree(self):
        heads = orient_with_indegree([0, 1, 2], [(0, 1), (1, 2), (2, 0)], {0: 1, 1: 1, 2: 1})
        self.assertIsNotNone(heads)
        self.assertIsNone(orient_with_indegree([0, 1, 2], [(0, 1), (1, 2), (2, 0)],
                                               {0: 3, 1: 0, 2: 0}))


if __name__ == "__main__":
    unittest.main()
