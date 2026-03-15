# -*- coding: utf-8 -*-
"""
目标检测与过滤：非固定形态（动物/四足）不依赖固定形状匹配。
基于运动前景轮廓 + 几何约束（面积、宽高比、extent）过滤杂草/树木/石块。
支持小目标（远距离）的面积与最小边长约束。
"""
from __future__ import annotations

import cv2
import numpy as np
from typing import List, Tuple, Optional
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as cfg


def _rect_extent(contour: np.ndarray) -> float:
    """轮廓面积 / 外接矩形面积。"""
    area = cv2.contourArea(contour)
    if area <= 0:
        return 0.0
    _, (w, h), _ = cv2.minAreaRect(contour)
    if w <= 0 or h <= 0:
        return 0.0
    return area / (float(w) * float(h))


def _aspect_ratio(contour: np.ndarray) -> float:
    """外接矩形宽高比 (width/height)，>=1。"""
    _, (w, h), _ = cv2.minAreaRect(contour)
    a, b = float(max(w, h)), float(min(w, h))
    return a / b if b > 0 else 0.0


def filter_contours_as_targets(
    contours: List[np.ndarray],
    min_area: Optional[int] = None,
    max_area: Optional[int] = None,
    min_bbox_side: Optional[int] = None,
    min_aspect: Optional[float] = None,
    max_aspect: Optional[float] = None,
    min_extent: Optional[float] = None,
    max_extent: Optional[float] = None,
) -> List[Tuple[np.ndarray, Tuple[int, int, int, int], float]]:
    """
    过滤轮廓，保留符合“动物/运动目标”几何约束的候选。
    返回列表 [(轮廓, (x,y,w,h), 面积), ...]。
    """
    min_area = min_area if min_area is not None else getattr(cfg, "MIN_FOREGROUND_AREA", 80)
    max_area = max_area if max_area is not None else getattr(cfg, "MAX_SINGLE_TARGET_AREA", 50000)
    min_bbox_side = min_bbox_side if min_bbox_side is not None else getattr(cfg, "MIN_BBOX_SIDE", 15)
    min_aspect = min_aspect if min_aspect is not None else getattr(cfg, "MIN_ASPECT_RATIO", 0.25)
    max_aspect = max_aspect if max_aspect is not None else getattr(cfg, "MAX_ASPECT_RATIO", 4.0)
    min_extent = min_extent if min_extent is not None else getattr(cfg, "MIN_EXTENT", 0.1)
    max_extent = max_extent if max_extent is not None else getattr(cfg, "MAX_EXTENT", 1.0)

    result: List[Tuple[np.ndarray, Tuple[int, int, int, int], float]] = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < min_area or area > max_area:
            continue
        x, y, w, h = cv2.boundingRect(c)
        side = min(w, h)
        if side < min_bbox_side:
            continue
        ar = _aspect_ratio(c)
        if ar < min_aspect or ar > max_aspect:
            continue
        ext = _rect_extent(c)
        if ext < min_extent or ext > max_extent:
            continue
        result.append((c, (x, y, w, h), float(area)))
    return result


def detect_targets_from_mask(
    mask: np.ndarray,
) -> List[Tuple[Tuple[int, int, int, int], float, bool]]:
    """
    从前景 mask 检测目标框。
    :return: [( (x,y,w,h), area, is_small_target ), ...]
    """
    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    small_thresh = getattr(cfg, "SMALL_TARGET_AREA_THRESH", 1500)
    candidates = filter_contours_as_targets(contours)
    out: List[Tuple[Tuple[int, int, int, int], float, bool]] = []
    for _c, (x, y, w, h), area in candidates:
        out.append(((x, y, w, h), area, area < small_thresh))
    return out
