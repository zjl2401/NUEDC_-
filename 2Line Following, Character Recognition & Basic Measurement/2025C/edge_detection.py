# -*- coding: utf-8 -*-
"""
高精度边缘提取与规则几何体识别
支持：圆、矩形、多边形；亚像素级边缘精化
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
import config


def preprocess_for_edges(
    image: np.ndarray,
    blur_ksize: int = 5,
    use_adaptive: bool = False,
) -> np.ndarray:
    """灰度化、去噪，便于边缘检测。"""
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    if blur_ksize > 0:
        gray = cv2.GaussianBlur(gray, (blur_ksize, blur_ksize), 0)
    if use_adaptive:
        gray = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
    return gray


def detect_edges_canny(
    image: np.ndarray,
    low: Optional[int] = None,
    high: Optional[int] = None,
) -> np.ndarray:
    """Canny 边缘检测。"""
    low = low or config.CANNY_LOW
    high = high or config.CANNY_HIGH
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    return cv2.Canny(gray, low, high)


def find_contours(
    binary: np.ndarray,
    min_area: Optional[int] = None,
    mode: int = cv2.RETR_EXTERNAL,
    method: int = cv2.CHAIN_APPROX_SIMPLE,
) -> List[np.ndarray]:
    """提取轮廓，按面积过滤。"""
    min_area = min_area or config.CONTOUR_MIN_AREA
    contours, _ = cv2.findContours(
        binary, mode, method
    )
    return [c for c in contours if cv2.contourArea(c) >= min_area]


def refine_corners_subpixel(
    gray: np.ndarray,
    corners: np.ndarray,
    win: Tuple[int, int] = (5, 5),
) -> np.ndarray:
    """角点亚像素精化。"""
    if corners.size == 0:
        return corners
    return cv2.cornerSubPix(
        gray, np.float32(corners), win, (-1, -1),
        (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
    )


def detect_circles(
    image: np.ndarray,
    dp: Optional[float] = None,
    min_dist: Optional[float] = None,
    param1: Optional[float] = None,
    param2: Optional[float] = None,
    min_radius: Optional[int] = None,
    max_radius: Optional[int] = None,
) -> List[Tuple[float, float, float]]:
    """
    Hough 圆检测，返回 [(cx, cy, radius), ...] 像素单位。
    """
    dp = dp or config.DP
    min_dist = min_dist or config.MIN_DIST
    param1 = param1 or config.CIRCLE_PARAM1
    param2 = param2 or config.CIRCLE_PARAM2
    min_radius = min_radius or config.MIN_RADIUS
    max_radius = max_radius or config.MAX_RADIUS

    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    circles = cv2.HoughCircles(
        gray, cv2.HOUGH_GRADIENT, dp, min_dist,
        param1=param1, param2=param2,
        minRadius=min_radius, maxRadius=max_radius
    )
    if circles is None:
        return []
    circles = np.uint16(np.around(circles))
    return [(c[0], c[1], c[2]) for c in circles[0, :]]


def detect_rectangles(
    image: np.ndarray,
    min_area: Optional[int] = None,
    approx_eps: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    从轮廓中筛选近似矩形的目标。
    返回列表，每项: {"contour", "box_points", "center", "width_px", "height_px", "angle"}
    """
    min_area = min_area or config.CONTOUR_MIN_AREA
    approx_eps = approx_eps or config.CONTOUR_APPROX_EPS

    edges = detect_edges_canny(image)
    contours = find_contours(edges, min_area=min_area)
    results = []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, approx_eps * peri, True)
        if len(approx) != 4:
            continue
        rect = cv2.minAreaRect(cnt)
        (cx, cy), (w, h), angle = rect
        box = cv2.boxPoints(rect)
        results.append({
            "contour": cnt,
            "box_points": np.int0(box),
            "center": (float(cx), float(cy)),
            "width_px": max(w, h),
            "height_px": min(w, h),
            "angle": angle,
        })
    return results


def detect_polygons(
    image: np.ndarray,
    min_area: Optional[int] = None,
    approx_eps: Optional[float] = None,
    min_vertices: int = 3,
    max_vertices: int = 8,
) -> List[Dict[str, Any]]:
    """
    检测多边形轮廓。
    返回: [{"contour", "approx", "center", "area", "num_vertices"}, ...]
    """
    min_area = min_area or config.CONTOUR_MIN_AREA
    approx_eps = approx_eps or config.CONTOUR_APPROX_EPS

    edges = detect_edges_canny(image)
    contours = find_contours(edges, min_area=min_area)
    results = []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, approx_eps * peri, True)
        n = len(approx)
        if not (min_vertices <= n <= max_vertices):
            continue
        M = cv2.moments(cnt)
        if M["m00"] == 0:
            continue
        cx = M["m10"] / M["m00"]
        cy = M["m01"] / M["m00"]
        results.append({
            "contour": cnt,
            "approx": approx,
            "center": (cx, cy),
            "area": area,
            "num_vertices": n,
        })
    return results


def get_circle_pixel_diameter(circle: Tuple[float, float, float]) -> float:
    """(cx, cy, r) -> 直径（像素）。"""
    return 2.0 * circle[2]


def get_rect_size_px(rect_info: Dict[str, Any]) -> Tuple[float, float]:
    """矩形宽、高（像素）。"""
    return rect_info["width_px"], rect_info["height_px"]
