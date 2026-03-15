# -*- coding: utf-8 -*-
"""
2005 E题 - 轨迹规划：直线、圆、正方形、任意曲线，匀速插补
"""
import math
from typing import List, Tuple, Callable, Optional
from kinematics import inverse_kinematics, check_workspace, BOARD_WIDTH, BOARD_HEIGHT

Point = Tuple[float, float]


def linear_interpolate(
    start: Point, end: Point, num_steps: int, include_end: bool = True
) -> List[Point]:
    """在 start 与 end 之间均匀插值 num_steps 个点（含/不含终点）。"""
    pts = []
    N = num_steps + (1 if include_end else 0)
    for i in range(N):
        t = i / num_steps if num_steps > 0 else 1.0
        if t > 1.0:
            t = 1.0
        x = start[0] + t * (end[0] - start[0])
        y = start[1] + t * (end[1] - start[1])
        pts.append((x, y))
    return pts


def trajectory_line(
    start: Point, end: Point, speed_cm_s: float = 2.0, dt_s: float = 0.05
) -> List[Point]:
    """从 start 匀速直线运动到 end，速度为 speed_cm_s，时间步 dt_s。"""
    dist = math.sqrt((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2)
    if dist <= 0:
        return [start]
    total_time = dist / speed_cm_s
    num_steps = max(1, int(total_time / dt_s))
    return linear_interpolate(start, end, num_steps)


def trajectory_circle(
    center: Point,
    radius_cm: float,
    speed_cm_s: float = 3.0,
    dt_s: float = 0.05,
    num_points_min: int = 64,
) -> List[Point]:
    """匀速画圆。按角速度换算为线速度，得到采样点。"""
    perimeter = 2.0 * math.pi * radius_cm
    total_time = perimeter / speed_cm_s
    n = max(num_points_min, int(total_time / dt_s))
    pts = []
    for i in range(n + 1):
        theta = 2.0 * math.pi * i / n
        x = center[0] + radius_cm * math.cos(theta)
        y = center[1] + radius_cm * math.sin(theta)
        pts.append((x, y))
    return pts


def trajectory_square(
    center: Point,
    side_cm: float,
    speed_cm_s: float = 2.0,
    dt_s: float = 0.05,
) -> List[Point]:
    """匀速画正方形，从中心偏左下角起，逆时针。"""
    half = side_cm / 2.0
    cx, cy = center
    # 四个顶点：左下、右下、右上、左上、回到左下
    corners = [
        (cx - half, cy - half),
        (cx + half, cy - half),
        (cx + half, cy + half),
        (cx - half, cy + half),
        (cx - half, cy - half),
    ]
    pts = []
    for k in range(4):
        seg = linear_interpolate(
            corners[k], corners[k + 1],
            max(1, int(side_cm / (speed_cm_s * dt_s))),
            include_end=(k < 3),
        )
        pts.extend(seg)
    return pts


def trajectory_arbitrary(
    path: List[Point],
    speed_cm_s: float = 2.0,
    dt_s: float = 0.05,
) -> List[Point]:
    """沿给定路径点匀速运动。每段按直线插补。"""
    if len(path) < 2:
        return path[:]
    out = [path[0]]
    for i in range(len(path) - 1):
        seg = trajectory_line(path[i], path[i + 1], speed_cm_s, dt_s)
        out.extend(seg[1:])  # 避免重复点
    return out


def points_to_string_lengths(points: List[Point]) -> List[Tuple[float, float]]:
    """将轨迹点列转为 (L1, L2) 序列，供电机控制。"""
    return [inverse_kinematics(x, y) for x, y in points]


def validate_trajectory(points: List[Point]) -> Tuple[bool, List[str]]:
    """检查轨迹是否全部在板面内，返回 (是否有效, 错误信息列表)。"""
    errs = []
    for i, (x, y) in enumerate(points):
        if not check_workspace(x, y):
            errs.append(f"点 {i} ({x:.1f}, {y:.1f}) 超出板面")
    return (len(errs) == 0, errs)
