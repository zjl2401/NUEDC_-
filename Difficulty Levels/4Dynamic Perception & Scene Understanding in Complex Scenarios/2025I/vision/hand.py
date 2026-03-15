# -*- coding: utf-8 -*-
"""
手部检测与手势识别：肤色分割 + 轮廓分析
- 手部 2D 中心（用于光标/参数映射）
- 握拳 / 张开 分类（轮廓面积与凸包面积比 + 凸包缺陷）
适配香橙派 OpenCV 纯软件，无 MediaPipe 依赖。
"""
from __future__ import annotations

import cv2
import numpy as np
from enum import Enum
from typing import Tuple, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as cfg


class HandState(Enum):
    """手势状态。"""
    NONE = "none"       # 未检测到
    OPEN = "open"       # 张开
    FIST = "fist"       # 握拳


class HandDetector:
    """
    基于 YCrCb 肤色 + 最大连通域的手部检测。
    输出：手中心 (cx, cy)、手势状态（张开/握拳）、可选轮廓与 mask。
    """

    def __init__(
        self,
        skin_cr: Tuple[int, int] = (cfg.SKIN_Cr_LOW, cfg.SKIN_Cr_HIGH),
        skin_cb: Tuple[int, int] = (cfg.SKIN_Cb_LOW, cfg.SKIN_Cb_HIGH),
        skin_y: Tuple[int, int] = (cfg.SKIN_Y_LOW, cfg.SKIN_Y_HIGH),
        min_area: int = cfg.MIN_HAND_AREA,
        max_area: int = cfg.MAX_HAND_AREA,
        fist_extent: float = cfg.FIST_EXTENT_THRESH,
        open_extent: float = cfg.OPEN_EXTENT_THRESH,
        defect_depth: int = cfg.DEFECT_DEPTH_THRESH,
    ):
        self.skin_cr = skin_cr
        self.skin_cb = skin_cb
        self.skin_y = skin_y
        self.min_area = min_area
        self.max_area = max_area
        self.fist_extent = fist_extent
        self.open_extent = open_extent
        self.defect_depth = defect_depth
        self._last_center: Optional[Tuple[float, float]] = None
        self._lost_frames = 0
        self._max_lost = getattr(cfg, "MAX_TRACK_LOST_FRAMES", 5)

    def _skin_mask(self, frame: np.ndarray) -> np.ndarray:
        """YCrCb 肤色二值图。"""
        ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
        y, cr, cb = cv2.split(ycrcb)
        mask = np.uint8(
            (y >= self.skin_y[0]) & (y <= self.skin_y[1]) &
            (cr >= self.skin_cr[0]) & (cr <= self.skin_cr[1]) &
            (cb >= self.skin_cb[0]) & (cb <= self.skin_cb[1])
        ) * 255
        kernel_open = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            getattr(cfg, "SKIN_MORPH_OPEN", (3, 3)),
        )
        kernel_close = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            getattr(cfg, "SKIN_MORPH_CLOSE", (9, 9)),
        )
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_open)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_close)
        return mask

    def _largest_contour(self, mask: np.ndarray):
        """最大连通域轮廓。"""
        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE,
        )
        if not contours:
            return None
        by_area = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(by_area)
        if area < self.min_area or area > self.max_area:
            return None
        return by_area

    def _classify_gesture(self, contour: np.ndarray) -> HandState:
        """
        轮廓面积/凸包面积：握拳时接近 1，张开时较小。
        辅以凸包缺陷数量（张开时指间有缺陷）。
        """
        area = cv2.contourArea(contour)
        if area <= 0:
            return HandState.NONE
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        if hull_area <= 0:
            return HandState.OPEN
        extent = area / hull_area

        if extent >= self.fist_extent:
            return HandState.FIST
        if extent <= self.open_extent:
            return HandState.OPEN
        # 中间区域：用凸包缺陷数区分（握拳缺陷少）
        try:
            hull_idx = cv2.convexHull(contour, returnPoints=False)
            if hull_idx is None or len(hull_idx) < 3:
                return HandState.OPEN
            defects = cv2.convexityDefects(contour, hull_idx)
            if defects is None:
                return HandState.FIST
            deep_defects = 0
            for i in range(defects.shape[0]):
                _, _, _, d = defects[i, 0]
                if d > self.defect_depth * 256:  # 固定点格式
                    deep_defects += 1
            return HandState.OPEN if deep_defects >= 2 else HandState.FIST
        except Exception:
            return HandState.FIST if extent > 0.65 else HandState.OPEN

    def process(
        self,
        frame: np.ndarray,
        *,
        classify_gesture: bool = True,
    ) -> Tuple[Optional[Tuple[float, float]], HandState, Optional[np.ndarray], np.ndarray]:
        """
        处理一帧，返回 (手中心, 手势, 轮廓, 肤色mask)。
        若未检测到 hand，中心为 None，手势为 NONE；丢失时用上一帧中心并增加 lost 计数。
        """
        mask = self._skin_mask(frame)
        contour = self._largest_contour(mask)

        if contour is None:
            self._lost_frames += 1
            if self._lost_frames <= self._max_lost and self._last_center is not None:
                center = self._last_center
                state = HandState.NONE  # 保持上次位置，但状态标为无
            else:
                center = None
                state = HandState.NONE
            return center, state, None, mask

        self._lost_frames = 0
        M = cv2.moments(contour)
        if M["m00"] > 0:
            cx = M["m10"] / M["m00"]
            cy = M["m01"] / M["m00"]
            self._last_center = (float(cx), float(cy))
        else:
            self._last_center = None

        state = self._classify_gesture(contour) if classify_gesture else HandState.OPEN
        return self._last_center, state, contour, mask
