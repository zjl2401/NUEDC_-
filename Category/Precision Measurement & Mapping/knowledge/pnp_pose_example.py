"""
PnP 位姿解算示例

输入:
    - 已标定好的相机内参 K 与畸变系数 dist (可来自 camera_calibration_example 的输出)
    - 一组已知 3D-2D 对应点:
        world_points: N x 3, 单位自定 (如 cm)
        image_points: N x 2, 像素坐标

中间操作:
    1. 使用 cv2.solvePnPRansac 估计旋转向量 rvec 与平移向量 tvec
    2. 将 rvec 转换为旋转矩阵 R

输出:
    - 打印 R, t
    - 打印重投影误差 (用于评估解的好坏)
"""

from typing import Tuple

import cv2
import numpy as np


def solve_pnp_with_ransac(
    world_points: np.ndarray,
    image_points: np.ndarray,
    K: np.ndarray,
    dist: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, float]:
    assert world_points.shape[0] == image_points.shape[0]
    obj = world_points.astype(np.float32)
    img = image_points.astype(np.float32)

    ok, rvec, tvec, inliers = cv2.solvePnPRansac(
        obj,
        img,
        K,
        dist,
        flags=cv2.SOLVEPNP_ITERATIVE,
    )
    if not ok:
        raise RuntimeError("solvePnPRansac 失败")

    R, _ = cv2.Rodrigues(rvec)

    # 计算重投影误差
    proj, _ = cv2.projectPoints(obj, rvec, tvec, K, dist)
    proj = proj.reshape(-1, 2)
    err = np.linalg.norm(proj - img, axis=1).mean()

    return R, tvec.reshape(3), float(err)


if __name__ == "__main__":
    # 使用一组虚拟数据演示 PnP 输入/输出格式
    # 实际工程中应从标定板/已知几何结构提取 world_points 与 image_points
    fx = fy = 800.0
    cx = cy = 320.0
    K = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]], dtype=np.float32)
    dist = np.zeros(5, dtype=np.float32)

    # 构造 4 个共面的 3D 点 (单位: cm)
    world_points = np.array(
        [
            [0.0, 0.0, 0.0],
            [10.0, 0.0, 0.0],
            [10.0, 10.0, 0.0],
            [0.0, 10.0, 0.0],
        ],
        dtype=np.float32,
    )

    # 假设真实相机位姿 (R_true, t_true), 这里简单设在 Z 轴前方
    R_true = np.eye(3, dtype=np.float32)
    t_true = np.array([[0.0], [0.0], [50.0]], dtype=np.float32)

    img_points_proj, _ = cv2.projectPoints(world_points, cv2.Rodrigues(R_true)[0], t_true, K, dist)
    image_points = img_points_proj.reshape(-1, 2)

    R_est, t_est, reproj_err = solve_pnp_with_ransac(world_points, image_points, K, dist)

    print("估计 R:\n", R_est)
    print("估计 t:\n", t_est)
    print("平均重投影误差 (像素):", reproj_err)

