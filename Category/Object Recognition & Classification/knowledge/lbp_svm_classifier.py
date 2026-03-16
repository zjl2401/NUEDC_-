"""
LBP 纹理特征 + 线性 SVM 分类示例

适用场景:
    - 纹理差异明显的目标分类 (如不同材质、印刷/未印刷、粗糙/光滑等)

输入:
    - 训练集图像路径列表 + 标签 (目录结构形如 train/class0, train/class1, ...)
    - 测试集图像路径列表

中间操作:
    1. 灰度化 + 统一缩放
    2. 计算每张图像的 LBP 图
    3. 统计 LBP 直方图作为特征向量
    4. 使用线性 SVM 进行训练与预测

输出:
    - 训练好的 SVM 模型 (内存中)
    - 在终端打印测试集分类报告 (precision/recall/F1)
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

import cv2
import numpy as np
from sklearn import svm
from sklearn.metrics import classification_report


@dataclass
class ImageSample:
    path: Path
    label: int


def load_gray(path: Path, size: Tuple[int, int]) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"无法读取图像: {path}")
    if size is not None:
        img = cv2.resize(img, size, interpolation=cv2.INTER_LINEAR)
    return img


def lbp_image(gray: np.ndarray, radius: int = 1, neighbors: int = 8) -> np.ndarray:
    """
    简易 LBP 实现 (非严格 uniform 模式，仅用于教学演示)
    """
    h, w = gray.shape
    dst = np.zeros((h - 2 * radius, w - 2 * radius), dtype=np.uint8)

    center = gray[radius : h - radius, radius : w - radius]
    idx = 0
    for dy, dx in [
        (-1, -1),
        (-1, 0),
        (-1, 1),
        (0, 1),
        (1, 1),
        (1, 0),
        (1, -1),
        (0, -1),
    ][:neighbors]:
        neighbor = gray[radius + dy : h - radius + dy, radius + dx : w - radius + dx]
        dst |= ((neighbor >= center) << idx).astype(np.uint8)
        idx += 1

    return dst


def lbp_histogram(img: np.ndarray, num_bins: int = 256) -> np.ndarray:
    hist, _ = np.histogram(img.ravel(), bins=num_bins, range=(0, num_bins), density=True)
    return hist.astype(np.float32)


def extract_lbp_features(
    samples: Iterable[ImageSample],
    size: Tuple[int, int] = (64, 64),
) -> Tuple[np.ndarray, np.ndarray]:
    feats: List[np.ndarray] = []
    labels: List[int] = []

    for s in samples:
        gray = load_gray(s.path, size)
        lbp = lbp_image(gray, radius=1, neighbors=8)
        hist = lbp_histogram(lbp, num_bins=256)
        feats.append(hist)
        labels.append(s.label)

    return np.vstack(feats), np.array(labels, dtype=np.int32)


def train_linear_svm(features: np.ndarray, labels: np.ndarray) -> svm.SVC:
    clf = svm.LinearSVC()
    clf.fit(features, labels)
    return clf


if __name__ == "__main__":
    # 示例: 从 train/class0, train/class1 训练, 在 test/class0, test/class1 上评估
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--train_root", type=str, required=True)
    parser.add_argument("--test_root", type=str, required=True)
    args = parser.parse_args()

    def collect_samples(root: Path) -> List[ImageSample]:
        res: List[ImageSample] = []
        for label, sub in enumerate(sorted(p for p in root.iterdir() if p.is_dir())):
            for ext in ("*.png", "*.jpg", "*.jpeg", "*.bmp"):
                for img_path in sub.glob(ext):
                    res.append(ImageSample(path=img_path, label=label))
        return res

    train_root = Path(args.train_root)
    test_root = Path(args.test_root)

    train_samples = collect_samples(train_root)
    test_samples = collect_samples(test_root)

    X_train, y_train = extract_lbp_features(train_samples)
    X_test, y_test = extract_lbp_features(test_samples)

    clf = train_linear_svm(X_train, y_train)
    y_pred = clf.predict(X_test)

    print(classification_report(y_test, y_pred))

