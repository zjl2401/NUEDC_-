# -*- coding: utf-8 -*-
"""
物像关系建模：相机标定与像素-世界坐标映射
单目针孔模型: u = fx*x/z + cx,  v = fy*y/z + cy
已知物体实际尺寸时: 尺寸(世界) = (距离 * 像素尺寸) / 焦距
"""

import os
import numpy as np
import cv2
from typing import Tuple, Optional
import config


def get_camera_matrix_and_distortion(
    calibration_dir: Optional[str] = None,
    image_size: Optional[Tuple[int, int]] = None,
) -> Tuple[np.ndarray, np.ndarray]]:
    """
    获取相机内参矩阵 K 和畸变系数。
    若存在标定文件则加载，否则使用默认针孔近似。
    """
    calibration_dir = calibration_dir or config.CALIBRATION_DIR
    os.makedirs(calibration_dir, exist_ok=True)
    calib_file = os.path.join(calibration_dir, "camera_params.npz")

    if os.path.isfile(calib_file):
        try:
            data = np.load(calib_file)
            K = data["camera_matrix"]
            dist = data["dist_coeffs"]
            if image_size is not None:
                h, w = image_size[:2]
                K, _ = cv2.getOptimalNewCameraMatrix(
                    K, dist, (w, h), 1, (w, h)
                )
            return K, dist
        except Exception:
            pass

    # 默认内参（假设图像尺寸或使用配置）
    w = int(image_size[1]) if image_size is not None else 640
    h = int(image_size[0]) if image_size is not None else 480
    fx = config.DEFAULT_FX if w <= 640 else config.DEFAULT_FX * (w / 640)
    fy = config.DEFAULT_FY if h <= 480 else config.DEFAULT_FY * (h / 480)
    cx, cy = w / 2.0, h / 2.0

    K = np.array([
        [fx, 0, cx],
        [0, fy, cy],
        [0, 0, 1]
    ], dtype=np.float64)
    dist = np.zeros(5)
    return K, dist


def pixel_to_ray(
    u: float, v: float,
    K: np.ndarray,
) -> Tuple[float, float, float]:
    """
    像素坐标 (u,v) 转为单位方向射线 (未归一化深度方向).
    在 z=1 平面上的方向为: ( (u-cx)/fx, (v-cy)/fy, 1 )
    """
    fx, fy = K[0, 0], K[1, 1]
    cx, cy = K[0, 2], K[1, 2]
    x = (u - cx) / fx
    y = (v - cy) / fy
    return (x, y, 1.0)


def pixel_to_world_plane(
    u: float, v: float,
    K: np.ndarray,
    plane_z: float,
) -> Tuple[float, float]:
    """
    假设物体在平面 z = plane_z 上，将像素 (u,v) 映射到该平面上的世界坐标 (x, y)。
    相机坐标系：z 指向前方，x 右，y 下。
    """
    x, y, _ = pixel_to_ray(u, v, K)
    scale = plane_z  # 射线 t*(x,y,1) 与 z=plane_z 交点
    return (x * scale, y * scale)


def world_plane_to_pixel(
    x: float, y: float,
    K: np.ndarray,
    plane_z: float,
) -> Tuple[float, float]:
    """世界平面 z=plane_z 上的点 (x,y) 投影到像素 (u,v)。"""
    u = K[0, 0] * (x / plane_z) + K[0, 2]
    v = K[1, 1] * (y / plane_z) + K[1, 2]
    return (u, v)


def calibrate_from_checkerboard(
    image_paths: list,
    pattern_size: Tuple[int, int],
    square_size: float = 0.025,
    save_path: Optional[str] = None,
) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    使用棋盘格图像进行标定。
    pattern_size: 内角点数量 (cols, rows)，不含边界
    square_size: 方格边长，单位米
    返回: K, dist, 平均重投影误差
    """
    objp = np.zeros((pattern_size[0] * pattern_size[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:pattern_size[0], 0:pattern_size[1]].T.reshape(-1, 2)
    objp *= square_size

    obj_points = []
    img_points = []
    shape = None

    for path in image_paths:
        if not os.path.isfile(path):
            continue
        img = cv2.imread(path)
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if shape is None:
            shape = gray.shape[::-1]

        ret, corners = cv2.findChessboardCorners(gray, pattern_size, None)
        if not ret:
            continue
        corners2 = cv2.cornerSubPix(
            gray, corners, (5, 5), (-1, -1),
            (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        )
        obj_points.append(objp)
        img_points.append(corners2)

    if len(obj_points) < 3:
        raise RuntimeError("有效标定图像不足，请至少提供 3 张不同角度的棋盘格图像")

    ret, K, dist, rvecs, tvecs = cv2.calibrateCamera(
        obj_points, img_points, shape, None, None
    )
    total_error = 0
    for i in range(len(obj_points)):
        proj, _ = cv2.projectPoints(obj_points[i], rvecs[i], tvecs[i], K, dist)
        total_error += cv2.norm(img_points[i], proj, cv2.NORM_L2) / len(proj)
    mean_error = total_error / len(obj_points)

    if save_path:
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        np.savez(save_path, camera_matrix=K, dist_coeffs=dist)

    return K, dist, mean_error
