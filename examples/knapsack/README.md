# 0/1 背包问题示例

此目录保存 Coding Agent 生成并经人工修正后的 0/1 背包示例，不修改项目根 README。

## 问题

给定容量为 `W` 的背包和 `n` 个物品。每个物品有重量 `weights[i]` 和价值 `values[i]`，且最多选择一次。目标是在总重量不超过 `W` 的条件下最大化总价值。

动态规划状态 `dp[i][w]` 表示只考虑前 `i` 个物品、容量为 `w` 时的最大价值：

```text
物品 i 放不下：dp[i][w] = dp[i-1][w]
物品 i 放得下：dp[i][w] = max(dp[i-1][w], dp[i-1][w-weight] + value)
```

- 时间复杂度：`O(nW)`
- 空间复杂度：`O(nW)`，保留二维表是为了回溯选中的物品

## 运行

```bash
conda run -n agent python examples/knapsack/knapsack_problem.py
conda run -n agent python -m unittest -v examples.knapsack.test_knapsack_problem
```

`knapsack()` 返回最大价值；`knapsack_with_items()` 还返回从零开始的物品索引。实现会拒绝负容量、非正整数重量以及长度不一致的输入。
