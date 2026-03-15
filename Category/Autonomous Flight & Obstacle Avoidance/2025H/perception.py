# -*- coding: utf-8 -*-
"""
野生动物巡查 - 主感知管道
流程：采集 → 背景减除 → 形态学 → 轮廓检测与几何过滤 → 输出目标列表
支持跳帧与空闲降频以降低功耗。
"""
from __future__ import annotations

import cv2
import numpy as np
import time
import logging
from typing import List, Tuple, Optional, Any, Union, Iterator

import config as cfg
from vision import create_bg_subtractor, get_foreground_mask, detect_targets_from_mask

logging.basicConfig(level=getattr(logging, cfg.LOG_LEVEL, logging.INFO))
logger = logging.getLogger(__name__)


class WildlifePerception:
    """野生动物巡查感知：非固定形态 + 低信噪比 + 小目标 + 低功耗友好。"""

    def __init__(
        self,
        cam_index: Union[int, str, None] = None,
        width: int | None = None,
        height: int | None = None,
        target_fps: float | None = None,
        process_every_n: int | None = None,
        idle_sleep_frames: int | None = None,
    ):
        # cam_index: int=摄像头号, str=视频文件路径
        self.cam_index = cam_index if cam_index is not None else cfg.CAM_INDEX
        self.width = width if width is not None else cfg.PROC_WIDTH
        self.height = height if height is not None else cfg.PROC_HEIGHT
        self.target_fps = target_fps if target_fps is not None else cfg.TARGET_FPS
        self.process_every_n = process_every_n if process_every_n is not None else cfg.PROCESS_EVERY_N_FRAMES
        self.idle_sleep_frames = idle_sleep_frames if idle_sleep_frames is not None else cfg.IDLE_SLEEP_FRAMES

        self.cap: Optional[cv2.VideoCapture] = None
        self.bg_subtractor = create_bg_subtractor()
        self.frame_count = 0
        self.last_detection_count = 0
        self.idle_frames = 0
        self._warmup_frames = 30  # 背景模型预热

    def open_camera(self) -> bool:
        """打开摄像头或视频文件。cam_index 为 int 时是设备号，str 时是视频路径。"""
        self.cap = cv2.VideoCapture(self.cam_index)
        if not self.cap.isOpened():
            logger.error("无法打开视频源: %s", self.cam_index)
            return False
        if isinstance(self.cam_index, int):
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, min(30, max(5, int(self.target_fps))))
        logger.info("视频源已打开 %s -> %dx%d", self.cam_index, self.width, self.height)
        return True

    def close(self) -> None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def _read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        if self.cap is None or not self.cap.isOpened():
            return False, None
        ret, frame = self.cap.read()
        if not ret or frame is None:
            return False, None
        if frame.shape[1] != self.width or frame.shape[0] != self.height:
            frame = cv2.resize(frame, (self.width, self.height))
        return True, frame

    def run_once(
        self,
        frame: Optional[np.ndarray] = None,
        *,
        learning_rate: float | None = None,
    ) -> Tuple[np.ndarray, np.ndarray, List[Tuple[Tuple[int, int, int, int], float, bool]]]:
        """
        执行一帧感知。
        :param frame: 若为 None 则从摄像头读一帧
        :param learning_rate: 背景学习率，None 用 config
        :return: (原图, 前景mask, 目标列表 [(bbox, area, is_small), ...])
        """
        if frame is None:
            ok, frame = self._read_frame()
            if not ok or frame is None:
                return np.array([]), np.array([]), []
        self.frame_count += 1
        lr = learning_rate if learning_rate is not None else cfg.BG_LEARNING_RATE
        # 预热阶段用较大学习率
        if self.frame_count <= self._warmup_frames:
            lr = min(0.1, lr * 10)
        fg_mask = get_foreground_mask(frame, self.bg_subtractor, learning_rate=lr)
        targets = detect_targets_from_mask(fg_mask)
        if targets:
            self.last_detection_count = len(targets)
            self.idle_frames = 0
        else:
            self.idle_frames += 1
        return frame, fg_mask, targets

    def should_process_this_frame(self) -> bool:
        """是否在本帧做完整检测（跳帧 / 空闲降频）。"""
        if self.process_every_n > 1 and self.frame_count % self.process_every_n != 0:
            return False
        if self.idle_frames >= 10 and self.idle_sleep_frames > 1:
            if (self.frame_count // self.idle_sleep_frames) % self.idle_sleep_frames != 0:
                return False
        return True

    def run_loop(
        self,
        callback: Optional[Any] = None,
        show: bool | None = None,
        max_frames: int | None = None,
    ) -> None:
        """
        主循环：读帧 → 按策略执行 run_once → 回调/显示。
        :param callback: 每帧回调 callback(frame, fg_mask, targets)，若返回 False 则退出
        :param show: 是否显示窗口，None 用 config
        :param max_frames: 最大处理帧数，None 无限
        """
        show = show if show is not None else cfg.SHOW_DEBUG_WINDOW
        if self.cap is None and not self.open_camera():
            return
        n = 0
        try:
            while True:
                if max_frames is not None and n >= max_frames:
                    break
                ok, frame = self._read_frame()
                if not ok or frame is None:
                    time.sleep(0.05)
                    continue
                n += 1
                if self.should_process_this_frame():
                    _, fg_mask, targets = self.run_once(frame, learning_rate=cfg.BG_LEARNING_RATE)
                else:
                    fg_mask = np.zeros((frame.shape[0], frame.shape[1]), dtype=np.uint8)
                    targets = []
                if callback:
                    try:
                        if callback(frame, fg_mask, targets) is False:
                            break
                    except Exception as e:
                        logger.exception("callback error: %s", e)
                if show:
                    vis = frame.copy()
                    for (x, y, w, h), area, is_small in targets:
                        color = (0, 255, 0) if not is_small else (0, 255, 255)
                        cv2.rectangle(vis, (x, y), (x + w, y + h), color, 2)
                        cv2.putText(
                            vis, f"{area:.0f}", (x, y - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1,
                        )
                    cv2.imshow("frame", vis)
                    cv2.imshow("foreground", fg_mask)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
        finally:
            if show:
                cv2.destroyAllWindows()
            self.close()

    def run_loop_with_generator(
        self,
        frame_generator: Iterator[Tuple[np.ndarray, int]],
        callback: Optional[Any] = None,
        show: bool | None = None,
        max_frames: int | None = None,
        delay_ms: int = 30,
    ) -> None:
        """
        纯软件模拟：从外部生成器读帧，不依赖摄像头。
        frame_generator 应 yield (frame_bgr, frame_index)。
        """
        show = show if show is not None else cfg.SHOW_DEBUG_WINDOW
        n = 0
        try:
            for frame, idx in frame_generator:
                if max_frames is not None and n >= max_frames:
                    break
                n += 1
                if self.should_process_this_frame():
                    _, fg_mask, targets = self.run_once(frame, learning_rate=cfg.BG_LEARNING_RATE)
                else:
                    fg_mask = np.zeros((frame.shape[0], frame.shape[1]), dtype=np.uint8)
                    targets = []
                if callback:
                    try:
                        if callback(frame, fg_mask, targets) is False:
                            break
                    except Exception as e:
                        logger.exception("callback error: %s", e)
                if show:
                    vis = frame.copy()
                    for (x, y, w, h), area, is_small in targets:
                        color = (0, 255, 0) if not is_small else (0, 255, 255)
                        cv2.rectangle(vis, (x, y), (x + w, y + h), color, 2)
                        cv2.putText(
                            vis, f"{area:.0f}", (x, y - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1,
                        )
                    cv2.imshow("frame", vis)
                    cv2.imshow("foreground", fg_mask)
                    if cv2.waitKey(delay_ms) & 0xFF == ord("q"):
                        break
        finally:
            if show:
                cv2.destroyAllWindows()
