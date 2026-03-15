# -*- coding: utf-8 -*-
"""
入侵检测核心模块：基于 OpenCV 背景减法的运动检测。
适用于 2021 电赛 D 题 - 基于互联网的摄像机入侵检测系统（纯软件模拟）。
"""

import cv2
import numpy as np
from typing import Optional, Tuple, List


class IntrusionDetector:
    """基于 MOG2 背景减法的入侵检测器。"""

    def __init__(
        self,
        min_area: int = 500,
        threshold: int = 25,
        blur_ksize: int = 5,
        history: int = 500,
        var_threshold: float = 16,
        roi: Optional[Tuple[int, int, int, int]] = None,
    ):
        """
        Args:
            min_area: 判定为入侵的最小轮廓面积（像素）
            threshold: 二值化阈值
            blur_ksize: 高斯模糊核大小（奇数）
            history: 背景建模历史帧数
            var_threshold: MOG2 方差阈值
            roi: 检测区域 (x, y, w, h)，None 表示全图
        """
        self.min_area = min_area
        self.threshold = threshold
        self.blur_ksize = blur_ksize if blur_ksize % 2 == 1 else blur_ksize + 1
        self.roi = roi  # (x, y, w, h)

        self._bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=history,
            varThreshold=var_threshold,
            detectShadows=True,
        )
        self._bg_subtractor.setShadowThreshold(0.5)
        self._bg_subtractor.setShadowValue(0)

    def _get_roi_frame(self, frame: np.ndarray) -> np.ndarray:
        """若配置了 ROI，则返回 ROI 区域；否则返回整帧。"""
        if self.roi is None:
            return frame
        x, y, w, h = self.roi
        return frame[y : y + h, x : x + w].copy()

    def _get_full_frame_mask(self, frame: np.ndarray, mask_roi: np.ndarray) -> np.ndarray:
        """将 ROI 内的二值掩码映射回全图尺寸。"""
        if self.roi is None:
            return mask_roi
        full_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        x, y, w, h = self.roi
        full_mask[y : y + h, x : x + w] = mask_roi
        return full_mask

    def process(self, frame: np.ndarray) -> Tuple[bool, np.ndarray, Optional[np.ndarray]]:
        """
        处理一帧图像，检测是否有入侵（运动目标）。

        Returns:
            (is_intrusion, frame_with_boxes, mask)
            - is_intrusion: 是否检测到入侵
            - frame_with_boxes: 在原图上绘制了检测框的帧（用于显示）
            - mask: 运动区域二值图（可选，用于调试）
        """
        roi_frame = self._get_roi_frame(frame)
        if roi_frame.size == 0:
            return False, frame.copy(), None

        # 灰度 + 高斯模糊降噪
        gray = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (self.blur_ksize, self.blur_ksize), 0)

        # 背景减法
        fg_mask = self._bg_subtractor.apply(gray)
        _, fg_mask = cv2.threshold(fg_mask, self.threshold, 255, cv2.THRESH_BINARY)
        # 去除阴影（MOG2 中阴影通常为 127）
        fg_mask[fg_mask == 127] = 0

        # 形态学去噪
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)

        # 全图掩码（用于画框时对应原图坐标）
        full_mask = self._get_full_frame_mask(frame, fg_mask)

        # 找轮廓，筛选面积 >= min_area 的轮廓
        contours, _ = cv2.findContours(
            full_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        intrusion_boxes: List[Tuple[int, int, int, int]] = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area >= self.min_area:
                x, y, w, h = cv2.boundingRect(cnt)
                intrusion_boxes.append((x, y, w, h))

        # 在原图上画框
        out = frame.copy()
        for (x, y, w, h) in intrusion_boxes:
            cv2.rectangle(out, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.putText(
                out, "INTRUSION", (x, y - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1,
            )

        is_intrusion = len(intrusion_boxes) > 0
        return is_intrusion, out, full_mask
