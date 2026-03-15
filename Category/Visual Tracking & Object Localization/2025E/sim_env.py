# -*- coding: utf-8 -*-
"""2025E 仿真环境：合成多目标运动、利萨如轨迹、闪烁/遮挡/光照干扰"""

import cv2
import numpy as np
import time
from typing import Tuple, List, Optional
import config as cfg
from control_2025 import lissajous_xy, circle_xy


# BGR 颜色，用于在画布上绘制各目标
COLOR_BGR = {
    "red": (0, 0, 255),
    "green": (0, 255, 0),
    "blue": (255, 0, 0),
    "yellow": (0, 255, 255),
    "cyan": (255, 255, 0),
}


class SimEnv:
    """
    纯软件仿真画布：
    - 多个彩色 blob 按轨迹运动（可含利萨如、圆周等）
    - 可选：背景闪烁、随机遮挡、光照周期变化
    - 输出 BGR 帧供 vision 模块检测
    """

    def __init__(
        self,
        width: int = None,
        height: int = None,
        enable_flicker: bool = False,
        enable_occlusion: bool = False,
        enable_light_sine: bool = False,
    ):
        self.w = width or cfg.CANVAS_W
        self.h = height or cfg.CANVAS_H
        self.enable_flicker = enable_flicker
        self.enable_occlusion = enable_occlusion
        self.enable_light_sine = enable_light_sine
        self.t0 = time.time()
        self.frame_count = 0
        # 遮挡：剩余持续帧数，0 表示当前无遮挡
        self._occlusion_remaining = 0
        self._occlusion_rect: Optional[Tuple[int, int, int, int]] = None
        # 多目标轨迹：每个 (name, trajectory_fn, radius)
        self._blobs: List[dict] = []

    def add_blob_lissajous(self, color_name: str, radius: int = 12) -> None:
        """添加沿利萨如图形运动的 blob。"""
        self._blobs.append({
            "color": color_name,
            "type": "lissajous",
            "radius": radius,
        })

    def add_blob_circle(
        self,
        color_name: str,
        cx: float,
        cy: float,
        circle_radius: float,
        speed: float = 0.5,
        radius: int = 12,
    ) -> None:
        """添加沿圆周运动的 blob。"""
        self._blobs.append({
            "color": color_name,
            "type": "circle",
            "cx": cx, "cy": cy, "circle_radius": circle_radius, "speed": speed,
            "radius": radius,
        })

    def add_blob_static(self, color_name: str, x: float, y: float, radius: int = 12) -> None:
        """添加静止 blob。"""
        self._blobs.append({
            "color": color_name,
            "type": "static",
            "x": x, "y": y,
            "radius": radius,
        })

    def _get_blob_xy(self, blob: dict, t: float) -> Tuple[float, float]:
        if blob["type"] == "lissajous":
            return lissajous_xy(t * cfg.LISSAJOUS_SPEED)
        if blob["type"] == "circle":
            return circle_xy(
                t, blob["cx"], blob["cy"],
                blob["circle_radius"], blob["speed"],
            )
        if blob["type"] == "static":
            return (blob["x"], blob["y"])
        return (self.w / 2, self.h / 2)

    def _draw_blobs(self, frame: np.ndarray, t: float) -> None:
        for blob in self._blobs:
            x, y = self._get_blob_xy(blob, t)
            ix, iy = int(round(x)), int(round(y))
            r = blob.get("radius", 12)
            bgr = COLOR_BGR.get(blob["color"], (128, 128, 128))
            cv2.circle(frame, (ix, iy), r, bgr, -1)
            cv2.circle(frame, (ix, iy), r + 2, (255, 255, 255), 1)

    def _apply_flicker(self, frame: np.ndarray) -> None:
        if not self.enable_flicker or np.random.rand() > cfg.FLICKER_PROB:
            return
        alpha = np.random.uniform(cfg.FLICKER_ALPHA_MIN, cfg.FLICKER_ALPHA_MAX)
        frame[:] = (frame.astype(np.float32) * (1 - alpha) + np.full_like(frame, 255) * alpha).astype(np.uint8)

    def _apply_occlusion(self, frame: np.ndarray) -> None:
        if not self.enable_occlusion:
            return
        if self._occlusion_remaining > 0:
            x, y, w, h = self._occlusion_rect
            cv2.rectangle(frame, (x, y), (x + w, y + h), (40, 40, 40), -1)
            self._occlusion_remaining -= 1
            return
        if np.random.rand() < cfg.OCCLUSION_PROB:
            sz = np.random.randint(20, cfg.OCCLUSION_MAX_SIZE)
            x = np.random.randint(0, max(1, self.w - sz))
            y = np.random.randint(0, max(1, self.h - sz))
            w = min(sz, self.w - x)
            h = min(sz, self.h - y)
            self._occlusion_rect = (x, y, w, h)
            self._occlusion_remaining = cfg.OCCLUSION_DURATION
            cv2.rectangle(frame, (x, y), (x + w, y + h), (40, 40, 40), -1)

    def _apply_light_sine(self, frame: np.ndarray) -> None:
        if not self.enable_light_sine:
            return
        a = cfg.LIGHT_SINE_AMPLITUDE
        period = cfg.LIGHT_SINE_PERIOD
        phase = (self.frame_count % period) / period * 2 * np.pi
        delta = 1.0 + a * np.sin(phase)
        frame[:] = np.clip(frame.astype(np.float32) * delta, 0, 255).astype(np.uint8)

    def step(self) -> np.ndarray:
        """生成一帧：背景 + 多目标 + 可选干扰。返回 BGR。"""
        t = time.time() - self.t0
        self.frame_count += 1
        # 深灰背景
        frame = np.full((self.h, self.w, 3), (45, 45, 45), dtype=np.uint8)
        self._draw_blobs(frame, t)
        self._apply_flicker(frame)
        self._apply_occlusion(frame)
        self._apply_light_sine(frame)
        return frame

    def get_lissajous_target_xy(self) -> Tuple[float, float]:
        """当前时刻利萨如轨迹上的参考点（用于轨迹跟随模式）。"""
        t = time.time() - self.t0
        return lissajous_xy(t * cfg.LISSAJOUS_SPEED)


def create_multi_target_scene(env: SimEnv) -> None:
    """在 env 上添加多目标：红(利萨如)、绿(圆周)、蓝(圆周)、黄(静态)。"""
    cx, cy = env.w / 2, env.h / 2
    env.add_blob_lissajous("red", radius=14)
    env.add_blob_circle("green", cx, cy, 100, 0.6, radius=12)
    env.add_blob_circle("blue", cx, cy, 140, 0.4, radius=12)
    env.add_blob_static("yellow", cx + 120, cy - 80, radius=12)
