# -*- coding: utf-8 -*-
"""
纯软件模拟：无需摄像头与香橙派。
1) 合成场景：生成“野外”背景 + 运动目标（模拟四足/动物），用于算法验证。
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

# 默认模拟分辨率
SIM_WIDTH = getattr(cfg, "PROC_WIDTH", 640)
SIM_HEIGHT = getattr(cfg, "PROC_HEIGHT", 480)


def _noise_background(w: int, h: int, seed: int = 42) -> np.ndarray:
    """生成带噪点的草地/野外底色。"""
    rng = np.random.default_rng(seed)
    # 绿色调 + 少量黄/棕
    base = np.array([40, 90, 40], dtype=np.uint8)
    var = rng.integers(-25, 25, (h, w, 3), dtype=np.int16)
    img = np.clip(base + var, 0, 255).astype(np.uint8)
    return cv2.GaussianBlur(img, (5, 5), 0)


def _draw_bushes(frame: np.ndarray, n: int = 8, seed: int = 1) -> None:
    """在画面上画若干静态椭圆模拟灌木/杂草丛。"""
    rng = np.random.default_rng(seed)
    h, w = frame.shape[:2]
    for _ in range(n):
        cx = int(rng.integers(0, w))
        cy = int(rng.integers(0, h))
        ax, ay = int(rng.integers(20, 60)), int(rng.integers(15, 45))
        color = (int(rng.integers(30, 70)), int(rng.integers(80, 140)), int(rng.integers(30, 70)))
        cv2.ellipse(frame, (cx, cy), (ax, ay), 0, 0, 360, color, -1)


def generate_synthetic_frame(
    frame_index: int,
    width: int = SIM_WIDTH,
    height: int = SIM_HEIGHT,
    *,
    bg_cache: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """
    生成一帧合成场景：野外背景 + 一个运动的“动物”椭圆（形态略变模拟肢体）。
    :return: (BGR 帧, 背景缓存，下次传入可复用避免重复生成)
    """
    if bg_cache is not None and bg_cache.shape[:2] == (height, width):
        frame = bg_cache.copy()
    else:
        frame = _noise_background(width, height)
        _draw_bushes(frame)
        bg_cache = frame.copy()

    # 运动目标：椭圆中心做 Lissajous 轨迹，长短轴轻微变化模拟非固定形态
    t = frame_index * 0.05
    cx = int(width * 0.5 + width * 0.35 * math.sin(t))
    cy = int(height * 0.5 + height * 0.3 * math.sin(t * 0.7 + 1))
    ax = int(25 + 8 * math.sin(t * 0.3))
    ay = int(40 + 10 * math.sin(t * 0.5 + 0.5))
    angle = 15 * math.sin(t * 0.2) * 180 / math.pi

    # 深色“动物”剪影，与背景有对比
    cv2.ellipse(frame, (cx, cy), (max(ax, 5), max(ay, 5)), angle, 0, 360, (30, 30, 30), -1)
    cv2.ellipse(frame, (cx, cy), (max(ax, 5), max(ay, 5)), angle, 0, 360, (50, 50, 50), 1)

    return frame, bg_cache


def synthetic_frame_generator(
    width: int = SIM_WIDTH,
    height: int = SIM_HEIGHT,
    max_frames: Optional[int] = None,
) -> Iterator[Tuple[np.ndarray, int]]:
    """无限或有限帧的合成场景生成器。yield (frame, index)。"""
    bg = None
    n = 0
    while max_frames is None or n < max_frames:
        frame, bg = generate_synthetic_frame(n, width, height, bg_cache=bg)
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
