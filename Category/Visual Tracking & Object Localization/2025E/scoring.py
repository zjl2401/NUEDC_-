"""
2025E 命中/击中判定与计分

核心思想：
- 定义一个“命中圈”半径 HIT_RADIUS_PX
- 目标点与瞄准点距离 <= 半径，且连续保持 HIT_HOLD_FRAMES 帧，则计 1 次击中
- 计中后进入冷却 HIT_COOLDOWN_FRAMES，避免重复计分

仿真模式：瞄准点 = follower 十字 (follower_x/y)
真机模式：若没有绿点反馈，默认瞄准点 = 画面中心 (cx, cy)
"""

from dataclasses import dataclass
from typing import Optional, Tuple

import config as cfg


@dataclass
class ScoreState:
    score: int = 0
    hits: int = 0
    in_radius_frames: int = 0
    cooldown_frames: int = 0

    def update(
        self,
        target_xy: Optional[Tuple[float, float]],
        aim_xy: Tuple[float, float],
    ) -> bool:
        """
        返回：本帧是否“新触发一次击中”
        """
        if self.cooldown_frames > 0:
            self.cooldown_frames -= 1

        if target_xy is None:
            self.in_radius_frames = 0
            return False

        tx, ty = target_xy
        ax, ay = aim_xy
        dx = tx - ax
        dy = ty - ay
        if (dx * dx + dy * dy) <= (cfg.HIT_RADIUS_PX * cfg.HIT_RADIUS_PX):
            if self.cooldown_frames > 0:
                return False
            self.in_radius_frames += 1
            if self.in_radius_frames >= cfg.HIT_HOLD_FRAMES:
                self.hits += 1
                self.score += cfg.SCORE_PER_HIT
                self.in_radius_frames = 0
                self.cooldown_frames = cfg.HIT_COOLDOWN_FRAMES
                return True
            return False

        self.in_radius_frames = 0
        return False

