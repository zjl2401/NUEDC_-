# -*- coding: utf-8 -*-
"""
非接触式控制盘 - 空间映射与虚拟控制盘
将手部 2D 坐标映射为归一化控制量（光标/参数），带死区与平滑；绘制虚拟控制盘叠加层。
"""
from __future__ import annotations

import cv2
import numpy as np
from typing import Tuple, Optional
import config as cfg
from vision import HandState


class ControlMapper:
    """
    图像坐标 (cx, cy) → 归一化控制量 (nx, ny) ∈ [0, 1]^2。
    支持死区、指数平滑、手部丢失时保持上一帧。
    """

    def __init__(
        self,
        width: int,
        height: int,
        deadzone: float = cfg.MAP_DEADZONE,
        smooth: float = cfg.MAP_SMOOTH,
    ):
        self.w = width
        self.h = height
        self.deadzone = deadzone
        self.smooth = smooth
        self._nx = 0.5
        self._ny = 0.5

    def update(
        self,
        hand_center: Optional[Tuple[float, float]],
        state: HandState,
    ) -> Tuple[float, float]:
        """
        根据当前手中心与手势更新映射。
        返回 (nx, ny)，未检测到 hand 时返回上一帧平滑值。
        """
        if hand_center is None:
            return (self._nx, self._ny)

        cx, cy = hand_center
        # 图像坐标 → [0, 1]
        raw_x = cx / max(1, self.w)
        raw_y = cy / max(1, self.h)
        raw_x = max(0, min(1, raw_x))
        raw_y = max(0, min(1, raw_y))

        # 死区：中心附近不变
        cx_center, cy_center = 0.5, 0.5
        dx = raw_x - cx_center
        dy = raw_y - cy_center
        if abs(dx) < self.deadzone:
            dx = 0
        else:
            dx = (dx - np.sign(dx) * self.deadzone) / (1 - 2 * self.deadzone)
        if abs(dy) < self.deadzone:
            dy = 0
        else:
            dy = (dy - np.sign(dy) * self.deadzone) / (1 - 2 * self.deadzone)
        target_x = 0.5 + dx * 0.5
        target_y = 0.5 + dy * 0.5
        target_x = max(0, min(1, target_x))
        target_y = max(0, min(1, target_y))

        # 指数平滑
        self._nx = self._nx * (1 - self.smooth) + target_x * self.smooth
        self._ny = self._ny * (1 - self.smooth) + target_y * self.smooth
        return (self._nx, self._ny)

    def get_normalized(self) -> Tuple[float, float]:
        """当前归一化控制量。"""
        return (self._nx, self._ny)


def draw_control_panel_overlay(
    frame: np.ndarray,
    nx: float,
    ny: float,
    state: HandState,
    *,
    margin: int = cfg.CONTROL_PANEL_MARGIN,
    alpha: float = cfg.CONTROL_PANEL_ALPHA,
) -> np.ndarray:
    """
    在画面上绘制虚拟控制盘叠加层：边框、十字准心、当前映射点、手势文字。
    """
    h, w = frame.shape[:2]
    overlay = frame.copy()
    # 有效控制区域
    x1, y1 = margin, margin
    x2, y2 = w - margin, h - margin
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 200, 255), 2)
    # 十字准心（中心）
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    cv2.line(overlay, (cx - 20, cy), (cx + 20, cy), (100, 100, 100), 1)
    cv2.line(overlay, (cx, cy - 20), (cx, cy + 20), (100, 100, 100), 1)
    # 映射点：nx,ny ∈ [0,1] 映射到 [x1,y1]-[x2,y2]
    px = int(x1 + (x2 - x1) * nx)
    py = int(y1 + (y2 - y1) * ny)
    color = (0, 255, 0) if state == HandState.OPEN else (0, 0, 255) if state == HandState.FIST else (128, 128, 128)
    cv2.circle(overlay, (px, py), 12, color, 2)
    cv2.circle(overlay, (px, py), 4, color, -1)
    # 手势标签
    state_text = state.value
    cv2.putText(
        overlay, f"Gesture: {state_text}", (x1, y1 - 8),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2,
    )
    cv2.putText(
        overlay, f"Gesture: {state_text}", (x1, y1 - 8),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1,
    )
    out = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
    return out
