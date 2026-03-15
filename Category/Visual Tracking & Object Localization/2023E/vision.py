# -*- coding: utf-8 -*-
"""视觉模块：HSV 双色追踪、透视校正、质心提取（OpenCV）"""

import cv2
import numpy as np
from typing import Optional, Tuple, List
import config as cfg


def get_laser_centroid(mask: np.ndarray, min_area: int, max_area: int) -> Optional[Tuple[float, float]]:
    """从二值 mask 中取最大连通域质心，并做面积过滤。"""
    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    best = None
    best_area = 0
    for c in contours:
        area = cv2.contourArea(c)
        if min_area <= area <= max_area and area > best_area:
            best = c
            best_area = area
    if best is None:
        return None
    M = cv2.moments(best)
    if M["m00"] <= 0:
        return None
    cx = M["m10"] / M["m00"]
    cy = M["m01"] / M["m00"]
    return (cx, cy)


def extract_red_mask(hsv: np.ndarray) -> np.ndarray:
    """红色在 HSV 中跨 0 度，需两段范围取并集。"""
    lower1 = np.array(cfg.RED_LOWER_1)
    upper1 = np.array(cfg.RED_UPPER_1)
    lower2 = np.array(cfg.RED_LOWER_2)
    upper2 = np.array(cfg.RED_UPPER_2)
    m1 = cv2.inRange(hsv, lower1, upper1)
    m2 = cv2.inRange(hsv, lower2, upper2)
    return cv2.bitwise_or(m1, m2)


def extract_green_mask(hsv: np.ndarray) -> np.ndarray:
    """绿色激光 mask。"""
    lower = np.array(cfg.GREEN_LOWER)
    upper = np.array(cfg.GREEN_UPPER)
    return cv2.inRange(hsv, lower, upper)


def find_red_centroid(hsv: np.ndarray) -> Optional[Tuple[float, float]]:
    """画面中红色目标点质心（原始像素坐标）。"""
    mask = extract_red_mask(hsv)
    return get_laser_centroid(mask, cfg.MIN_LASER_AREA, cfg.MAX_LASER_AREA)


def find_green_centroid(hsv: np.ndarray) -> Optional[Tuple[float, float]]:
    """画面中绿色激光点质心（原始像素坐标）。"""
    mask = extract_green_mask(hsv)
    return get_laser_centroid(mask, cfg.MIN_LASER_AREA, cfg.MAX_LASER_AREA)


def find_screen_quad(gray: np.ndarray) -> Optional[np.ndarray]:
    """从灰度图里找黑框四边形，返回 4x2 顶点 (顺序: 左上、右上、右下、左下)。"""
    _, binary = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(
        binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    # 取面积最大的轮廓
    if not contours:
        return None
    cnt = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(cnt)
    if area < 1000:
        return None
    # 多边形逼近
    epsilon = 0.02 * cv2.arcLength(cnt, True)
    approx = cv2.approxPolyDP(cnt, epsilon, True)
    if len(approx) != 4:
        return None
    pts = approx.reshape(4, 2).astype(np.float32)
    # 排序：左上、右上、右下、左下
    s = pts.sum(axis=1)
    left_top = pts[np.argmin(s)]
    right_bottom = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    right_top = pts[np.argmin(diff)]
    left_bottom = pts[np.argmax(diff)]
    return np.array([left_top, right_top, right_bottom, left_bottom], dtype=np.float32)


class PerspectiveTransformer:
    """透视校正：将摄像头视野中的屏幕四边形映射到标准矩形坐标。"""

    def __init__(self):
        self.M: Optional[np.ndarray] = None
        self.dst_size = (cfg.SCREEN_W, cfg.SCREEN_H)

    def calibrate(self, frame: np.ndarray) -> bool:
        """从当前帧检测黑框并建立透视变换矩阵。"""
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame
        src_quad = find_screen_quad(gray)
        if src_quad is None:
            return False
        dst_quad = np.array([
            [0, 0],
            [self.dst_size[0], 0],
            [self.dst_size[0], self.dst_size[1]],
            [0, self.dst_size[1]],
        ], dtype=np.float32)
        self.M = cv2.getPerspectiveTransform(src_quad, dst_quad)
        return True

    def set_matrix(self, src_quad: np.ndarray) -> None:
        """直接用四个顶点设置变换（src_quad 4x2）。"""
        dst_quad = np.array([
            [0, 0],
            [self.dst_size[0], 0],
            [self.dst_size[0], self.dst_size[1]],
            [0, self.dst_size[1]],
        ], dtype=np.float32)
        self.M = cv2.getPerspectiveTransform(src_quad.astype(np.float32), dst_quad)

    def point_to_screen(self, px: float, py: float) -> Optional[Tuple[float, float]]:
        """将图像像素坐标变换到屏幕坐标 (0~SCREEN_W, 0~SCREEN_H)。"""
        if self.M is None:
            return None
        pt = np.array([[[px, py]]], dtype=np.float32)
        out = cv2.perspectiveTransform(pt, self.M)
        x, y = out[0, 0]
        return (float(x), float(y))

    def warp_frame(self, frame: np.ndarray) -> np.ndarray:
        """整帧透视校正。"""
        if self.M is None:
            return frame
        return cv2.warpPerspective(frame, self.M, self.dst_size)


class VisionPipeline:
    """完整视觉流水线：读帧 → 透视校正(可选) → 红/绿质心（屏幕坐标）。"""

    def __init__(self, use_perspective: bool = True):
        self.use_perspective = use_perspective
        self.transformer = PerspectiveTransformer() if use_perspective else None

    def process_frame(
        self,
        frame: np.ndarray,
        calibrate_if_needed: bool = False,
    ) -> Tuple[
        Optional[Tuple[float, float]],
        Optional[Tuple[float, float]],
        np.ndarray,
    ]:
        """
        返回: (red_screen_xy, green_screen_xy, work_frame)
        work_frame 若做了透视则为校正后小图，否则为原图（用于显示）。
        """
        if frame is None or frame.size == 0:
            return None, None, frame

        if self.use_perspective and self.transformer is not None:
            if self.transformer.M is None and calibrate_if_needed:
                self.transformer.calibrate(frame)
            if self.transformer.M is not None:
                work = self.transformer.warp_frame(frame)
                hsv_work = cv2.cvtColor(work, cv2.COLOR_BGR2HSV)
            else:
                work = frame
                hsv_work = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        else:
            work = frame
            hsv_work = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        red_raw = find_red_centroid(hsv_work)
        green_raw = find_green_centroid(hsv_work)

        # 校正后的 work 已是屏幕坐标系，质心即屏幕坐标；未校正时用原图坐标
        red_screen = red_raw
        green_screen = green_raw

        return red_screen, green_screen, work
