# -*- coding: utf-8 -*-
"""2025E 视觉模块：多目标 HSV 检测、颜色/编号锁定、简单形状（手势）区分"""

import cv2
import numpy as np
from typing import Optional, Tuple, List, Dict
import config as cfg


# 颜色名称 -> (lower, upper) 或 双范围 (red)
COLOR_RANGES: Dict[str, List[Tuple]] = {
    "red": [
        (np.array(cfg.RED_LOWER_1), np.array(cfg.RED_UPPER_1)),
        (np.array(cfg.RED_LOWER_2), np.array(cfg.RED_UPPER_2)),
    ],
    "green": [(np.array(cfg.GREEN_LOWER), np.array(cfg.GREEN_UPPER))],
    "blue": [(np.array(cfg.BLUE_LOWER), np.array(cfg.BLUE_UPPER))],
    "yellow": [(np.array(cfg.YELLOW_LOWER), np.array(cfg.YELLOW_UPPER))],
    "cyan": [(np.array(cfg.CYAN_LOWER), np.array(cfg.CYAN_UPPER))],
}
COLOR_IDS = ["red", "green", "blue", "yellow", "cyan"]


def _get_mask_for_color(hsv: np.ndarray, color: str) -> np.ndarray:
    """按颜色名取 HSV 二值 mask。"""
    ranges = COLOR_RANGES.get(color, [])
    if not ranges:
        return np.zeros(hsv.shape[:2], dtype=np.uint8)
    masks = [cv2.inRange(hsv, lo, hi) for lo, hi in ranges]
    return cv2.bitwise_or(masks[0], masks[1]) if len(masks) > 1 else masks[0]


def _contour_shape_hint(contour: np.ndarray) -> str:
    """简单形状：圆度 -> 'circle'，细长比 -> 'strip'，否则 'other'。"""
    area = cv2.contourArea(contour)
    if area < 10:
        return "other"
    perimeter = cv2.arcLength(contour, True)
    if perimeter <= 0:
        return "other"
    circularity = 4 * np.pi * area / (perimeter * perimeter)
    (_, _), (ma, MA), _ = cv2.fitEllipse(contour)
    if ma <= 0:
        return "circle" if circularity > 0.8 else "other"
    aspect = MA / ma
    if circularity > 0.75:
        return "circle"
    if aspect > 2.0:
        return "strip"
    return "other"


def get_blobs_from_mask(
    mask: np.ndarray,
    min_area: int = None,
    max_area: int = None,
) -> List[Tuple[float, float, float, str]]:
    """
    从二值 mask 提取连通域，返回 [(cx, cy, area, shape_hint), ...]，按面积从大到小。
    """
    min_a = min_area if min_area is not None else cfg.MIN_BLOB_AREA
    max_a = max_area if max_area is not None else cfg.MAX_BLOB_AREA
    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    result = []
    for c in contours:
        area = cv2.contourArea(c)
        if not (min_a <= area <= max_a):
            continue
        M = cv2.moments(c)
        if M["m00"] <= 0:
            continue
        cx = M["m10"] / M["m00"]
        cy = M["m01"] / M["m00"]
        shape = _contour_shape_hint(c)
        result.append((cx, cy, area, shape))
    result.sort(key=lambda x: -x[2])
    return result


def detect_multi_targets(
    frame: np.ndarray,
    normalize_light: bool = True,
) -> Dict[str, List[Tuple[float, float, float, str]]]:
    """
    对帧做多颜色检测。若 normalize_light 为 True，先做 CLAHE 缓解光照变化。
    返回 { "red": [(cx,cy,area,shape), ...], "green": [...], ... }
    """
    if frame is None or frame.size == 0:
        return {c: [] for c in COLOR_IDS}
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    if normalize_light:
        h, s, v = cv2.split(hsv)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        v = clahe.apply(v)
        hsv = cv2.merge([h, s, v])
    out = {}
    for color in COLOR_IDS:
        mask = _get_mask_for_color(hsv, color)
        out[color] = get_blobs_from_mask(mask)
    return out


def select_target_by_id(
    all_detections: Dict[str, List[Tuple[float, float, float, str]]],
    target_color_id: int,
) -> Optional[Tuple[float, float, str]]:
    """
    按编号选择目标：0=红, 1=绿, 2=蓝, 3=黄, 4=青。
    返回 (cx, cy, shape) 或 None。
    """
    if target_color_id < 0 or target_color_id >= len(COLOR_IDS):
        return None
    color = COLOR_IDS[target_color_id]
    blobs = all_detections.get(color, [])
    if not blobs:
        return None
    cx, cy, _, shape = blobs[0]
    return (cx, cy, shape)


def select_target_by_color_name(
    all_detections: Dict[str, List[Tuple[float, float, float, str]]],
    color_name: str,
) -> Optional[Tuple[float, float, str]]:
    """按颜色名选择最大 blob，返回 (cx, cy, shape)。"""
    blobs = all_detections.get(color_name, [])
    if not blobs:
        return None
    cx, cy, _, shape = blobs[0]
    return (cx, cy, shape)


def select_target_by_gesture(
    all_detections: Dict[str, List[Tuple[float, float, float, str]]],
    gesture: str,
) -> Optional[Tuple[float, float, str]]:
    """在全部颜色中找第一个 shape 匹配 gesture 的目标（circle / strip / other）。"""
    for color in COLOR_IDS:
        for (cx, cy, _, shape) in all_detections.get(color, []):
            if shape == gesture:
                return (cx, cy, shape)
    return None
