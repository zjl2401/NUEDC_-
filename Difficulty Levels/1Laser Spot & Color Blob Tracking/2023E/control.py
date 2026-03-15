# -*- coding: utf-8 -*-
"""控制模块：增量式 PID、死区、线性预测（动态追踪）"""

import numpy as np
from collections import deque
import config as cfg


class PIDController:
    """增量式 PID，输出为增量，便于叠加到舵机当前角度。"""

    def __init__(self, kp: float = None, ki: float = None, kd: float = None, max_out: float = None):
        self.kp = kp if kp is not None else cfg.PID_KP
        self.ki = ki if ki is not None else cfg.PID_KI
        self.kd = kd if kd is not None else cfg.PID_KD
        self.max_out = max_out if max_out is not None else cfg.PID_MAX_OUTPUT
        self.deadzone = cfg.DEADZONE_PX
        self._last_error = 0.0
        self._integral = 0.0

    def update(self, error: float, dt: float = 1.0) -> float:
        if abs(error) <= self.deadzone:
            return 0.0
        self._integral += error * dt
        self._integral = np.clip(self._integral, -100, 100)
        derivative = (error - self._last_error) / dt if dt > 0 else 0.0
        self._last_error = error
        out = self.kp * error + self.ki * self._integral + self.kd * derivative
        return np.clip(out, -self.max_out, self.max_out)

    def reset(self) -> None:
        self._last_error = 0.0
        self._integral = 0.0


class TrackerController:
    """双轴追踪：用两个 PID 把 (current_x, current_y) 追到 (target_x, target_y)。"""

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
    ) -> tuple:
        """返回 (delta_pan, delta_tilt)，为角度增量（需按标定转为舵机角度）。"""
        err_x = target_x - current_x
        err_y = target_y - current_y
        out_x = self.pid_x.update(err_x, dt)
        out_y = self.pid_y.update(err_y, dt)
        return (out_x, out_y)

    def reset(self) -> None:
        self.pid_x.reset()
        self.pid_y.reset()


class VelocityPredictor:
    """根据前几帧目标位置做线性预测，得到“即将到达”的目标点。"""

    def __init__(self, num_frames: int = None):
        self.n = num_frames if num_frames is not None else cfg.PREDICT_FRAMES
        self._history: deque = deque(maxlen=max(self.n + 1, 2))

    def update(self, x: float, y: float) -> tuple:
        """传入当前帧目标 (x,y)，返回预测的下一帧目标 (px, py)。"""
        self._history.append((x, y))
        if len(self._history) < 2:
            return (x, y)
        # 用最近两点的差作为速度，外推一步
        (x0, y0) = self._history[-2]
        (x1, y1) = self._history[-1]
        vx = x1 - x0
        vy = y1 - y0
        pred_x = x1 + vx
        pred_y = y1 + vy
        return (pred_x, pred_y)

    def reset(self) -> None:
        self._history.clear()
