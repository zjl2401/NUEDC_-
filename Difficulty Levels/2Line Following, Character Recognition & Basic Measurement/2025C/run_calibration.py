# -*- coding: utf-8 -*-
"""
使用棋盘格图像进行相机标定，保存内参供测量模块使用。
用法：将多张不同角度的棋盘格照片放入 calibration/ 目录，命名为 1.jpg, 2.jpg, ...
或：python run_calibration.py <图1> <图2> ...
"""

import os
import sys
import glob
import config
from camera_calibration import calibrate_from_checkerboard

# 棋盘格内角点（不含最外圈）
PATTERN_SIZE = (9, 6)
SQUARE_SIZE_M = 0.025  # 方格边长 2.5cm


def main():
    calibration_dir = config.CALIBRATION_DIR
    os.makedirs(calibration_dir, exist_ok=True)

    if len(sys.argv) > 1:
        image_paths = [p for p in sys.argv[1:] if os.path.isfile(p)]
    else:
        image_paths = []
        for ext in ("*.jpg", "*.png", "*.jpeg"):
            image_paths.extend(glob.glob(os.path.join(calibration_dir, ext)))
        image_paths = sorted(image_paths)

    if not image_paths:
        print("请将棋盘格标定图放入 calibration/ 或使用: python run_calibration.py img1.jpg img2.jpg ...")
        return

    try:
        K, dist, err = calibrate_from_checkerboard(
            image_paths,
            pattern_size=PATTERN_SIZE,
            square_size=SQUARE_SIZE_M,
            save_path=os.path.join(calibration_dir, "camera_params.npz"),
        )
        print("标定完成。内参矩阵 K:")
        print(K)
        print("畸变系数:", dist.ravel())
        print("平均重投影误差 (像素):", err)
    except Exception as e:
        print("标定失败:", e)


if __name__ == "__main__":
    main()
