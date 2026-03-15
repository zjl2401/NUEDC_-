"""
房号识别（香橙派 + OpenCV）：识别病房门口数字（如 "1"、"2"）。
支持：ROI 裁切 → 二值化 → 轮廓/连通域 → 可选 pytesseract OCR 或模板匹配。
"""
from __future__ import annotations

from typing import Tuple

import cv2
import numpy as np

# 可选：pip install pytesseract，且系统安装 tesseract-ocr
try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

# 默认 ROI：图像中门口区域 (x_ratio, y_ratio, w_ratio, h_ratio)，便于不同分辨率
_roi_ratio: Tuple[float, float, float, float] | None = None


def init_room_detector(roi: Tuple[int, int, int, int] | Tuple[float, float, float, float] | None = None) -> None:
    """
    初始化房号检测器。
    roi: 像素 (x, y, w, h) 或比例 (x_ratio, y_ratio, w_ratio, h_ratio)，如 (0.3, 0.2, 0.4, 0.3)
    """
    global _roi_ratio
    if roi is not None and len(roi) == 4:
        if all(0 <= r <= 1 for r in roi):
            _roi_ratio = tuple(roi)
        else:
            _roi_ratio = None  # 调用时用像素 roi 传入


def _crop_roi(frame: np.ndarray, roi: Tuple[int, int, int, int] | None) -> np.ndarray:
    h, w = frame.shape[:2]
    if roi is not None:
        x, y, rw, rh = roi
        x, y, rw, rh = int(x), int(y), int(rw), int(rh)
        x = max(0, min(x, w - 1))
        y = max(0, min(y, h - 1))
        rw = min(rw, w - x)
        rh = min(rh, h - y)
        return frame[y : y + rh, x : x + rw]
    if _roi_ratio is not None:
        x = int(w * _roi_ratio[0])
        y = int(h * _roi_ratio[1])
        rw = int(w * _roi_ratio[2])
        rh = int(h * _roi_ratio[3])
        rw = min(rw, w - x)
        rh = min(rh, h - y)
        if rw > 0 and rh > 0:
            return frame[y : y + rh, x : x + rw]
    return frame


def recognize_room_number(
    frame: np.ndarray,
    roi: Tuple[int, int, int, int] | None = None,
) -> Tuple[int, float]:
    """
    从一帧图像中识别房号（单个数字 1–9，0 表示未识别）。
    :param frame: BGR 图像
    :param roi: 可选 (x, y, w, h) 像素；若 init 时已设比例则此处可 None
    :return: (房号 0–9, 置信度 0~1)
    """
    if frame is None or frame.size == 0:
        return 0, 0.0

    img = _crop_roi(frame, roi)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # 自适应阈值更好应对光照
    th = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
    )
    # 形态学去噪
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, kernel)

    num, conf = 0, 0.0

    if HAS_TESSERACT:
        # 只识别数字，单字符
        cfg = "--psm 10 -c tessedit_char_whitelist=0123456789"
        try:
            s = pytesseract.image_to_string(th, config=cfg).strip()
            if s and len(s) >= 1 and s[0].isdigit():
                num = int(s[0])
                conf = 0.85
        except Exception:
            pass

    if conf <= 0 and th.size > 0:
        # 无 tesseract 或识别失败：用轮廓面积比粗判“有数字区域”，不解析具体数字
        contours, _ = cv2.findContours(
            th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        area = img.shape[0] * img.shape[1]
        for c in contours:
            a = cv2.contourArea(c)
            if 0.01 * area < a < 0.8 * area:
                x, y, w, h = cv2.boundingRect(c)
                if h > 10 and w > 5 and 0.3 < h / w < 3:
                    # 有合理数字形状的轮廓，但无法识别具体数字
                    num = 0
                    conf = 0.3
                    break

    if num < 0 or num > 9:
        num = 0
    return num, min(1.0, conf)


def recognize_room_number_with_template(
    frame: np.ndarray,
    template_dir: str,
    roi: Tuple[int, int, int, int] | None = None,
) -> Tuple[int, float]:
    """
    使用模板匹配识别房号（不依赖 pytesseract）。
    template_dir 下放 1.png, 2.png, ... 9.png，与 ROI 内区域做 matchTemplate。
    """
    img = _crop_roi(frame, roi)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    th = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
    )
    best_num, best_score = 0, 0.0
    for i in range(1, 10):
        path = f"{template_dir}/{i}.png"
        try:
            tpl = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if tpl is None:
                continue
            res = cv2.matchTemplate(th, tpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            if max_val > best_score:
                best_score = max_val
                best_num = i
        except Exception:
            continue
    if best_score < 0.5:
        return 0, 0.0
    return best_num, float(best_score)
