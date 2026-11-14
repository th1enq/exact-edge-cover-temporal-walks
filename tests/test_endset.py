"""End-set semantics, chain constraints, and restricted pair exchanges."""
import random
import unittest

from nscover import Instance, brute_force, solve_pairflow, build_walks, check_walks


class EndSet(unittest.TestCase):
    def test_json_and_legacy_positionals(self):
        old = Instance(2, [], [1, 0], None, "legacy")
        self.assertNotIn("end_set", old.to_json())
        new = Instance(2, [], [1, 0], end_set={1, 0})
        self.assertEqual(Instance.from_json(new.to_json()), new)
        self.assertEqual(new.to_json()["end_set"], [0, 1])
        with self.assertRaises(ValueError):
            Instance(2, [], [0, 0], [0, 0], end_set=[])
        for bad in ([-1], [2]):
            with self.assertRaises(ValueError):
                Instance(2, [], [0, 0], end_set=bad)

    def test_empty_edges_and_empty_set(self):
        for a, t, answer in (([0, 0], [], True), ([1, 0], [], False),
                             ([1, 0], [0], True), ([1, 0], [1], False)):
            inst = Instance(2, [], a, end_set=t)
            self.assertEqual(brute_force(inst), answer)
            self.assertEqual(solve_pairflow(inst).status == "YES", answer)

    def test_exact_zero_outside_set(self):
        for a, t, answer in (([1, 0], [1], True), ([1, 0], [0], False),
                             ([2, 0], [1], False), ([1, 1], [1], True)):
            inst = Instance(2, [(0, 1, 1)], a, end_set=t)
            self.assertEqual(brute_force(inst), answer)
            self.assertEqual(solve_pairflow(inst).status == "YES", answer)

    def test_random_backends_and_witnesses(self):
        rng = random.Random(461)
        for _ in range(300):
            n = rng.randint(2, 5)
            edges = [(*rng.sample(range(n), 2), rng.randint(1, 3))
                     for _ in range(rng.randint(0, 7))]
            a = [0] * n
            for _ in range(rng.randint(0, 3)):
                a[rng.randrange(n)] += 1
            t = [v for v in range(n) if rng.randrange(2)]
            inst = Instance(n, edges, a, end_set=t)
            expected = brute_force(inst)
            for backend in ("augment", "augment-bfs", "python"):
                result = solve_pairflow(inst, backend=backend)
                self.assertEqual(result.status == "YES", expected, inst.to_json())
                if expected:
                    check_walks(inst, build_walks(inst, result.tails))
            free = inst.free_end()
            all_t = Instance(n, edges, a, end_set=list(range(n)))
            self.assertEqual(solve_pairflow(free), solve_pairflow(all_t))

    def test_proper_set_requires_pair_augmentation(self):
        inst = Instance(5, [(1, 2, 3), (3, 0, 1), (1, 4, 2), (3, 4, 3),
                            (2, 1, 3), (1, 4, 2), (1, 4, 1)],
                        [1, 1, 0, 0, 1], end_set=[0, 1, 3, 4])
        result = solve_pairflow(inst)
        self.assertTrue(brute_force(inst))
        self.assertEqual(result.status, "YES")
        self.assertEqual(result.stats["augmentations"], 1)
        check_walks(inst, build_walks(inst, result.tails))

    def test_witness_checker_rejects_excluded_end(self):
        inst = Instance(2, [(0, 1, 1)], [1, 0], end_set=[0])
        with self.assertRaises(AssertionError):
            check_walks(inst, [(0, [0])])

    def test_min_walks(self):
        from experiments.min_walks_small_S import min_walks
        path = Instance(3, [(0, 1, 1), (1, 2, 2)], [0, 0, 0])
        self.assertEqual(min_walks(path, [0]), 1)
        self.assertIsNone(min_walks(path, [2]))
        self.assertIsNone(min_walks(path, []))
        self.assertEqual(min_walks(Instance(2, [], [0, 0]), []), 0)


if __name__ == "__main__":
    unittest.main()
