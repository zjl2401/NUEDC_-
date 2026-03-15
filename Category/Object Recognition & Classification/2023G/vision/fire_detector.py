# -*- coding: utf-8 -*-
"""
火源检测：OpenCV 红色光斑 / 发热物体模拟（HSV 红色双区间）。
适用于俯视图中红色目标。
"""
import cv2
import numpy as np
from dataclasses import dataclass
from typing import List

try:
    import config as cfg
except ImportError:
    cfg = None

if cfg:
    LOW1 = getattr(cfg, "FIRE_HSV_LOW1", (0, 100, 100))
    HIGH1 = getattr(cfg, "FIRE_HSV_HIGH1", (10, 255, 255))
    LOW2 = getattr(cfg, "FIRE_HSV_LOW2", (170, 100, 100))
    HIGH2 = getattr(cfg, "FIRE_HSV_HIGH2", (180, 255, 255))
    MIN_AREA = getattr(cfg, "FIRE_MIN_AREA", 150)
    MAX_AREA = getattr(cfg, "FIRE_MAX_AREA", 50000)
else:
    LOW1, HIGH1 = (0, 100, 100), (10, 255, 255)
    LOW2, HIGH2 = (170, 100, 100), (180, 255, 255)
    MIN_AREA, MAX_AREA = 150, 50000


@dataclass
class FireDetectResult:
    found: bool
    x: float
    y: float
    area: float
    confidence: float = 1.0


def _red_mask(hsv: np.ndarray) -> np.ndarray:
    m1 = cv2.inRange(hsv, np.array(LOW1), np.array(HIGH1))
    m2 = cv2.inRange(hsv, np.array(LOW2), np.array(HIGH2))
    return cv2.bitwise_or(m1, m2)


def detect_fire_sources(frame: np.ndarray) -> List[FireDetectResult]:
    """
    在俯视图中检测火源（红色区域），返回世界坐标 (x, y)。
    """
    if frame is None or frame.size == 0:
        return []
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = _red_mask(hsv)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel), cv2.MORPH_OPEN, kernel)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    results = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < MIN_AREA or area > MAX_AREA:
            continue
        M = cv2.moments(c)
        if M["m00"] <= 0:
            continue
        cx = M["m10"] / M["m00"]
        cy = M["m01"] / M["m00"]
        conf = min(1.0, (area - MIN_AREA) / (MAX_AREA - MIN_AREA)) if MAX_AREA > MIN_AREA else 1.0
        results.append(FireDetectResult(True, cx, cy, area, conf))
    results.sort(key=lambda r: r.area, reverse=True)
    return results
