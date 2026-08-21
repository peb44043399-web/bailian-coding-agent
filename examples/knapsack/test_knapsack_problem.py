from __future__ import annotations

import unittest

from examples.knapsack.knapsack_problem import knapsack, knapsack_with_items


class KnapsackTests(unittest.TestCase):
    def test_first_documented_example(self) -> None:
        weights = [2, 1, 3, 2]
        values = [12, 10, 20, 15]

        self.assertEqual(knapsack(weights, values, 5), 37)
        self.assertEqual(knapsack_with_items(weights, values, 5), (37, [0, 1, 3]))

    def test_second_documented_example(self) -> None:
        self.assertEqual(knapsack([10, 20, 30], [60, 100, 120], 50), 220)

    def test_empty_input_and_zero_capacity(self) -> None:
        self.assertEqual(knapsack([], [], 0), 0)
        self.assertEqual(knapsack_with_items([1], [9], 0), (0, []))

    def test_negative_values_are_not_selected(self) -> None:
        self.assertEqual(knapsack([1, 2], [-1, -2], 2), 0)

    def test_rejects_mismatched_lengths(self) -> None:
        with self.assertRaisesRegex(ValueError, "same length"):
            knapsack([1, 2], [10], 2)

    def test_rejects_negative_capacity(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-negative"):
            knapsack([1], [10], -1)

    def test_rejects_non_positive_weight(self) -> None:
        for invalid_weight in (0, -1):
            with self.subTest(weight=invalid_weight):
                with self.assertRaisesRegex(ValueError, "positive integer"):
                    knapsack([invalid_weight], [10], 2)


if __name__ == "__main__":
    unittest.main()
