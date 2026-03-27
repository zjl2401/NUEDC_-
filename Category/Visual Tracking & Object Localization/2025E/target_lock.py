"""
2025E 更稳的目标锁定/重捕获策略（抗干扰）

输入:
    - detections: {color: [(cx, cy, area, shape), ...], ...}
    - 期望目标（按颜色名或按编号）

策略要点:
    - 候选打分：面积优先 + 距离上一帧/预测点更近优先
    - 距离门限：单帧跳变过大视为可疑
    - 连续帧确认：稳定出现若干帧才认为锁定
    - 丢失处理：进入 LOST 状态，允许短期预测；ROI 可逐步扩大/回退全图由外层实现
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

import config as cfg


Blob = Tuple[float, float, float, str]  # cx, cy, area, shape


@dataclass
class LockResult:
    target_xy: Optional[Tuple[float, float]]
    status: str  # SEARCH/TRACK/LOST
    stable: bool
    debug: str = ""


class TargetLock:
    def __init__(self):
        self._last_xy: Optional[Tuple[float, float]] = None
        self._stable_frames = 0
        self._lost_frames = 0

    @staticmethod
    def _dist2(a: Tuple[float, float], b: Tuple[float, float]) -> float:
        dx = a[0] - b[0]
        dy = a[1] - b[1]
        return dx * dx + dy * dy

    def reset(self) -> None:
        self._last_xy = None
        self._stable_frames = 0
        self._lost_frames = 0

    def _pick_best(self, blobs: List[Blob], prior_xy: Optional[Tuple[float, float]]) -> Optional[Tuple[float, float]]:
        if not blobs:
            return None

        # prior 为空时：直接取面积最大
        if prior_xy is None:
            cx, cy, _, _ = blobs[0]
            return (cx, cy)

        # prior 存在时：按 "距离优先 + 面积" 综合
        best = None
        best_score = -1e18
        for (cx, cy, area, _) in blobs:
            d2 = self._dist2((cx, cy), prior_xy)
            # 距离越小越好（负），面积越大越好（正）
            score = (-d2) + 0.2 * float(area)
            if score > best_score:
                best_score = score
                best = (cx, cy)
        return best

    def update_by_color_name(
        self,
        detections: Dict[str, List[Blob]],
        color_name: str,
        prior_xy: Optional[Tuple[float, float]] = None,
    ) -> LockResult:
        blobs = detections.get(color_name, [])
        # detect_multi_targets 已按面积从大到小排序，先取 topK 降低误检影响
        top = blobs[:5]

        prior = prior_xy or self._last_xy
        cand = self._pick_best(top, prior_xy=prior)

        if cand is None:
            self._lost_frames += 1
            self._stable_frames = 0
            stable = False
            status = "LOST" if self._last_xy is not None else "SEARCH"
            return LockResult(target_xy=None, status=status, stable=stable, debug=f"lost={self._lost_frames}")

        # 跳变门限
        if self._last_xy is not None:
            d2 = self._dist2(cand, self._last_xy)
            if d2 > float(cfg.MAX_JUMP_PX * cfg.MAX_JUMP_PX):
                # 可疑跳变：当成“本帧丢失”，等待重捕获
                self._lost_frames += 1
                self._stable_frames = 0
                return LockResult(
                    target_xy=None,
                    status="LOST",
                    stable=False,
                    debug=f"jump_reject d={np.sqrt(d2):.1f}px",
                )

        self._last_xy = cand
        self._lost_frames = 0
        self._stable_frames += 1
        stable = self._stable_frames >= cfg.CONFIRM_HITS_FRAMES
        return LockResult(target_xy=cand, status="TRACK", stable=stable, debug=f"stable={self._stable_frames}")

