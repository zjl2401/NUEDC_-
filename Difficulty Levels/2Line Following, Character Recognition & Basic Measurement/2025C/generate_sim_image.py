# -*- coding: utf-8 -*-
"""
生成仿真测量图像：在已知尺寸与“距离”下绘制圆、矩形，便于验证单目测距/测尺寸。
纯软件仿真，无需真实相机。
"""

import os
import cv2
import numpy as np
import config
from camera_calibration import get_camera_matrix_and_distortion


def world_to_pixel(x_m: float, y_m: float, z_m: float, K: np.ndarray) -> tuple:
    """将平面 z=z_m 上的世界坐标 (x_m, y_m) 投影到像素 (u, v)。"""
    u = K[0, 0] * (x_m / z_m) + K[0, 2]
    v = K[1, 1] * (y_m / z_m) + K[1, 2]
    return (int(round(u)), int(round(v)))


def generate_sim_image(
    width: int = 640,
    height: int = 480,
    plane_z_m: float = 0.5,
    circle_center_m: tuple = (0.0, 0.0),
    circle_radius_m: float = 0.05,
    rect_center_m: tuple = (-0.15, 0.1),
    rect_width_m: float = 0.08,
    rect_height_m: float = 0.06,
    bg_gray: int = 200,
    shape_gray: int = 80,
    border_gray: int = 30,
    add_noise: bool = True,
    save_path: str = None,
) -> np.ndarray:
    """
    根据给定世界尺寸与平面距离，用针孔模型生成仿真图。
    返回 BGR 图像；若 save_path 给定则保存。
    """
    K, _ = get_camera_matrix_and_distortion(image_size=(height, width))

    img = np.ones((height, width, 3), dtype=np.uint8) * bg_gray

    # 圆：在 z=plane_z_m 平面上
    cx, cy = circle_center_m
    # 圆在图像上的半径（像素）： real_r / z * f
    fx = (K[0, 0] + K[1, 1]) / 2.0
    r_px = int((circle_radius_m / plane_z_m) * fx)
    center_px = world_to_pixel(cx, cy, plane_z_m, K)
    if 0 < r_px < min(width, height) // 2:
        cv2.circle(img, center_px, r_px, (shape_gray,) * 3, -1)
        cv2.circle(img, center_px, r_px, (border_gray,) * 3, 2)

    # 矩形：四个角在 z=plane_z_m
    rx, ry = rect_center_m
    hw, hh = rect_width_m / 2, rect_height_m / 2
    pts_m = [
        (rx - hw, ry - hh),
        (rx + hw, ry - hh),
        (rx + hw, ry + hh),
        (rx - hw, ry + hh),
    ]
    pts_px = [world_to_pixel(x, y, plane_z_m, K) for x, y in pts_m]
    pts = np.array(pts_px, dtype=np.int32)
    cv2.fillPoly(img, [pts], (shape_gray,) * 3)
    cv2.polylines(img, [pts], True, (border_gray,) * 3, 2)

    if add_noise:
        noise = np.random.randint(-8, 9, img.shape, dtype=np.int16)
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    if save_path:
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        cv2.imwrite(save_path, img)
    return img


if __name__ == "__main__":
    path = os.path.join(config.SAMPLE_IMAGES_DIR, "sim_targets.png")
    img = generate_sim_image(
        plane_z_m=0.5,
        circle_radius_m=0.05,
        rect_width_m=0.08,
        rect_height_m=0.06,
        save_path=path,
    )
    print("仿真图已保存:", path)
    print("预期: 圆直径 10cm @ 0.5m, 矩形 8x6 cm @ 0.5m")
