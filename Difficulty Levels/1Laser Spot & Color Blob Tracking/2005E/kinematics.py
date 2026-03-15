# -*- coding: utf-8 -*-
"""
2005 E题 悬挂运动控制系统 - 双拉线几何与正逆解
坐标: 板面 80cm×100cm, 原点左下角, x向右, y向上
左电机 (0, HEIGHT), 右电机 (WIDTH, HEIGHT)
"""
import math
from typing import Tuple

# 板面尺寸 (cm)
BOARD_WIDTH = 80.0
BOARD_HEIGHT = 100.0

# 电机安装位置 (左上、右上)
LEFT_MOTOR = (0.0, BOARD_HEIGHT)
RIGHT_MOTOR = (BOARD_WIDTH, BOARD_HEIGHT)


def inverse_kinematics(x: float, y: float) -> Tuple[float, float]:
    """
    逆解: 给定画笔坐标 (x, y)，求左右拉线长度 L1, L2。
    L1 = 左电机到笔的距离, L2 = 右电机到笔的距离
    """
    lx, ly = LEFT_MOTOR
    rx, ry = RIGHT_MOTOR
    L1 = math.sqrt((x - lx) ** 2 + (y - ly) ** 2)
    L2 = math.sqrt((x - rx) ** 2 + (y - ry) ** 2)
    return (L1, L2)


def forward_kinematics(L1: float, L2: float) -> Tuple[float, float]:
    """
    正解: 给定左右拉线长度 L1, L2，求画笔坐标 (x, y)。
    两圆交点：圆心为左右电机，半径分别为 L1, L2。
    """
    lx, ly = LEFT_MOTOR
    rx, ry = RIGHT_MOTOR
    d = rx - lx  # 两电机水平距离
    if d <= 0:
        return (lx, ly)
    # 以左电机为原点时: x^2 + y^2 = L1^2, (d-x)^2 + y^2 = L2^2
    # 相减: d^2 - 2*d*x = L2^2 - L1^2  =>  x = (d^2 + L1^2 - L2^2) / (2*d)
    x_local = (d * d + L1 * L1 - L2 * L2) / (2.0 * d)
    yy = L1 * L1 - x_local * x_local
    if yy < 0:
        yy = 0  # 浮点误差
    y_local = math.sqrt(yy)
    # 取交点在下半平面 (y 向下为正时取 -y_local，本题 y 向上，取正)
    x = lx + x_local
    y = ly - y_local  # 电机在上，笔在下，故 ly - y_local
    return (x, y)


def xy_to_string_lengths(x: float, y: float) -> Tuple[float, float]:
    """逆解别名，与题目表述一致。"""
    return inverse_kinematics(x, y)


def string_lengths_to_xy(L1: float, L2: float) -> Tuple[float, float]:
    """正解别名。"""
    return forward_kinematics(L1, L2)


def check_workspace(x: float, y: float) -> bool:
    """检查 (x,y) 是否在板面范围内。"""
    return 0 <= x <= BOARD_WIDTH and 0 <= y <= BOARD_HEIGHT


def get_max_reachable():
    """理论可达范围：两拉线都绷直时的交集。简化返回板面矩形。"""
    return (0, 0, BOARD_WIDTH, BOARD_HEIGHT)
