# -*- coding: utf-8 -*-
"""空对空目标检测。"""

import cv2
import numpy as np
from dataclasses import dataclass
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as cfg


@dataclass
class AirTargetResult:
    found: bool
    cx: float
    cy: float
    area: float


def detect_air_target(frame):
    h, w = frame.shape[:2]
    cx, cy = w/2, h/2
    if frame is None or frame.size == 0:
        return AirTargetResult(False, cx, cy, 0.0)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    low = np.array(getattr(cfg, "AIR_TARGET_HSV_LOW", (20,100,100)))
    high = np.array(getattr(cfg, "AIR_TARGET_HSV_HIGH", (35,255,255)))
    mask = cv2.inRange(hsv, low, high)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3,3)))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_a, max_a = getattr(cfg, "AIR_TARGET_MIN_AREA", 200), getattr(cfg, "AIR_TARGET_MAX_AREA", 15000)
    best, best_area = None, 0
    for c in contours:
        area = cv2.contourArea(c)
        if min_a <= area <= max_a and area > best_area:
            best, best_area = c, area
    if best is None:
        return AirTargetResult(False, cx, cy, 0.0)
    M = cv2.moments(best)
    if M["m00"] <= 0:
        return AirTargetResult(False, cx, cy, 0.0)
    return AirTargetResult(True, M["m10"]/M["m00"], M["m01"]/M["m00"], best_area)
