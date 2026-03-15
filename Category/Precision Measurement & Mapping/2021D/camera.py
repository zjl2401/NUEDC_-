# -*- coding: utf-8 -*-
"""
摄像头/视频采集封装。支持 USB 摄像头或本地视频文件（用于纯软件模拟）。
"""

import cv2
from typing import Union, Optional


def open_source(source: Union[int, str]) -> cv2.VideoCapture:
    """
    打开视频源：摄像头索引（int）或视频文件路径（str）。

    Args:
        source: 0/1 等为摄像头索引，或 "path/to/video.mp4"

    Returns:
        cv2.VideoCapture 对象
    """
    if isinstance(source, str) and source.isdigit():
        source = int(source)
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"无法打开视频源: {source}")
    return cap


def read_frame(cap: cv2.VideoCapture) -> Optional[tuple]:
    """
    读取一帧。若为视频文件且读到末尾，会循环重播。

    Returns:
        (ret, frame) 或 None（若未打开）
    """
    if cap is None:
        return None
    ret, frame = cap.read()
    if not ret and isinstance(cap.get(cv2.CAP_PROP_FRAME_COUNT), (int, float)):
        # 视频文件结束时重置到开头
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total > 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
    return (ret, frame) if ret else None
