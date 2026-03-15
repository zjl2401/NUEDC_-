# -*- coding: utf-8 -*-
"""摄像头封装：香橙派 / 树莓派兼容。"""

import cv2
import numpy as np
from typing import Optional, Tuple
import config as cfg


def open_camera(index=None, width=None, height=None, exposure=None):
    idx = index if index is not None else cfg.CAMERA_INDEX
    cap = cv2.VideoCapture(idx)
    if not cap.isOpened():
        cap = cv2.VideoCapture(f"/dev/video{idx}")
    if not cap.isOpened():
        return cap
    w = width or cfg.FRAME_WIDTH
    h = height or cfg.FRAME_HEIGHT
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
    if hasattr(cv2, "CAP_PROP_EXPOSURE"):
        exp = exposure if exposure is not None else getattr(cfg, "EXPOSURE", -4)
        cap.set(cv2.CAP_PROP_EXPOSURE, exp)
    return cap


def read_frame(cap):
    ret, frame = cap.read()
    if not ret or frame is None:
        return False, None
    return True, frame
