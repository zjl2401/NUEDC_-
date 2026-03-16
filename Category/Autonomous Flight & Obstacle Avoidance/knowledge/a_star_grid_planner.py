"""
基于 2D 占据栅格的 A* 路径规划示例

输入:
    - 占据栅格: 0=空闲, 1=障碍, -1=未知
    - 起点/终点栅格坐标 (sx, sy), (gx, gy)

中间操作:
    1. 在 4/8 邻域上进行 A* 搜索
    2. 使用曼哈顿/欧氏距离作为启发式

输出:
    - 栅格路径点列表 [(x0, y0), (x1, y1), ...]
"""

import heapq
from typing import Dict, List, Optional, Tuple

import numpy as np


GridIndex = Tuple[int, int]


def heuristic(a: GridIndex, b: GridIndex) -> float:
    return float(abs(a[0] - b[0]) + abs(a[1] - b[1]))


def a_star(
    grid: np.ndarray,
    start: GridIndex,
    goal: GridIndex,
    allow_diagonal: bool = False,
) -> Optional[List[GridIndex]]:
    h, w = grid.shape

    def in_bounds(p: GridIndex) -> bool:
        x, y = p
        return 0 <= x < w and 0 <= y < h

    def passable(p: GridIndex) -> bool:
        x, y = p
        return grid[y, x] == 0  # 仅空闲格可通过

    if allow_diagonal:
        neighbors_delta = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)]
    else:
        neighbors_delta = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    open_set: List[Tuple[float, GridIndex]] = []
    heapq.heappush(open_set, (0.0, start))

    came_from: Dict[GridIndex, Optional[GridIndex]] = {start: None}
    g_score: Dict[GridIndex, float] = {start: 0.0}

    while open_set:
        _, current = heapq.heappop(open_set)
        if current == goal:
            # 回溯路径
            path: List[GridIndex] = []
            cur = current
            while cur is not None:
                path.append(cur)
                cur = came_from[cur]
            path.reverse()
            return path

        for dx, dy in neighbors_delta:
            nx, ny = current[0] + dx, current[1] + dy
            neighbor = (nx, ny)
            if not in_bounds(neighbor) or not passable(neighbor):
                continue

            new_g = g_score[current] + 1.0
            if neighbor not in g_score or new_g < g_score[neighbor]:
                g_score[neighbor] = new_g
                f = new_g + heuristic(neighbor, goal)
                heapq.heappush(open_set, (f, neighbor))
                came_from[neighbor] = current

    return None


if __name__ == "__main__":
    # 使用一个简单的虚拟栅格演示 A* 路径
    grid = np.zeros((10, 10), dtype=np.int8)
    grid[4, 2:8] = 1  # 中间一堵墙

    start = (1, 1)
    goal = (8, 8)

    path = a_star(grid, start, goal, allow_diagonal=False)
    print("规划出的路径:", path)

