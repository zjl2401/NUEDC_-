"""
循线行驶：稳定跟随地面黑色引导线。
- 输入：多路灰度/红外巡线传感器读数 或 图像中黑线偏差
- 输出：舵机转角 或 左右轮差速（目标速度）
"""
from __future__ import annotations

from typing import Tuple

# 典型：5 路或 7 路红外，读数为 0/1 或灰度值
# 偏差 = 加权中心 - 理论中心，用于 PD/PID


def compute_line_error(sensor_values: list[int | float]) -> float:
    """
    根据多路传感器计算循线偏差。
    :param sensor_values: 从左到右的传感器值，0 为白，1 或大值为黑
    :return: 偏差值，负=线在左，正=线在右，0=居中
    """
    n = len(sensor_values)
    if n == 0:
        return 0.0
    center = (n - 1) / 2.0
    weighted_sum = sum(i * v for i, v in enumerate(sensor_values))
    total = sum(sensor_values)
    if total == 0:
        return 0.0
    actual_center = weighted_sum / total
    return actual_center - center


def pid_line_follow(
    error: float,
    kp: float,
    ki: float,
    kd: float,
    integral: float,
    last_error: float,
    dt: float,
) -> Tuple[float, float, float]:
    """
    循线 PID 计算。
    :return: (输出控制量, 更新后的 integral, 更新后的 last_error)
    """
    integral = integral + error * dt
    derivative = (error - last_error) / dt if dt > 0 else 0.0
    out = kp * error + ki * integral + kd * derivative
    return out, integral, error


def get_wheel_speeds(
    base_speed: float,
    pid_out: float,
    max_diff: float = 0.5,
) -> Tuple[float, float]:
    """
    由 PID 输出得到左右轮速度（差速转向）。
    :param base_speed: 基础线速度
    :param pid_out: 循线 PID 输出，正=需右转（左快右慢）
    :param max_diff: 左右轮最大速度差比例
    :return: (left_speed, right_speed)
    """
    diff = max(-max_diff, min(max_diff, pid_out))
    left = base_speed + diff
    right = base_speed - diff
    return left, right
