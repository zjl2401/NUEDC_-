# -*- coding: utf-8 -*-
"""
背景建模与前景分割：应对野外杂草、树木等低信噪比环境。
使用 MOG2/GMG/KNN + 形态学去噪，突出运动/形态变化目标。
"""
from __future__ import annotations

import cv2
import numpy as np
from typing import Tuple

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as cfg


def create_bg_subtractor() -> cv2.BackgroundSubtractor:
    """根据 config 创建背景减除器。"""
    name = getattr(cfg, "BG_SUBTRACTOR", "MOG2").upper()
    if name == "MOG2":
        return cv2.createBackgroundSubtractorMOG2(
            history=getattr(cfg, "MOG2_HISTORY", 500),
            varThreshold=getattr(cfg, "MOG2_VAR_THRESHOLD", 16),
            detectShadows=getattr(cfg, "MOG2_DETECT_SHADOWS", True),
        )
    if name == "KNN":
        return cv2.createBackgroundSubtractorKNN(
            history=getattr(cfg, "MOG2_HISTORY", 500),
            dist2Threshold=400.0,
            detectShadows=getattr(cfg, "MOG2_DETECT_SHADOWS", True),
        )
    if name == "GMG":
        return cv2.createBackgroundSubtractorMOG2(
            history=120,
            varThreshold=16,
            detectShadows=False,
        )
    return cv2.createBackgroundSubtractorMOG2(500, 16, True)


def get_morph_kernels() -> Tuple[np.ndarray, np.ndarray]:
    """开运算、闭运算核。"""
    open_sz = getattr(cfg, "MORPH_OPEN_SIZE", (3, 3))
    close_sz = getattr(cfg, "MORPH_CLOSE_SIZE", (5, 5))
    return (
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, open_sz),
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, close_sz),
    )


def apply_morphology(mask: np.ndarray) -> np.ndarray:
    """对前景 mask 做开运算去小斑点、闭运算填洞。"""
    k_open, k_close = get_morph_kernels()
    out = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k_open)
    out = cv2.morphologyEx(out, cv2.MORPH_CLOSE, k_close)
    return out


def get_foreground_mask(
    frame: np.ndarray,
    bg_subtractor: cv2.BackgroundSubtractor,
    learning_rate: float | None = None,
) -> np.ndarray:
    """
    得到前景二值图。
    :param frame: BGR 帧
    :param bg_subtractor: 已创建的背景减除器
    :param learning_rate: 学习率，None 则用 config
    """
    lr = learning_rate if learning_rate is not None else getattr(cfg, "BG_LEARNING_RATE", 0.001)
    fg = bg_subtractor.apply(frame, fgmask=None, learningRate=lr)
    # 阴影置为 0，只保留确定前景 255
    fg[fg == 127] = 0
    fg = apply_morphology(fg)
    return fg
