# -*- coding: utf-8 -*-
"""
无人机代理：上帝视角搜索火源，通过通信信道下发给地面小车。
"""
from typing import Tuple, Optional, List

try:
    import config as cfg
except ImportError:
    cfg = None

from ..vision import detect_fire_sources, FireDetectResult
from ..comm import CommChannel, FireReport

DETECT_INTERVAL = getattr(cfg, "UAV_DETECT_INTERVAL", 3) if cfg else 3


class UAVAgent:
    """
    无人机逻辑：每帧获得俯视图，按间隔检测火源并下发坐标。
    """
    def __init__(self, channel: CommChannel, frame_size: Tuple[int, int]):
        self.channel = channel
        self.w, self.h = frame_size
        self._frame_count = 0
        self._last_detected: Optional[FireDetectResult] = None

    def update(self, uav_view_bgr) -> List[FireDetectResult]:
        """
        输入无人机俯视图，检测火源；按间隔通过 channel 下发。
        返回本帧检测到的火源列表（用于显示）。
        """
        detections = detect_fire_sources(uav_view_bgr)
        self._frame_count += 1
        if detections and (self._frame_count % DETECT_INTERVAL == 0):
            best = detections[0]
            self._last_detected = best
            self.channel.send(FireReport(world_x=best.x, world_y=best.y, frame_id=self._frame_count))
        elif not detections:
            self._last_detected = None
        return detections

    @property
    def last_detected(self) -> Optional[FireDetectResult]:
        return self._last_detected
