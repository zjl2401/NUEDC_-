# -*- coding: utf-8 -*-
"""
纯软件模拟：无需摄像头与香橙派。
1) 合成场景：背景 + 运动的“手” (肤色椭圆/ blob)，用于验证手势与映射。
2) 视频文件：用本地视频代替实时摄像头。
"""
from __future__ import annotations

import cv2
import numpy as np
import math
from typing import Iterator, Tuple, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as cfg

SIM_WIDTH = getattr(cfg, "PROC_WIDTH", 640)
SIM_HEIGHT = getattr(cfg, "PROC_HEIGHT", 480)

# 肤色 BGR 近似（使 YCrCb 落在 config 中肤色范围内）
SKIN_BGR = (130, 150, 200)   # BGR 肤色块


def _neutral_background(w: int, h: int) -> np.ndarray:
    """室内/桌面风格背景。"""
    base = np.array([220, 218, 210], dtype=np.uint8)  # 浅灰
    img = np.tile(base.reshape(1, 1, 3), (h, w, 1))
    # 轻微纹理
    noise = np.random.randint(-8, 8, (h, w, 3), dtype=np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return cv2.GaussianBlur(img, (3, 3), 0)


def generate_synthetic_frame(
    frame_index: int,
    width: int = SIM_WIDTH,
    height: int = SIM_HEIGHT,
    *,
    bg_cache: Optional[np.ndarray] = None,
    gesture: str = "open",  # "open" | "fist" 影响椭圆扁率（握拳更圆）
) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """
    生成一帧：背景 + 一个运动的肤色椭圆模拟“手”。
    gesture: open 时椭圆略扁（张开手掌），fist 时更圆。
    """
    if bg_cache is not None and bg_cache.shape[:2] == (height, width):
        frame = bg_cache.copy()
    else:
        frame = _neutral_background(width, height)
        bg_cache = frame.copy()

    t = frame_index * 0.04
    # 手中心做 Lissajous 轨迹
    cx = int(width * 0.5 + width * 0.35 * math.sin(t))
    cy = int(height * 0.5 + height * 0.3 * math.sin(t * 0.7 + 1))
    if gesture == "fist":
        ax, ay = 35, 35
    else:
        ax = int(45 + 5 * math.sin(t * 0.5))
        ay = int(35 + 5 * math.cos(t * 0.3))
    angle = 20 * math.sin(t * 0.15) * 180 / math.pi

    # 肤色椭圆
    cv2.ellipse(frame, (cx, cy), (max(ax, 10), max(ay, 10)), angle, 0, 360, SKIN_BGR, -1)
    # 边缘稍暗，更像手部立体感
    cv2.ellipse(frame, (cx, cy), (max(ax, 10), max(ay, 10)), angle, 0, 360, (100, 120, 170), 2)
    # 轻微高斯模糊使轮廓更自然
    roi = frame[
        max(0, cy - ay - 20) : min(height, cy + ay + 20),
        max(0, cx - ax - 20) : min(width, cx + ax + 20),
    ]
    if roi.size > 0:
        frame[
            max(0, cy - ay - 20) : min(height, cy + ay + 20),
            max(0, cx - ax - 20) : min(width, cx + ax + 20),
        ] = cv2.GaussianBlur(roi, (5, 5), 0.8)

    return frame, bg_cache


def synthetic_frame_generator(
    width: int = SIM_WIDTH,
    height: int = SIM_HEIGHT,
    max_frames: Optional[int] = None,
    alternate_gesture: bool = True,
) -> Iterator[Tuple[np.ndarray, int]]:
    """合成“手”运动序列。alternate_gesture 时每隔一段帧在 open/fist 间切换。"""
    bg = None
    n = 0
    gesture = "open"
    while max_frames is None or n < max_frames:
        if alternate_gesture and n > 0 and n % 60 == 0:
            gesture = "fist" if gesture == "open" else "open"
        frame, bg = generate_synthetic_frame(n, width, height, bg_cache=bg, gesture=gesture)
        yield frame, n
        n += 1


def video_file_generator(
    video_path: str,
    resize: Optional[Tuple[int, int]] = None,
    max_frames: Optional[int] = None,
) -> Iterator[Tuple[np.ndarray, int]]:
    """从视频文件逐帧读取。yield (frame, index)。"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"无法打开视频: {video_path}")
    n = 0
    try:
        while max_frames is None or n < max_frames:
            ret, frame = cap.read()
            if not ret or frame is None:
                break
            if resize:
                frame = cv2.resize(frame, resize)
            yield frame, n
            n += 1
    finally:
        cap.release()
