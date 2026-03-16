"""
简单双目视差 -> 深度图 -> 点云 示例

输入:
    - 左右视图 (已校正的立体图像), 灰度或 BGR 都可
    - 相机内参 K, 基线长度 B (左到右相机的距离, 单位与希望的 Z 单位一致)

中间操作:
    1. 使用 StereoBM 计算视差图
    2. 根据 Z = f * B / d 将视差转换为深度
    3. 利用相机模型将 (u, v, Z) 还原为三维点 (X, Y, Z)

输出:
    - 保存一份深度图可视化 (depth_vis.png)
    - 导出简单的点云到 txt (pointcloud.xyz), 每行 X Y Z
"""

from pathlib import Path
from typing import Tuple

import cv2
import numpy as np


def compute_disparity(left_gray: np.ndarray, right_gray: np.ndarray) -> np.ndarray:
    # 参数可根据实际情况调整
    num_disparities = 16 * 6  # 必须是 16 的倍数
    block_size = 9
    stereo = cv2.StereoBM_create(numDisparities=num_disparities, blockSize=block_size)
    disp = stereo.compute(left_gray, right_gray).astype(np.float32) / 16.0
    return disp


def disparity_to_depth(disparity: np.ndarray, f: float, baseline: float) -> np.ndarray:
    depth = np.zeros_like(disparity, dtype=np.float32)
    mask = disparity > 0.1
    depth[mask] = f * baseline / disparity[mask]
    return depth


def depth_to_pointcloud(
    depth: np.ndarray,
    K: np.ndarray,
) -> np.ndarray:
    h, w = depth.shape
    u_coords, v_coords = np.meshgrid(np.arange(w), np.arange(h))

    Z = depth.reshape(-1)
    X = (u_coords.reshape(-1) - K[0, 2]) * Z / K[0, 0]
    Y = (v_coords.reshape(-1) - K[1, 2]) * Z / K[1, 1]

    pts = np.stack([X, Y, Z], axis=1)
    valid = Z > 0
    return pts[valid]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--left", type=str, required=True, help="左目图像路径 (已校正)")
    parser.add_argument("--right", type=str, required=True, help="右目图像路径 (已校正)")
    parser.add_argument("--fx", type=float, required=True, help="焦距 fx")
    parser.add_argument("--fy", type=float, required=True, help="焦距 fy")
    parser.add_argument("--cx", type=float, required=True, help="主点 cx")
    parser.add_argument("--cy", type=float, required=True, help="主点 cy")
    parser.add_argument("--baseline", type=float, required=True, help="双目基线长度")
    args = parser.parse_args()

    left_img = cv2.imread(args.left, cv2.IMREAD_GRAYSCALE)
    right_img = cv2.imread(args.right, cv2.IMREAD_GRAYSCALE)
    if left_img is None or right_img is None:
        raise FileNotFoundError("无法读取左右目图像")

    disp = compute_disparity(left_img, right_img)
    K = np.array([[args.fx, 0, args.cx], [0, args.fy, args.cy], [0, 0, 1]], dtype=np.float32)
    depth = disparity_to_depth(disp, f=args.fx, baseline=args.baseline)

    # 深度可视化
    depth_norm = cv2.normalize(depth, None, 0, 255, cv2.NORM_MINMAX)
    depth_vis = depth_norm.astype(np.uint8)
    out_depth = Path(args.left).with_name("depth_vis.png")
    cv2.imwrite(str(out_depth), depth_vis)
    print(f"深度图可视化已保存: {out_depth}")

    # 点云导出
    pts = depth_to_pointcloud(depth, K)
    out_pc = Path(args.left).with_name("pointcloud.xyz")
    np.savetxt(str(out_pc), pts, fmt="%.4f")
    print(f"点云共 {pts.shape[0]} 点, 已保存为: {out_pc}")

