"""
深度图/距离场 -> 占据栅格示例

输入:
    - 深度图 (或距离图) 路径, 单位可为米
    - 栅格分辨率 (每格实际大小, 如 0.1m)
    - 占据阈值 (小于该距离认为是障碍)

中间操作:
    1. 将深度图下采样/归一到较小尺寸
    2. 按阈值将每个网格标记为: 0=空闲, 1=障碍, -1=未知

输出:
    - 一个 2D 占据栅格 (numpy 数组), 并保存为可视化图片 occupancy.png
"""

from pathlib import Path

import cv2
import numpy as np


def depth_to_occupancy(
    depth: np.ndarray,
    max_range: float,
    occ_thresh: float,
) -> np.ndarray:
    grid = np.full(depth.shape, -1, dtype=np.int8)  # -1: 未知
    grid[(depth > 0) & (depth < occ_thresh)] = 1    # 1: 障碍
    grid[(depth >= occ_thresh) & (depth <= max_range)] = 0  # 0: 空闲
    return grid


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--depth", type=str, required=True, help="输入深度图路径 (16位或32位浮点)")
    parser.add_argument("--max_range", type=float, default=10.0, help="最大感知距离, 超出视为未知")
    parser.add_argument("--occ_thresh", type=float, default=2.0, help="障碍占据阈值 (小于该距离为障碍)")
    parser.add_argument("--scale", type=float, default=0.25, help="下采样比例, 方便做小栅格")
    args = parser.parse_args()

    depth_raw = cv2.imread(args.depth, cv2.IMREAD_UNCHANGED)
    if depth_raw is None:
        raise FileNotFoundError(f"无法读取深度图: {args.depth}")

    if depth_raw.dtype != np.float32:
        depth = depth_raw.astype(np.float32)
    else:
        depth = depth_raw

    if args.scale != 1.0:
        depth = cv2.resize(depth, None, fx=args.scale, fy=args.scale, interpolation=cv2.INTER_NEAREST)

    grid = depth_to_occupancy(depth, max_range=args.max_range, occ_thresh=args.occ_thresh)

    # 可视化: 障碍=黑, 空闲=白, 未知=灰
    vis = np.zeros_like(grid, dtype=np.uint8)
    vis[grid == -1] = 128
    vis[grid == 0] = 255
    vis[grid == 1] = 0

    out_path = Path(args.depth).with_name("occupancy.png")
    cv2.imwrite(str(out_path), vis)
    print(f"占据栅格可视化已保存: {out_path}")

