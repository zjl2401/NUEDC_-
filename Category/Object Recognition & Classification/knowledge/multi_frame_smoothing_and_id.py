"""
多帧置信度累加 + 简单 ID 维持示例

适用场景:
    - 识别/检测结果在连续帧间抖动, 希望通过时间维度平滑
    - 同一物体在画面中缓慢移动, 希望给它分配一个稳定 ID

输入 (逐帧):
    - 当前帧检测结果: 列表 [ (x, y, w, h, class_id, score), ... ]

中间操作:
    1. 利用欧氏距离将当前帧目标与上一帧已有轨迹关联
    2. 对每条轨迹维持:
        - 当前置信度 (如滑动平均)
        - 连续命中帧数 / 丢失帧数
    3. 仅当置信度和连续命中帧数达到阈值时, 输出“稳定目标”

输出:
    - 带 ID 的稳定目标列表, 例如:
        [ {id: 1, bbox: [...], class_id: 0, score: 0.92}, ... ]
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np


@dataclass
class Track:
    track_id: int
    class_id: int
    bbox: np.ndarray  # [x, y, w, h]
    score: float
    hits: int = 1
    misses: int = 0


class SimpleTracker:
    def __init__(
        self,
        dist_thresh: float = 50.0,
        min_hits: int = 3,
        max_misses: int = 5,
        alpha: float = 0.6,  # 置信度滑动平均权重
    ):
        self.dist_thresh = dist_thresh
        self.min_hits = min_hits
        self.max_misses = max_misses
        self.alpha = alpha
        self._next_id = 1
        self.tracks: Dict[int, Track] = {}

    @staticmethod
    def _center(bbox: np.ndarray) -> np.ndarray:
        x, y, w, h = bbox
        return np.array([x + w / 2.0, y + h / 2.0], dtype=np.float32)

    def update(self, detections: List[Tuple[float, float, float, float, int, float]]) -> List[Track]:
        """
        detections: 列表 [(x, y, w, h, class_id, score), ...]
        返回: 当前帧认为是“稳定”的轨迹列表
        """
        # 标记所有轨迹为“未匹配”
        for tr in self.tracks.values():
            tr.misses += 1

        used_det = set()

        # 尝试为每个轨迹寻找最近的检测框
        for tid, tr in list(self.tracks.items()):
            tr_center = self._center(tr.bbox)

            best_det_idx = -1
            best_dist = float("inf")

            for di, det in enumerate(detections):
                if di in used_det:
                    continue
                x, y, w, h, class_id, score = det
                if class_id != tr.class_id:
                    continue
                det_center = self._center(np.array([x, y, w, h], dtype=np.float32))
                dist = np.linalg.norm(det_center - tr_center)
                if dist < best_dist:
                    best_dist = dist
                    best_det_idx = di

            if best_det_idx >= 0 and best_dist <= self.dist_thresh:
                # 成功匹配: 更新轨迹
                x, y, w, h, class_id, score = detections[best_det_idx]
                tr.bbox = np.array([x, y, w, h], dtype=np.float32)
                tr.score = self.alpha * score + (1 - self.alpha) * tr.score
                tr.hits += 1
                tr.misses = 0
                used_det.add(best_det_idx)

        # 对未匹配的检测框新建轨迹
        for di, det in enumerate(detections):
            if di in used_det:
                continue
            x, y, w, h, class_id, score = det
            bbox = np.array([x, y, w, h], dtype=np.float32)
            tr = Track(
                track_id=self._next_id,
                class_id=class_id,
                bbox=bbox,
                score=score,
            )
            self.tracks[self._next_id] = tr
            self._next_id += 1

        # 清理长时间未命中的轨迹
        to_delete = [tid for tid, tr in self.tracks.items() if tr.misses > self.max_misses]
        for tid in to_delete:
            del self.tracks[tid]

        # 仅输出“命中次数达到 min_hits”的稳定目标
        stable = [tr for tr in self.tracks.values() if tr.hits >= self.min_hits]
        return stable


if __name__ == "__main__":
    # 演示: 构造若干帧虚拟检测结果, 观察 ID 和置信度如何随时间演化
    tracker = SimpleTracker(dist_thresh=30.0, min_hits=2, max_misses=3, alpha=0.5)

    # 三帧: 同一目标缓慢移动, score 有些抖动
    frames = [
        [(10, 10, 20, 20, 0, 0.7)],
        [(12, 11, 20, 20, 0, 0.9)],
        [(15, 13, 20, 20, 0, 0.8)],
    ]

    for t, dets in enumerate(frames, start=1):
        stable_tracks = tracker.update(dets)
        print(f"Frame {t}: detections={dets}")
        for tr in stable_tracks:
            print(f"  Track id={tr.track_id}, hits={tr.hits}, score={tr.score:.3f}, bbox={tr.bbox.tolist()}")

