# -*- coding: utf-8 -*-
"""地面标志物检测。"""

import cv2
import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as cfg


@dataclass
class GroundMarkerResult:
    found: bool
    cx: float
    cy: float
    area: float
    color_type: str
    bbox: Tuple[int, int, int, int]


def _red_mask(hsv):
    l1, u1 = np.array(cfg.GROUND_MARKER_RED_LOW1), np.array(cfg.GROUND_MARKER_RED_HIGH1)
    l2, u2 = np.array(cfg.GROUND_MARKER_RED_LOW2), np.array(cfg.GROUND_MARKER_RED_HIGH2)
    return cv2.bitwise_or(cv2.inRange(hsv, l1, u1), cv2.inRange(hsv, l2, u2))


def _green_mask(hsv):
    return cv2.inRange(hsv, np.array(cfg.GROUND_MARKER_GREEN_LOW), np.array(cfg.GROUND_MARKER_GREEN_HIGH))


def _largest_contour(mask, min_a, max_a):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best, best_area, best_rect = None, 0, (0,0,0,0)
    for c in contours:
        area = cv2.contourArea(c)
        if min_a <= area <= max_a and area > best_area:
            best, best_area = c, area
            x,y,w,h = cv2.boundingRect(c)
            best_rect = (x,y,w,h)
    if best is None:
        return None
    M = cv2.moments(best)
    if M["m00"] <= 0:
        return None
    cx, cy = M["m10"]/M["m00"], M["m01"]/M["m00"]
    return (cx, cy, best_area, best_rect)


def detect_ground_markers(frame, roi=None):
    if frame is None or frame.size == 0:
        return []
    work = frame
    if roi:
        x,y,w,h = roi
        work = frame[y:y+h, x:x+w]
    hsv = cv2.cvtColor(work, cv2.COLOR_BGR2HSV)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5))
    results = []
    for mask_fn, color in [(_red_mask, "red"), (_green_mask, "green")]:
        m = mask_fn(hsv)
        m = cv2.morphologyEx(cv2.morphologyEx(m, cv2.MORPH_CLOSE, kernel), cv2.MORPH_OPEN, kernel)
        ret = _largest_contour(m, cfg.GROUND_MARKER_MIN_AREA, cfg.GROUND_MARKER_MAX_AREA)
        if ret:
            cx, cy, area, (bx,by,bw,bh) = ret
            if roi:
                cx, cy, bx, by = cx+roi[0], cy+roi[1], bx+roi[0], by+roi[1]
            results.append(GroundMarkerResult(True, cx, cy, area, color, (bx,by,bw,bh)))
    results.sort(key=lambda r: r.area, reverse=True)
    return results
