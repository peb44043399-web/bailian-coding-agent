"""Dynamic-programming solution for the 0/1 knapsack problem."""

from __future__ import annotations

from collections.abc import Sequence


def _validate_inputs(
    weights: Sequence[int], values: Sequence[int], capacity: int
) -> None:
    if isinstance(capacity, bool) or not isinstance(capacity, int):
        raise TypeError("capacity must be an integer")
    if capacity < 0:
        raise ValueError("capacity must be non-negative")
    if len(weights) != len(values):
        raise ValueError("weights and values must have the same length")
    if any(
        isinstance(weight, bool) or not isinstance(weight, int) or weight <= 0
        for weight in weights
    ):
        raise ValueError("every weight must be a positive integer")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        raise ValueError("every value must be an integer")


def _build_table(
    weights: Sequence[int], values: Sequence[int], capacity: int
) -> list[list[int]]:
    """Return ``dp[i][w]`` for the first *i* items and capacity *w*."""

    _validate_inputs(weights, values, capacity)
    table = [[0] * (capacity + 1) for _ in range(len(weights) + 1)]
    for item_index, (weight, value) in enumerate(zip(weights, values), start=1):
        for current_capacity in range(capacity + 1):
            without_item = table[item_index - 1][current_capacity]
            if weight > current_capacity:
                table[item_index][current_capacity] = without_item
                continue
            with_item = table[item_index - 1][current_capacity - weight] + value
            table[item_index][current_capacity] = max(without_item, with_item)
    return table


def knapsack(weights: Sequence[int], values: Sequence[int], capacity: int) -> int:
    """Return the maximum value obtainable without exceeding ``capacity``."""

    return _build_table(weights, values, capacity)[len(weights)][capacity]


def knapsack_with_items(
    weights: Sequence[int], values: Sequence[int], capacity: int
) -> tuple[int, list[int]]:
    """Return the maximum value and the selected zero-based item indexes."""

    table = _build_table(weights, values, capacity)
    selected: list[int] = []
    remaining_capacity = capacity
    for item_index in range(len(weights), 0, -1):
        if table[item_index][remaining_capacity] == table[item_index - 1][remaining_capacity]:
            continue
        selected.append(item_index - 1)
        remaining_capacity -= weights[item_index - 1]
    selected.reverse()
    return table[len(weights)][capacity], selected


def print_knapsack_solution(
    weights: Sequence[int], values: Sequence[int], capacity: int
) -> None:
    """Print one optimal solution for a small interactive demonstration."""

    maximum_value, selected = knapsack_with_items(weights, values, capacity)
    total_weight = sum(weights[index] for index in selected)
    print(f"背包容量: {capacity}")
    print(f"最大价值: {maximum_value}")
    print(f"选中物品索引: {selected}")
    print(f"总重量: {total_weight}")


if __name__ == "__main__":
    print_knapsack_solution([2, 1, 3, 2], [12, 10, 20, 15], 5)
