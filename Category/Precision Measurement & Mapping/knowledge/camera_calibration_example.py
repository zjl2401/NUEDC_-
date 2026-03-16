"""
棋盘格相机内参标定 + 畸变矫正示例

输入:
    - 一组棋盘格标定图片所在目录 (data_root), 命名任意, 常见扩展名 (*.png, *.jpg)
    - 棋盘格内角点数 (cols, rows), 如 9x6

中间操作:
    1. 在每张图中检测棋盘格角点 (cv2.findChessboardCorners)
    2. 聚合所有图像的 2D 像素坐标 + 理想 3D 角点坐标, 调用 cv2.calibrateCamera
    3. 使用标定结果对一张示例图做畸变矫正 (cv2.undistort)

输出:
    - 打印相机矩阵 K、畸变系数 dist
    - 在磁盘保存一张原图与矫正后对比图 (undistorted.png)
"""

from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np


def collect_calib_images(root: Path) -> List[Path]:
    exts = ("*.png", "*.jpg", "*.jpeg", "*.bmp")
    imgs: List[Path] = []
    for ext in exts:
        imgs.extend(root.glob(ext))
    return sorted(imgs)


def build_object_points(board_size: Tuple[int, int], square_size: float = 1.0) -> np.ndarray:
    cols, rows = board_size
    objp = np.zeros((rows * cols, 3), np.float32)
    # 约定棋盘格在 XY 平面, Z=0
    xs, ys = np.meshgrid(np.arange(cols), np.arange(rows))
    objp[:, 0] = xs.reshape(-1) * square_size
    objp[:, 1] = ys.reshape(-1) * square_size
    return objp


def calibrate_from_folder(
    data_root: Path,
    board_size: Tuple[int, int],
    square_size: float = 1.0,
):
    image_paths = collect_calib_images(data_root)
    if not image_paths:
        raise FileNotFoundError(f"在 {data_root} 下未找到任何标定图片")

    obj_points: List[np.ndarray] = []  # 3D 点 (世界坐标)
    img_points: List[np.ndarray] = []  # 2D 点 (像素坐标)

    objp = build_object_points(board_size, square_size)

    gray_shape = None

    for p in image_paths:
        img = cv2.imread(str(p))
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray_shape = gray.shape[::-1]  # (w, h)
        ret, corners = cv2.findChessboardCorners(gray, board_size, None)
        if not ret:
            print(f"警告: {p} 中未找到棋盘格角点, 跳过")
            continue

        # 角点精细化
        corners2 = cv2.cornerSubPix(
            gray,
            corners,
            winSize=(11, 11),
            zeroZone=(-1, -1),
            criteria=(cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001),
        )

        obj_points.append(objp)
        img_points.append(corners2)

    if not obj_points:
        raise RuntimeError("没有任何有效角点, 无法标定")

    assert gray_shape is not None
    ret, K, dist, rvecs, tvecs = cv2.calibrateCamera(
        obj_points,
        img_points,
        gray_shape,
        None,
        None,
    )

    print("标定 RMS 误差:", ret)
    print("相机矩阵 K:\n", K)
    print("畸变系数 dist:\n", dist.ravel())

    # 使用第一张图片做畸变矫正示例
    sample_img = cv2.imread(str(image_paths[0]))
    undistorted = cv2.undistort(sample_img, K, dist)
    out_path = data_root / "undistorted.png"
    cv2.imwrite(str(out_path), undistorted)
    print(f"示例畸变矫正结果已保存: {out_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--data_root", type=str, required=True, help="棋盘格标定图片目录")
    parser.add_argument("--cols", type=int, required=True, help="棋盘格内角点列数")
    parser.add_argument("--rows", type=int, required=True, help="棋盘格内角点行数")
    parser.add_argument("--square_size", type=float, default=1.0, help="棋盘格实际方格边长(单位自定)")
    args = parser.parse_args()

    calibrate_from_folder(
        Path(args.data_root),
        board_size=(args.cols, args.rows),
        square_size=args.square_size,
    )

