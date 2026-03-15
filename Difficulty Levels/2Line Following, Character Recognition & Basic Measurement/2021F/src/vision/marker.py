"""
标志物识别（香橙派 + OpenCV）：识别病房门口红线（停止线）或红色色块。
HSV 红色两段区间 → 形态学 → 轮廓面积过滤。
"""
from __future__ import annotations

from typing import Tuple

import cv2
import numpy as np

# 红色 HSV：OpenCV H 范围 0–180
DEFAULT_RED_HSV_LOW1 = (0, 100, 100)
DEFAULT_RED_HSV_HIGH1 = (10, 255, 255)
DEFAULT_RED_HSV_LOW2 = (170, 100, 100)
DEFAULT_RED_HSV_HIGH2 = (180, 255, 255)

_hsv_low1: Tuple[int, int, int] = DEFAULT_RED_HSV_LOW1
_hsv_high1: Tuple[int, int, int] = DEFAULT_RED_HSV_HIGH1
_hsv_low2: Tuple[int, int, int] = DEFAULT_RED_HSV_LOW2
_hsv_high2: Tuple[int, int, int] = DEFAULT_RED_HSV_HIGH2
_min_area: int = 500


def init_marker_detector(
    hsv_low1: Tuple[int, int, int] = DEFAULT_RED_HSV_LOW1,
    hsv_high1: Tuple[int, int, int] = DEFAULT_RED_HSV_HIGH1,
    hsv_low2: Tuple[int, int, int] = DEFAULT_RED_HSV_LOW2,
    hsv_high2: Tuple[int, int, int] = DEFAULT_RED_HSV_HIGH2,
    min_area: int = 500,
) -> None:
    global _hsv_low1, _hsv_high1, _hsv_low2, _hsv_high2, _min_area
    _hsv_low1, _hsv_high1 = hsv_low1, hsv_high1
    _hsv_low2, _hsv_high2 = hsv_low2, hsv_high2
    _min_area = min_area


def detect_stop_marker(
    frame: np.ndarray,
    roi: Tuple[int, int, int, int] | None = None,
) -> Tuple[bool, float]:
    """
    检测当前帧中是否存在红色停止线或红色色块。
    :param frame: BGR 图像
    :param roi: 可选 (x, y, w, h)，例如只检视野下方
    :return: (是否检测到, 面积占比 0~1)
    """
    if frame is None or frame.size == 0:
        return False, 0.0

    if roi is not None:
        x, y, w, h = roi
        img = frame[y : y + h, x : x + w]
    else:
        img = frame

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, np.array(_hsv_low1), np.array(_hsv_high1))
    mask2 = cv2.inRange(hsv, np.array(_hsv_low2), np.array(_hsv_high2))
    mask = cv2.bitwise_or(mask1, mask2)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    total_area = img.shape[0] * img.shape[1]
    max_ratio = 0.0

    for c in contours:
        area = cv2.contourArea(c)
        if area < _min_area:
            continue
        ratio = area / total_area
        if ratio > max_ratio:
            max_ratio = ratio

    # 面积占比超过一定阈值认为检测到停止线/色块
    detected = max_ratio > 0.005  # 约 0.5% 画面
    return detected, min(1.0, max_ratio * 10)
