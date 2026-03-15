"""
摄像头采集（香橙派 + OpenCV）：USB 摄像头或 CSI，为视觉模块提供图像帧。
支持仿真注入：set_simulator(sim) 后 read_frame 从仿真器获取图像。
"""
from __future__ import annotations

from typing import Any

import cv2

_cap: cv2.VideoCapture | None = None
_width = 640
_height = 480
_simulator: Any = None


def set_simulator(sim: Any) -> None:
    """注入仿真器后，read_frame 返回仿真画面。"""
    global _simulator
    _simulator = sim


def init_camera(device: int = 0, width: int = 640, height: int = 480) -> bool:
    """
    初始化摄像头。香橙派 USB 摄像头一般为 /dev/video0，即 device=0。
    CSI 摄像头在部分系统上也可能是 0 或需指定 v4l2 等。
    """
    global _cap, _width, _height
    if _cap is not None:
        _cap.release()
        _cap = None
    _cap = cv2.VideoCapture(device)
    if not _cap.isOpened():
        return False
    _width = width
    _height = height
    _cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    _cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    return True


def read_frame() -> Any:
    """
    读取一帧 BGR 图像（numpy ndarray）。失败返回 None。仿真模式下从仿真器获取。
    """
    global _cap, _simulator
    if _simulator is not None:
        return _simulator.read_frame()
    if _cap is None or not _cap.isOpened():
        return None
    ret, frame = _cap.read()
    if not ret or frame is None:
        return None
    return frame


def release_camera() -> None:
    global _cap
    if _cap is not None:
        _cap.release()
        _cap = None
