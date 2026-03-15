# -*- coding: utf-8 -*-
"""
2D 俯视世界：地图、火源、障碍物、无人机视角画面。
纯软件模拟，所有坐标为像素（世界坐标系）。
"""
import cv2
import numpy as np
import random
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

try:
    import config as cfg
except ImportError:
    cfg = None

if cfg is None:
    WORLD_W, WORLD_H = 800, 600
    OBSTACLE_CELL = 20
    OBSTACLE_DENSITY = 0.08
else:
    WORLD_W = getattr(cfg, "WORLD_WIDTH", 800)
    WORLD_H = getattr(cfg, "WORLD_HEIGHT", 600)
    OBSTACLE_CELL = getattr(cfg, "OBSTACLE_CELL_SIZE", 20)
    OBSTACLE_DENSITY = getattr(cfg, "OBSTACLE_DENSITY", 0.08)


@dataclass
class FireSource:
    """火源：红色光斑或发热物体模拟。"""
    x: float
    y: float
    radius: int = 25
    extinguished: bool = False  # 被灭火后置 True
    intensity: float = 1.0      # 0~1，灭火过程中可逐渐减小


@dataclass
class ObstacleGrid:
    """栅格障碍物。"""
    grid: np.ndarray  # (ny, nx) 0=可通行 1=障碍
    cell_size: int
    world_w: int
    world_h: int

    def is_blocked(self, px: int, py: int) -> bool:
        if px < 0 or py < 0 or px >= self.world_w or py >= self.world_h:
            return True
        gx, gy = px // self.cell_size, py // self.cell_size
        nx, ny = self.grid.shape[1], self.grid.shape[0]
        if gx >= nx or gy >= ny:
            return False
        return self.grid[gy, gx] == 1

    def world_to_grid(self, px: int, py: int) -> Tuple[int, int]:
        return px // self.cell_size, py // self.cell_size

    def grid_to_world(self, gx: int, gy: int) -> Tuple[int, int]:
        return gx * self.cell_size + self.cell_size // 2, gy * self.cell_size + self.cell_size // 2


def _build_random_obstacles(w: int, h: int, cell: int, density: float) -> np.ndarray:
    nx, ny = w // cell, h // cell
    grid = np.zeros((ny, nx), dtype=np.uint8)
    n_obst = int(nx * ny * density)
    for _ in range(n_obst):
        gx, gy = random.randint(0, nx - 1), random.randint(0, ny - 1)
        grid[gy, gx] = 1
    return grid


class World:
    """俯视 2D 世界：绘制地图、火源、障碍物，并生成无人机“看到”的俯视图。"""
    def __init__(self, width: int = None, height: int = None, seed: int = None):
        self.w = width or WORLD_W
        self.h = height or WORLD_H
        if seed is not None:
            random.seed(seed)
        self.fires: List[FireSource] = []
        self.obstacles = ObstacleGrid(
            _build_random_obstacles(self.w, self.h, OBSTACLE_CELL, OBSTACLE_DENSITY),
            OBSTACLE_CELL, self.w, self.h
        )
        self._base_map: Optional[np.ndarray] = None  # 仅障碍物底图，缓存

    def add_fire(self, x: float, y: float, radius: int = 25) -> FireSource:
        f = FireSource(x=x, y=y, radius=radius)
        self.fires.append(f)
        return f

    def add_fire_random(self, margin: int = 80) -> FireSource:
        x = random.randint(margin, self.w - margin)
        y = random.randint(margin, self.h - margin)
        return self.add_fire(x, y)

    def get_active_fires(self) -> List[FireSource]:
        return [f for f in self.fires if not f.extinguished]

    def _draw_base_map(self) -> np.ndarray:
        if self._base_map is not None:
            return self._base_map.copy()
        img = np.ones((self.h, self.w, 3), dtype=np.uint8) * 240  # 浅灰地面
        cell = self.obstacles.cell_size
        grid = self.obstacles.grid
        for gy in range(grid.shape[0]):
            for gx in range(grid.shape[1]):
                if grid[gy, gx] == 1:
                    x1, y1 = gx * cell, gy * cell
                    cv2.rectangle(img, (x1, y1), (x1 + cell - 1, y1 + cell - 1), (80, 80, 80), -1)
        self._base_map = img
        return self._base_map.copy()

    def render(self, vehicle_xy: Tuple[float, float] = None, uav_xy: Tuple[float, float] = None) -> np.ndarray:
        """渲染完整俯视图（含火源、小车、无人机位置）。"""
        frame = self._draw_base_map()
        for f in self.fires:
            if f.extinguished:
                cv2.circle(frame, (int(f.x), int(f.y)), f.radius, (100, 100, 100), -1)
                cv2.putText(frame, "X", (int(f.x) - 8, int(f.y) + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 80, 80), 2)
            else:
                color = (0, 0, min(255, int(150 + 105 * f.intensity)))
                cv2.circle(frame, (int(f.x), int(f.y)), f.radius, color, -1)
                cv2.circle(frame, (int(f.x), int(f.y)), f.radius, (0, 0, 255), 2)
        if vehicle_xy:
            vx, vy = int(vehicle_xy[0]), int(vehicle_xy[1])
            cv2.circle(frame, (vx, vy), 14, (0, 180, 0), -1)
            cv2.circle(frame, (vx, vy), 14, (0, 255, 0), 2)
            cv2.putText(frame, "Car", (vx - 12, vy - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 120, 0), 1)
        if uav_xy:
            ux, uy = int(uav_xy[0]), int(uav_xy[1])
            cv2.circle(frame, (ux, uy), 10, (255, 200, 0), -1)
            cv2.circle(frame, (ux, uy), 10, (0, 165, 255), 2)
            cv2.putText(frame, "UAV", (ux - 14, uy - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 100, 200), 1)
        return frame

    def get_uav_view(self, vehicle_xy=None, uav_xy=None) -> np.ndarray:
        """无人机“上帝视角”看到的画面（即整张俯视图，用于火源检测）。"""
        return self.render(vehicle_xy=vehicle_xy, uav_xy=uav_xy)
