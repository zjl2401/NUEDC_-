# -*- coding: utf-8 -*-
"""速度预测。"""
from collections import deque
from typing import Tuple

class VelocityPredictor:
    def __init__(self, num_frames=3):
        self._history = deque(maxlen=max(num_frames + 1, 2))
    def update(self, x: float, y: float) -> Tuple[float, float]:
        self._history.append((x, y))
        if len(self._history) < 2:
            return (x, y)
        x0, y0 = self._history[-2]
        x1, y1 = self._history[-1]
        return (x1 + (x1-x0), y1 + (y1-y0))
    def reset(self):
        self._history.clear()
