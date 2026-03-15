# -*- coding: utf-8 -*-
"""
地面小车：接收无人机下发的火源坐标，避障行驶至火源附近并执行灭火。
"""
import heapq
from typing import List, Tuple, Optional
from dataclasses import dataclass

try:
    import config as cfg
except ImportError:
    cfg = None

from ..comm import CommChannel, FireReport
from ..scene import ObstacleGrid

SPEED = getattr(cfg, "VEHICLE_SPEED", 3.0) if cfg else 3.0
RADIUS = getattr(cfg, "VEHICLE_RADIUS", 12) if cfg else 12
ACTION_RADIUS = getattr(cfg, "FIRE_ACTION_RADIUS", 40) if cfg else 40
ACTION_DURATION = getattr(cfg, "FIRE_ACTION_DURATION", 60) if cfg else 60


@dataclass
class VehicleState:
    x: float
    y: float
    target_x: Optional[float] = None
    target_y: Optional[float] = None
    path: List[Tuple[int, int]] = None
    path_index: int = 0
    extinguishing: bool = False
    extinguish_countdown: int = 0
    current_fire: Optional[Tuple[float, float]] = None  # 当前正在灭的火源坐标

    def __post_init__(self):
        if self.path is None:
            self.path = []


def _neighbors(gx: int, gy: int, grid: ObstacleGrid) -> List[Tuple[int, int]]:
    nx, ny = grid.grid.shape[1], grid.grid.shape[0]
    out = []
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
        ngx, ngy = gx + dx, gy + dy
        if 0 <= ngx < nx and 0 <= ngy < ny and grid.grid[ngy, ngx] == 0:
            out.append((ngx, ngy))
    return out


def astar_path(
    start_xy: Tuple[float, float],
    goal_xy: Tuple[float, float],
    obstacles: ObstacleGrid,
) -> List[Tuple[int, int]]:
    """A* 在栅格上规划路径，返回栅格坐标序列。"""
    cell = obstacles.cell_size
    gx0, gy0 = obstacles.world_to_grid(int(start_xy[0]), int(start_xy[1]))
    gx1, gy1 = obstacles.world_to_grid(int(goal_xy[0]), int(goal_xy[1]))
    if obstacles.grid[gy0, gx0] == 1 or obstacles.grid[gy1, gx1] == 1:
        return []
    open_set = [(0, (gx0, gy0))]
    came_from = {}
    g_score = {(gx0, gy0): 0}
    while open_set:
        _, (gx, gy) = heapq.heappop(open_set)
        if (gx, gy) == (gx1, gy1):
            path = []
            cur = (gx, gy)
            while cur in came_from:
                path.append(cur)
                cur = came_from[cur]
            path.append((gx0, gy0))
            path.reverse()
            return path
        for ng in _neighbors(gx, gy, obstacles):
            cost = 1.414 if (ng[0] - gx) != 0 and (ng[1] - gy) != 0 else 1.0
            tg = g_score[(gx, gy)] + cost
            if ng not in g_score or tg < g_score[ng]:
                g_score[ng] = tg
                th = abs(ng[0] - gx1) + abs(ng[1] - gy1)
                heapq.heappush(open_set, (tg + th, ng))
                came_from[ng] = (gx, gy)
    return []


class GroundVehicle:
    """
    小车逻辑：从 channel 接收火源坐标，A* 寻路，移动到火源附近后灭火。
    """
    def __init__(self, channel: CommChannel, obstacles: ObstacleGrid, world_bounds: Tuple[int, int]):
        self.channel = channel
        self.obstacles = obstacles
        self.w, self.h = world_bounds
        self.state = VehicleState(x=50.0, y=50.0)  # 初始位置

    def _clamp(self, x: float, y: float) -> Tuple[float, float]:
        x = max(RADIUS, min(self.w - RADIUS, x))
        y = max(RADIUS, min(self.h - RADIUS, y))
        return x, y

    def update(self, world_fires_extinguish_callback=None) -> None:
        """
        每帧调用：收报文、寻路、移动、灭火。
        world_fires_extinguish_callback: 回调 (fire_x, fire_y) 通知世界将该火源标记为已灭。
        """
        s = self.state
        if s.extinguishing:
            s.extinguish_countdown -= 1
            if s.extinguish_countdown <= 0:
                if world_fires_extinguish_callback and s.current_fire:
                    world_fires_extinguish_callback(s.current_fire[0], s.current_fire[1])
                s.extinguishing = False
                s.current_fire = None
                s.target_x = s.target_y = None
                s.path = []
                s.path_index = 0
            return

        report = self.channel.receive()
        if report is not None and (s.target_x is None or s.target_y is None):
            s.target_x, s.target_y = report.world_x, report.world_y
            s.current_fire = (report.world_x, report.world_y)
            s.path = astar_path((s.x, s.y), (s.target_x, s.target_y), self.obstacles)
            s.path_index = 0

        if s.target_x is not None and s.target_y is not None:
            dist = ((s.x - s.target_x) ** 2 + (s.y - s.target_y) ** 2) ** 0.5
            if dist <= ACTION_RADIUS:
                s.extinguishing = True
                s.extinguish_countdown = ACTION_DURATION
                return
            if s.path and s.path_index < len(s.path):
                gx, gy = s.path[s.path_index]
                wx, wy = self.obstacles.grid_to_world(gx, gy)
                dx, dy = wx - s.x, wy - s.y
                d = (dx * dx + dy * dy) ** 0.5
                if d > 0:
                    step = min(SPEED, d)
                    s.x, s.y = self._clamp(s.x + dx * step / d, s.y + dy * step / d)
                if d <= SPEED * 1.5:
                    s.path_index = min(s.path_index + 1, len(s.path) - 1)
            else:
                dx = s.target_x - s.x
                dy = s.target_y - s.y
                d = (dx * dx + dy * dy) ** 0.5
                if d > 0 and d > ACTION_RADIUS:
                    step = min(SPEED, d - ACTION_RADIUS)
                    nx = s.x + dx * step / d
                    ny = s.y + dy * step / d
                    if not self.obstacles.is_blocked(int(nx), int(ny)):
                        s.x, s.y = self._clamp(nx, ny)

    @property
    def position(self) -> Tuple[float, float]:
        return self.state.x, self.state.y

    @property
    def is_extinguishing(self) -> bool:
        return self.state.extinguishing
