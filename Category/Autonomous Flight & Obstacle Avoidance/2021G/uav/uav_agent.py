# -*- coding: utf-8 -*-
"""
2021G 植保飞行器 - 无人机逻辑
起飞 → 寻 A（作业起点）→ 全覆盖路径规划与播撒 → 返回起降点并降落。
纯软件模拟：位置为 (x,y)，无真实高度；用“状态 + 路径点”驱动。
"""

import math
import config as cfg
from scene.world import get_cell_center


class UAVState:
    TAKEOFF = "takeoff"
    CRUISE_TO_A = "cruise_to_a"
    SPRAYING = "spraying"
    RETURN = "return"
    LAND = "land"
    DONE = "done"


class UAVAgent:
    def __init__(self):
        self.x = float(cfg.CROSS_CENTER_X)
        self.y = float(cfg.CROSS_CENTER_Y)
        self.state = UAVState.TAKEOFF
        self.path = []           # 待飞行的 (x,y) 路径点
        self.sprayed_cells = set()  # 已播撒的 (row,col)
        self.a_cell = None       # (row, col) 作业起点
        self.green_cells = []    # 全部绿色区块 (row,col)
        self.speed = 3.0         # 像素/帧
        self.landing_ok = False

    def set_mission(self, a_cell, green_cells):
        """设置作业起点 A 与所有绿色区块。"""
        self.a_cell = a_cell
        self.green_cells = list(green_cells)
        self.sprayed_cells = set()

    def _dist(self, x1, y1, x2, y2):
        return math.hypot(x2 - x1, y2 - y1)

    def _move_toward(self, tx, ty):
        dx = tx - self.x
        dy = ty - self.y
        d = self._dist(self.x, self.y, tx, ty)
        if d <= self.speed:
            self.x, self.y = tx, ty
            return True
        self.x += dx / d * self.speed
        self.y += dy / d * self.speed
        return False

    def update(self, full_map, detector_module):
        """
        每帧更新：根据状态机移动或切换状态。
        detector_module: vision.detector，用于在 UAV 视野内做识别（本模拟可省略，直接用已知网格）
        """
        if self.state == UAVState.TAKEOFF:
            self.state = UAVState.CRUISE_TO_A
            if self.a_cell is not None:
                cx, cy = get_cell_center(self.a_cell[0], self.a_cell[1])
                self.path = [(cx, cy)]

        if self.state == UAVState.CRUISE_TO_A and self.path:
            tx, ty = self.path[0]
            if self._move_toward(tx, ty):
                self.path.pop(0)
                if not self.path:
                    self.state = UAVState.SPRAYING
                    self._build_spray_path()

        if self.state == UAVState.SPRAYING:
            self._update_spraying()

        if self.state == UAVState.RETURN and self.path:
            tx, ty = self.path[0]
            if self._move_toward(tx, ty):
                self.path.pop(0)
                if not self.path:
                    self.state = UAVState.LAND

        if self.state == UAVState.LAND:
            if self._move_toward(cfg.CROSS_CENTER_X, cfg.CROSS_CENTER_Y):
                d = self._dist(self.x, self.y, cfg.CROSS_CENTER_X, cfg.CROSS_CENTER_Y)
                self.landing_ok = d <= cfg.LANDING_ERROR_THRESHOLD_PX
                self.state = UAVState.DONE

    def _build_spray_path(self):
        """按顺序生成所有绿色区块中心为路径点（简单行扫）。"""
        self.path = []
        for (r, c) in self.green_cells:
            cx, cy = get_cell_center(r, c)
            self.path.append((cx, cy))

    def _update_spraying(self):
        """飞向当前路径点，到达则标记该区块已播撒并取下一点。"""
        if not self.path:
            self.state = UAVState.RETURN
            self.path = [(cfg.CROSS_CENTER_X, cfg.CROSS_CENTER_Y)]
            return
        tx, ty = self.path[0]
        if self._move_toward(tx, ty):
            self.path.pop(0)
            for (r, c) in self.green_cells:
                cx, cy = get_cell_center(r, c)
                if self._dist(self.x, self.y, cx, cy) < cfg.CELL_SIZE // 2:
                    self.sprayed_cells.add((r, c))
                    break
