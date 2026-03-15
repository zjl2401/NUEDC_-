# -*- coding: utf-8 -*-
"""水平跟踪 PID。"""
import numpy as np
from typing import Tuple
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as cfg


class TrackPIDController:
    def __init__(self, kp=None, ki=None, kd=None, max_out=None, deadzone=None):
        self.kp = kp if kp is not None else cfg.TRACK_PID_KP
        self.ki = ki if ki is not None else cfg.TRACK_PID_KI
        self.kd = kd if kd is not None else cfg.TRACK_PID_KD
        self.max_out = max_out if max_out is not None else cfg.TRACK_PID_MAX_OUTPUT
        self.deadzone = deadzone if deadzone is not None else cfg.DEADZONE_PX
        self._last_x = self._last_y = 0.0
        self._ix = self._iy = 0.0

    def update(self, target_px, target_py, center_x, center_y, dt=1.0):
        ex = target_px - center_x
        ey = target_py - center_y
        if abs(ex) <= self.deadzone: ex = 0.0
        if abs(ey) <= self.deadzone: ey = 0.0
        self._ix += ex * dt
        self._iy += ey * dt
        self._ix = np.clip(self._ix, -200, 200)
        self._iy = np.clip(self._iy, -200, 200)
        dx = (ex - self._last_x) / dt if dt > 0 else 0.0
        dy = (ey - self._last_y) / dt if dt > 0 else 0.0
        self._last_x, self._last_y = ex, ey
        ox = np.clip(self.kp*ex + self.ki*self._ix + self.kd*dx, -self.max_out, self.max_out)
        oy = np.clip(self.kp*ey + self.ki*self._iy + self.kd*dy, -self.max_out, self.max_out)
        return (ox, oy)

    def reset(self):
        self._last_x = self._last_y = self._ix = self._iy = 0.0
