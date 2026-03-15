# -*- coding: utf-8 -*-
"""运动目标跟踪：色块 + 卡尔曼 + 丢失保持。"""

import cv2
import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass
from collections import deque
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as cfg


@dataclass
class MovingTargetResult:
    found: bool
    cx: float
    cy: float
    area: float
    pred_cx: float
    pred_cy: float
    lost_frames: int


def _red_mask(hsv):
    l1 = np.array(cfg.TRACK_TARGET_RED_LOW1)
    u1 = np.array(cfg.TRACK_TARGET_RED_HIGH1)
    l2 = np.array(cfg.TRACK_TARGET_RED_LOW2)
    u2 = np.array(cfg.TRACK_TARGET_RED_HIGH2)
    return cv2.bitwise_or(cv2.inRange(hsv, l1, u1), cv2.inRange(hsv, l2, u2))


def _centroid(mask, min_a, max_a):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best, best_area = None, 0
    for c in contours:
        area = cv2.contourArea(c)
        if min_a <= area <= max_a and area > best_area:
            best, best_area = c, area
    if best is None:
        return None
    M = cv2.moments(best)
    if M["m00"] <= 0:
        return None
    return (M["m10"]/M["m00"], M["m01"]/M["m00"], best_area)


class SimpleKalman:
    def __init__(self, q=0.01, r=0.1):
        self.q, self.r = q, r
        self.x, self.p = 0.0, 1.0
    def update(self, z):
        self.p += self.q
        k = self.p / (self.p + self.r)
        self.x += k * (z - self.x)
        self.p *= (1 - k)
        return self.x
    def set_state(self, x, p=1.0):
        self.x, self.p = x, p


class MovingTargetTracker:
    def __init__(self):
        self.kx = SimpleKalman(cfg.KALMAN_PROCESS_NOISE, cfg.KALMAN_MEASURE_NOISE)
        self.ky = SimpleKalman(cfg.KALMAN_PROCESS_NOISE, cfg.KALMAN_MEASURE_NOISE)
        self._last_cx, self._last_cy = cfg.IMG_CENTER_X, cfg.IMG_CENTER_Y
        self._lost = 0

    def update(self, frame):
        h, w = frame.shape[:2]
        cx, cy = w/2, h/2
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.morphologyEx(_red_mask(hsv), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3,3)))
        ret = _centroid(mask, cfg.TRACK_TARGET_MIN_AREA, cfg.TRACK_TARGET_MAX_AREA)
        if ret:
            tx, ty, area = ret
            self._lost = 0
            self._last_cx, self._last_cy = tx, ty
            pred_x = self.kx.update(tx)
            pred_y = self.ky.update(ty)
            return MovingTargetResult(True, tx, ty, area, pred_x, pred_y, 0)
        self._lost += 1
        keep = getattr(cfg, "LOST_FRAME_KEEP", 5)
        if self._lost <= keep:
            return MovingTargetResult(False, self._last_cx, self._last_cy, 0, self.kx.x, self.ky.x, self._lost)
        return MovingTargetResult(False, cx, cy, 0, cx, cy, self._lost)

    def reset(self):
        self._lost = 0
        self.kx.set_state(self._last_cx)
        self.ky.set_state(self._last_cy)
