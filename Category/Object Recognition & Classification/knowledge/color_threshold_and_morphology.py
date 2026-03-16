"""
颜色阈值分割 + 形态学清洗示例

输入:
    - BGR 图像 (numpy.ndarray, shape: [H, W, 3])
    - HSV 颜色区间 (lower_hsv, upper_hsv)

中间操作:
    1. BGR -> HSV 颜色空间转换
    2. 颜色阈值分割得到二值 Mask
    3. 开运算去除小噪点
    4. 闭运算填补目标内部空洞

输出:
    - binary_mask: 清洗后的二值图 (uint8, 0/255)
"""

from typing import Tuple

import cv2
import numpy as np


def color_threshold_with_morphology(
    bgr_image: np.ndarray,
    lower_hsv: Tuple[int, int, int],
    upper_hsv: Tuple[int, int, int],
    kernel_size: int = 5,
) -> np.ndarray:
    if bgr_image is None or bgr_image.size == 0:
        raise ValueError("输入图像为空")

    hsv = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array(lower_hsv, dtype=np.uint8), np.array(upper_hsv, dtype=np.uint8))

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)
    return closed


if __name__ == "__main__":
    # 简单命令行 demo: 读取一张图片并显示中间结果与最终 Mask
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("image_path", type=str, help="输入图片路径")
    parser.add_argument("--hmin", type=int, default=35)
    parser.add_argument("--hmax", type=int, default=85)
    parser.add_argument("--smin", type=int, default=50)
    parser.add_argument("--vmin", type=int, default=50)
    args = parser.parse_args()

    bgr = cv2.imread(args.image_path)
    if bgr is None:
        raise FileNotFoundError(f"无法读取图像: {args.image_path}")

    lower = (args.hmin, args.smin, args.vmin)
    upper = (args.hmax, 255, 255)

    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    raw_mask = cv2.inRange(hsv, np.array(lower, dtype=np.uint8), np.array(upper, dtype=np.uint8))
    cleaned = color_threshold_with_morphology(bgr, lower, upper)

    cv2.imshow("input", bgr)
    cv2.imshow("raw_mask", raw_mask)
    cv2.imshow("cleaned_mask", cleaned)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

