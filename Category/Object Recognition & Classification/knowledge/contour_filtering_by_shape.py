"""
连通域轮廓提取 + 面积 / 长宽比过滤示例

输入:
    - binary_mask: 二值图 (0/255), 目标区域为白色

中间操作:
    1. 提取轮廓
    2. 计算每个轮廓的面积和外接矩形长宽比
    3. 按面积范围和长宽比过滤

输出:
    - filtered_contours: 满足条件的轮廓列表
"""

from typing import List, Tuple

import cv2
import numpy as np


def filter_contours_by_area_aspect(
    binary_mask: np.ndarray,
    min_area: float,
    max_area: float,
    min_aspect: float,
    max_aspect: float,
) -> List[np.ndarray]:
    if binary_mask is None or binary_mask.size == 0:
        raise ValueError("输入 Mask 为空")

    contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filtered: List[np.ndarray] = []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area or area > max_area:
            continue

        x, y, w, h = cv2.boundingRect(cnt)
        if h == 0:
            continue
        aspect = w / h if w >= h else h / w  # 统一 >= 1
        if aspect < min_aspect or aspect > max_aspect:
            continue

        filtered.append(cnt)

    return filtered


def draw_filtered_contours(
    original_bgr: np.ndarray,
    filtered_contours: List[np.ndarray],
    color: Tuple[int, int, int] = (0, 0, 255),
) -> np.ndarray:
    canvas = original_bgr.copy()
    cv2.drawContours(canvas, filtered_contours, -1, color, 2)
    return canvas


if __name__ == "__main__":
    # 示例: 从颜色分割结果中筛选“近似长方形”的候选目标
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("mask_path", type=str, help="输入二值 Mask 路径 (0/255)")
    parser.add_argument("--min_area", type=float, default=200.0)
    parser.add_argument("--max_area", type=float, default=1e5)
    parser.add_argument("--min_aspect", type=float, default=1.0)
    parser.add_argument("--max_aspect", type=float, default=4.0)
    args = parser.parse_args()

    mask = cv2.imread(args.mask_path, cv2.IMREAD_GRAYSCALE)
    if mask is None:
        raise FileNotFoundError(f"无法读取 Mask: {args.mask_path}")

    filtered = filter_contours_by_area_aspect(
        mask,
        min_area=args.min_area,
        max_area=args.max_area,
        min_aspect=args.min_aspect,
        max_aspect=args.max_aspect,
    )

    # 为了演示输出，这里用三通道版本的 mask 作为背景
    bgr_bg = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
    vis = draw_filtered_contours(bgr_bg, filtered)

    out_path = str(Path(args.mask_path).with_name("filtered_contours_vis.png"))
    cv2.imwrite(out_path, vis)
    print(f"筛选出的轮廓数量: {len(filtered)}, 可视化结果已保存到: {out_path}")

