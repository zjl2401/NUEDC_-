"""
2025E 真机视觉流水线：
- 可选：黑框四边形检测 + 透视矫正（将摄像头画面映射到标准屏幕坐标）
- 可选：ROI 模式（锁定目标后只在局部区域检测，提升帧率与稳定性）

输入:
    - 摄像头帧（BGR）

中间操作:
    1) （可选）透视矫正：检测黑框四边形 -> warpPerspective
    2) （可选）ROI：根据上一帧目标位置裁剪 ROI，检测后再坐标补偿回全图
    3) 调用 vision_2025.detect_multi_targets 得到多颜色 blob 质心

输出:
    - detections: 与 detect_multi_targets 一致的结构（坐标已经在“矫正后画面”的坐标系中）
    - work_frame: 用于显示的工作帧（矫正后或原图）
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

import config as cfg
from vision_2025 import detect_multi_targets


def find_screen_quad(gray: np.ndarray) -> Optional[np.ndarray]:
    """从灰度图里找黑框四边形，返回 4x2 顶点 (顺序: 左上、右上、右下、左下)。"""
    _, binary = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    cnt = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(cnt)
    if area < 1000:
        return None
    epsilon = 0.02 * cv2.arcLength(cnt, True)
    approx = cv2.approxPolyDP(cnt, epsilon, True)
    if len(approx) != 4:
        return None
    pts = approx.reshape(4, 2).astype(np.float32)
    s = pts.sum(axis=1)
    left_top = pts[np.argmin(s)]
    right_bottom = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    right_top = pts[np.argmin(diff)]
    left_bottom = pts[np.argmax(diff)]
    return np.array([left_top, right_top, right_bottom, left_bottom], dtype=np.float32)


class PerspectiveTransformer:
    def __init__(self, dst_size: Tuple[int, int]):
        self.dst_size = dst_size
        self.M: Optional[np.ndarray] = None

    def calibrate(self, frame: np.ndarray) -> bool:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        src_quad = find_screen_quad(gray)
        if src_quad is None:
            return False
        w, h = self.dst_size
        dst_quad = np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype=np.float32)
        self.M = cv2.getPerspectiveTransform(src_quad, dst_quad)
        return True

    def warp(self, frame: np.ndarray) -> np.ndarray:
        if self.M is None:
            return frame
        return cv2.warpPerspective(frame, self.M, self.dst_size)


@dataclass
class ROIState:
    enabled: bool = True
    size: int = 240
    last_xy: Optional[Tuple[float, float]] = None
    lost_frames: int = 0


class RealVisionPipeline:
    def __init__(self, use_perspective: bool = True, roi_enabled: bool = True, roi_size: int = 240):
        self.use_perspective = use_perspective
        self.transformer = PerspectiveTransformer(dst_size=(cfg.SCREEN_W, cfg.SCREEN_H)) if use_perspective else None
        self.roi = ROIState(enabled=roi_enabled, size=roi_size, last_xy=None)

    def calibrate_if_needed(self, frame: np.ndarray) -> bool:
        if not self.use_perspective or self.transformer is None:
            return False
        if self.transformer.M is not None:
            return True
        return self.transformer.calibrate(frame)

    def _crop_roi(self, frame: np.ndarray) -> Tuple[np.ndarray, Tuple[int, int]]:
        if not self.roi.enabled or self.roi.last_xy is None:
            return frame, (0, 0)
        h, w = frame.shape[:2]
        cx, cy = self.roi.last_xy
        half = self.roi.size // 2
        x0 = max(0, int(cx) - half)
        y0 = max(0, int(cy) - half)
        x1 = min(w, x0 + self.roi.size)
        y1 = min(h, y0 + self.roi.size)
        roi = frame[y0:y1, x0:x1]
        return roi, (x0, y0)

    @staticmethod
    def _offset_detections(
        det: Dict[str, List[Tuple[float, float, float, str]]],
        ox: int,
        oy: int,
    ) -> Dict[str, List[Tuple[float, float, float, str]]]:
        if ox == 0 and oy == 0:
            return det
        out: Dict[str, List[Tuple[float, float, float, str]]] = {}
        for k, blobs in det.items():
            out[k] = [(cx + ox, cy + oy, area, shape) for (cx, cy, area, shape) in blobs]
        return out

    def process(self, frame: np.ndarray, normalize_light: bool = True) -> Tuple[Dict, np.ndarray]:
        if frame is None or frame.size == 0:
            return {}, frame

        work = frame
        if self.use_perspective and self.transformer is not None and self.transformer.M is not None:
            work = self.transformer.warp(frame)

        roi_img, (ox, oy) = self._crop_roi(work)
        detections_roi = detect_multi_targets(roi_img, normalize_light=normalize_light)
        detections = self._offset_detections(detections_roi, ox, oy)
        return detections, work

    def update_roi_center(self, xy: Optional[Tuple[float, float]]) -> None:
        if not self.roi.enabled:
            return
        if xy is None:
            self.roi.lost_frames += 1
            # 丢失时扩大 ROI（逐步回退到全图由外层做）
            if cfg.ROI_GROW_ON_LOST and self.roi.size < cfg.ROI_SIZE_MAX:
                self.roi.size = min(cfg.ROI_SIZE_MAX, self.roi.size + cfg.ROI_GROW_STEP)
            # 仍保留 last_xy，方便“以老位置为中心”扩大搜索
            return
        self.roi.last_xy = xy
        self.roi.lost_frames = 0
        # 找回目标后把 ROI 收回默认大小
        self.roi.size = cfg.ROI_SIZE

