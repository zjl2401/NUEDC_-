"""
纯软件仿真：模拟场地、巡线传感器、摄像头画面与差速运动。
无需硬件即可在 PC 上运行完整逻辑与视觉算法。
"""
from __future__ import annotations

import math
from typing import List, Tuple, Optional

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

# 场地单位：米
LINE_WIDTH = 0.02
SENSOR_SPACING = 0.01
SENSOR_FRONT_DIST = 0.03
ROBOT_WHEEL_BASE = 0.05
SPEED_SCALE = 0.15
ROOM_NEAR_DIST = 0.08
JUNCTION_RADIUS = 0.06
# 摄像头模拟：视野范围（米）
CAM_WIDTH_M = 0.5
CAM_HEIGHT_M = 0.4
CAM_IMG_W = 640
CAM_IMG_H = 480


def _point_to_segment_dist(px: float, py: float,
                           x1: float, y1: float, x2: float, y2: float) -> float:
    """点到线段的最短距离。"""
    dx, dy = x2 - x1, y2 - y1
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / length_sq))
    nx = x1 + t * dx
    ny = y1 + t * dy
    return math.hypot(px - nx, py - ny)


class SimTrack:
    """仿真赛道：折线路径 + 房间与路口标记。"""

    def __init__(self) -> None:
        # 路径：折线顶点 (x, y)，单位米
        self.path: List[Tuple[float, float]] = []
        # 房间：(路径段索引, 该段内比例 0~1, 房号)
        self.rooms: List[Tuple[int, float, int]] = []
        # 路口：(路径段索引, 该段内比例)
        self.junctions: List[Tuple[int, float]] = []
        self._build_default_track()

    def _build_default_track(self) -> None:
        """默认赛道：起点 -> 直道 -> 路口 -> 直道 -> 1号房 -> 直道 -> 2号房。"""
        # 折线：每段 0.2m
        self.path = [
            (0.0, 0.5),
            (0.2, 0.5),
            (0.4, 0.5),
            (0.6, 0.5),
            (0.8, 0.5),
            (1.0, 0.5),
            (1.0, 0.3),
            (1.0, 0.1),
            (1.0, -0.1),
            (1.2, -0.1),
            (1.4, -0.1),
            (1.6, -0.1),
        ]
        self.rooms = [
            (5, 0.5, 1),
            (11, 0.5, 2),
        ]
        self.junctions = [
            (4, 0.5),
        ]

    def path_segment(self, i: int) -> Tuple[float, float, float, float]:
        if i < 0 or i >= len(self.path) - 1:
            return 0, 0, 0, 0
        x1, y1 = self.path[i]
        x2, y2 = self.path[i + 1]
        return x1, y1, x2, y2

    def distance_to_path(self, x: float, y: float) -> float:
        d = 1e9
        for i in range(len(self.path) - 1):
            x1, y1, x2, y2 = self.path_segment(i)
            d = min(d, _point_to_segment_dist(x, y, x1, y1, x2, y2))
        return d

    def nearest_room(self, x: float, y: float) -> Optional[Tuple[int, float, float]]:
        """返回 (房号, 距离, 该段索引)。"""
        best: Optional[Tuple[int, float, float]] = None
        for i in range(len(self.path) - 1):
            x1, y1, x2, y2 = self.path_segment(i)
            for room_idx, t_ratio, room_num in self.rooms:
                if room_idx != i:
                    continue
                rx = x1 + t_ratio * (x2 - x1)
                ry = y1 + t_ratio * (y2 - y1)
                dist = math.hypot(x - rx, y - ry)
                if dist < ROOM_NEAR_DIST and (best is None or dist < best[1]):
                    best = (room_num, dist, float(i))
        return best

    def at_junction(self, x: float, y: float) -> bool:
        for seg_i, t_ratio in self.junctions:
            x1, y1, x2, y2 = self.path_segment(seg_i)
            jx = x1 + t_ratio * (x2 - x1)
            jy = y1 + t_ratio * (y2 - y1)
            if math.hypot(x - jx, y - jy) < JUNCTION_RADIUS:
                return True
        return False


