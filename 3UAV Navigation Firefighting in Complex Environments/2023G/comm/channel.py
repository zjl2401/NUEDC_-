# -*- coding: utf-8 -*-
"""
空地协同通信：模拟 WiFi/Lora 低延迟链路。
UAV 下发火源坐标，地面小车接收。纯软件用内存队列实现。
"""
from collections import deque
from dataclasses import dataclass
from typing import Optional

try:
    import config as cfg
except ImportError:
    cfg = None

LATENCY = getattr(cfg, "COMM_LATENCY_FRAMES", 0) if cfg else 0


@dataclass
class FireReport:
    """火源上报报文。"""
    world_x: float
    world_y: float
    frame_id: int = 0


class CommChannel:
    """
    模拟无线信道：发送端 push，接收端在延迟 N 帧后 pop。
    单进程内用 deque 模拟延迟队列。
    """
    def __init__(self, latency_frames: int = 0):
        self.latency_frames = latency_frames
        self._queue: deque = deque()  # (report, deliver_at_frame)
        self._current_frame = 0

    def tick(self) -> None:
        self._current_frame += 1

    def send(self, report: FireReport) -> None:
        deliver_at = self._current_frame + self.latency_frames
        self._queue.append((report, deliver_at))

    def receive(self) -> Optional[FireReport]:
        while self._queue and self._queue[0][1] <= self._current_frame:
            report, _ = self._queue.popleft()
            return report
        return None
