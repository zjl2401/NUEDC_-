# -*- coding: utf-8 -*-
"""2025E 控制模块：双轴 PID、Kalman 预测、利萨如图形轨迹生成"""

import numpy as np
from typing import Tuple
import config as cfg


class PIDController:
    """增量式 PID，输出为增量。"""

    def __init__(self, kp=None, ki=None, kd=None, max_out=None, deadzone=None):
        self.kp = kp if kp is not None else cfg.PID_KP
        self.ki = ki if ki is not None else cfg.PID_KI
        self.kd = kd if kd is not None else cfg.PID_KD
        self.max_out = max_out if max_out is not None else cfg.PID_MAX_OUTPUT
        self.deadzone = deadzone if deadzone is not None else cfg.DEADZONE_PX
        self._last_error = 0.0
        self._integral = 0.0

    def update(self, error: float, dt: float = 1.0) -> float:
        if abs(error) <= self.deadzone:
            return 0.0
        self._integral += error * dt
        self._integral = np.clip(self._integral, -150, 150)
        derivative = (error - self._last_error) / dt if dt > 0 else 0.0
        self._last_error = error
        out = self.kp * error + self.ki * self._integral + self.kd * derivative
        return np.clip(out, -self.max_out, self.max_out)

    def reset(self) -> None:
        self._last_error = 0.0
        self._integral = 0.0


class TrackerController:
    """双轴追踪：(current_x, current_y) 追 (target_x, target_y)，输出像素增量。"""

    def __init__(self):
        self.pid_x = PIDController()
        self.pid_y = PIDController()

    def update(
        self,
        target_x: float,
        target_y: float,
        current_x: float,
        current_y: float,
        dt: float = 1.0,
    ) -> Tuple[float, float]:
        err_x = target_x - current_x
        err_y = target_y - current_y
        out_x = self.pid_x.update(err_x, dt)
        out_y = self.pid_y.update(err_y, dt)
        return (out_x, out_y)

    def reset(self) -> None:
        self.pid_x.reset()
        self.pid_y.reset()


class KalmanPredictor:
    """二维位置 Kalman 滤波 + 一步预测，用于遮挡/闪烁时保持轨迹平滑。"""

    def __init__(self, process_noise=None, measure_noise=None):
        q = process_noise if process_noise is not None else cfg.KALMAN_PROCESS_NOISE
        r = measure_noise if measure_noise is not None else cfg.KALMAN_MEASURE_NOISE
        # 状态 [x, y, vx, vy]，观测 [x, y]
        self.F = np.array([
            [1, 0, 1, 0],
            [0, 1, 0, 1],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ], dtype=np.float64)
        self.H = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
        ], dtype=np.float64)
        self.Q = np.eye(4, dtype=np.float64) * q
        self.R = np.eye(2, dtype=np.float64) * r
        self.P = np.eye(4, dtype=np.float64) * 1.0
        self.x = np.zeros(4, dtype=np.float64)
        self._initialized = False

    def update(self, x_meas: float, y_meas: float) -> Tuple[float, float]:
        z = np.array([x_meas, y_meas], dtype=np.float64)
        if not self._initialized:
            self.x = np.array([z[0], z[1], 0.0, 0.0], dtype=np.float64)
            self._initialized = True
            return (float(z[0]), float(z[1]))
        # 预测
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
        # 更新
        y = z - self.H @ self.x
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        self.P = (np.eye(4) - K @ self.H) @ self.P
        # 一步预测位置（下一帧）
        x_next = self.F @ self.x
        return (float(x_next[0]), float(x_next[1]))

    def predict_only(self) -> Tuple[float, float]:
        """无观测时仅用状态方程预测。"""
        if not self._initialized:
            return (0.0, 0.0)
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
        return (float(self.x[0]), float(self.x[1]))

    def reset(self) -> None:
        self._initialized = False
        self.P = np.eye(4, dtype=np.float64) * 1.0


def lissajous_xy(t: float) -> Tuple[float, float]:
    """利萨如图形：x = A*sin(a*t+d), y = B*sin(b*t)。中心为画布中心。"""
    cx = cfg.CANVAS_W / 2
    cy = cfg.CANVAS_H / 2
    x = cx + cfg.LISSAJOUS_A * np.sin(cfg.LISSAJOUS_A_FREQ * t + cfg.LISSAJOUS_PHASE)
    y = cy + cfg.LISSAJOUS_B * np.sin(cfg.LISSAJOUS_B_FREQ * t)
    return (float(x), float(y))


def circle_xy(t: float, cx: float, cy: float, radius: float, speed: float) -> Tuple[float, float]:
    """圆周轨迹。"""
    x = cx + radius * np.cos(t * speed)
    y = cy + radius * np.sin(t * speed)
    return (float(x), float(y))


def figure8_xy(t: float, cx: float, cy: float, scale: float, speed: float) -> Tuple[float, float]:
    """8 字形。"""
    x = cx + scale * np.sin(t * speed)
    y = cy + scale * 0.5 * np.sin(2 * t * speed)
    return (float(x), float(y))