class Simulator:
    """纯软件仿真器：差速运动 + 巡线传感器 + 模拟摄像头画面。"""

    def __init__(self, track: Optional[SimTrack] = None) -> None:
        self.track = track or SimTrack()
        self.x = 0.1
        self.y = 0.5
        self.theta = 0.0
        self._last_left = 0.0
        self._last_right = 0.0
        self._last_time: Optional[float] = None

    def set_wheel_speeds(self, left: float, right: float) -> None:
        self._last_left = left
        self._last_right = right

    def step(self, dt: float) -> None:
        v = (self._last_left + self._last_right) / 2.0 * SPEED_SCALE
        omega = (self._last_right - self._last_left) / 2.0 * SPEED_SCALE / max(0.01, ROBOT_WHEEL_BASE)
        self.x += v * math.cos(self.theta) * dt
        self.y += v * math.sin(self.theta) * dt
        self.theta += omega * dt

    def read_line_sensors(self) -> List[float]:
        """5 路巡线：根据机器人位姿与路径计算哪几路压线。"""
        half = (5 - 1) / 2.0 * SENSOR_SPACING
        values = []
        for i in range(5):
            offset = (i - 2) * SENSOR_SPACING
            nx = -math.sin(self.theta) * offset + math.cos(self.theta) * SENSOR_FRONT_DIST
            ny = math.cos(self.theta) * offset + math.sin(self.theta) * SENSOR_FRONT_DIST
            sx = self.x + nx
            sy = self.y + ny
            d = self.track.distance_to_path(sx, sy)
            on_line = 1.0 if d <= LINE_WIDTH / 2 else 0.0
            values.append(on_line)
        if self.track.at_junction(self.x, self.y):
            values = [1.0, 1.0, 1.0, 1.0, 0.5]
        return values

    def read_frame(self) -> Optional["np.ndarray"]:
        """生成模拟摄像头图像：前方地面 + 黑线 + 房号与红线（若在房间附近）。"""
        if cv2 is None:
            return None
        img = np.ones((CAM_IMG_H, CAM_IMG_W, 3), dtype=np.uint8) * 255
        # 机器人坐标系：前方 +X，左侧 +Y。视野 X in [0, CAM_HEIGHT_M], Y in [-CAM_WIDTH_M/2, CAM_WIDTH_M/2]
        def world_to_robot(wx: float, wy: float) -> Tuple[float, float]:
            dx = wx - self.x
            dy = wy - self.y
            rx = dx * math.cos(self.theta) + dy * math.sin(self.theta)
            ry = -dx * math.sin(self.theta) + dy * math.cos(self.theta)
            return rx, ry

        def robot_to_img(rx: float, ry: float) -> Tuple[int, int]:
            if rx < 0 or rx > CAM_HEIGHT_M:
                return -1, -1
            if ry < -CAM_WIDTH_M / 2 or ry > CAM_WIDTH_M / 2:
                return -1, -1
            ix = int((ry + CAM_WIDTH_M / 2) / CAM_WIDTH_M * CAM_IMG_W)
            iy = int((CAM_HEIGHT_M - rx) / CAM_HEIGHT_M * CAM_IMG_H)
            return ix, iy

        for i in range(len(self.track.path) - 1):
            x1, y1, x2, y2 = self.track.path_segment(i)
            r1x, r1y = world_to_robot(x1, y1)
            r2x, r2y = world_to_robot(x2, y2)
            i1x, i1y = robot_to_img(r1x, r1y)
            i2x, i2y = robot_to_img(r2x, r2y)
            if 0 <= i1x < CAM_IMG_W and 0 <= i1y < CAM_IMG_H and 0 <= i2x < CAM_IMG_W and 0 <= i2y < CAM_IMG_H:
                cv2.line(img, (i1x, i1y), (i2x, i2y), (0, 0, 0), 12)

        room_info = self.track.nearest_room(self.x, self.y)
        if room_info is not None:
            room_num, _, _ = room_info
            cv2.rectangle(img, (CAM_IMG_W // 4, CAM_IMG_H // 2 - 40),
                          (CAM_IMG_W * 3 // 4, CAM_IMG_H // 2 + 40), (0, 0, 255), -1)
            cv2.putText(img, str(room_num), (CAM_IMG_W // 2 - 25, CAM_IMG_H // 2 + 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 2.0, (255, 255, 255), 3)
        return img

    def get_pose(self) -> Tuple[float, float, float]:
        return self.x, self.y, self.theta

    def reset(self, x: float = 0.1, y: float = 0.5, theta: float = 0.0) -> None:
        self.x, self.y, self.theta = x, y, theta


def draw_track_top_down(track: SimTrack, robot_xy: Tuple[float, float],
                        robot_theta: float, size: int = 400) -> Optional["np.ndarray"]:
    """绘制俯视图：赛道 + 机器人位置，用于仿真窗口。"""
    if cv2 is None:
        return None
    scale = size / 2.0
    cx, cy = size // 2, size // 2
    img = np.ones((size, size, 3), dtype=np.uint8) * 240
    for i in range(len(track.path) - 1):
        x1, y1, x2, y2 = track.path_segment(i)
        pt1 = (int(cx + x1 * scale), int(cy - y1 * scale))
        pt2 = (int(cx + x2 * scale), int(cy - y2 * scale))
        cv2.line(img, pt1, pt2, (0, 0, 0), 4)
    rx, ry = robot_xy
    px = int(cx + rx * scale)
    py = int(cy - ry * scale)
    cv2.circle(img, (px, py), 8, (0, 165, 255), -1)
    dx = 15 * math.cos(robot_theta)
    dy = -15 * math.sin(robot_theta)
    cv2.arrowedLine(img, (px, py), (int(px + dx), int(py + dy)), (0, 165, 255), 2)
    return img
