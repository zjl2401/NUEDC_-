"""
HOG + 线性 SVM 目标分类示例（适合作为小数据集的基线）

输入:
    - 训练集图像路径列表 + 标签
    - 测试图像路径列表

中间操作:
    1. 将图像统一缩放到固定大小
    2. 提取 HOG 特征向量
    3. 用线性 SVM 拟合分类边界

输出:
    - 训练好的 SVM 模型
    - 对测试集的类别预测结果
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


def load_and_resize_gray(path: Path, size: Tuple[int, int]) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"无法读取图像: {path}")
    return cv2.resize(img, size, interpolation=cv2.INTER_LINEAR)


def build_hog(win_size: Tuple[int, int]) -> cv2.HOGDescriptor:
    return cv2.HOGDescriptor(
        _winSize=win_size,
        _blockSize=(16, 16),
        _blockStride=(8, 8),
        _cellSize=(8, 8),
        _nbins=9,
    )


def extract_hog_features(
    samples: Iterable[ImageSample],
    win_size: Tuple[int, int] = (64, 64),
) -> Tuple[np.ndarray, np.ndarray]:
    hog = build_hog(win_size)
    feats: List[np.ndarray] = []
    labels: List[int] = []

    for s in samples:
        img = load_and_resize_gray(s.path, win_size)
        f = hog.compute(img)
        if f is None:
            continue
        feats.append(f.reshape(-1))
        labels.append(s.label)

    return np.vstack(feats).astype(np.float32), np.array(labels, dtype=np.int32)


def train_linear_svm(features: np.ndarray, labels: np.ndarray) -> svm.SVC:
    clf = svm.LinearSVC()
    clf.fit(features, labels)
    return clf


if __name__ == "__main__":
    # 简单示例: 从两个文件夹 train/class0, train/class1 读取样本训练，再在 test 下做预测
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--train_root", type=str, required=True, help="训练集根目录, 形如 train/class0, train/class1")
    parser.add_argument("--test_root", type=str, required=True, help="测试集根目录, 形如 test/class0, test/class1")
    args = parser.parse_args()

    def collect_samples(root: Path) -> List[ImageSample]:
        samples: List[ImageSample] = []
        for label, sub in enumerate(sorted(p for p in root.iterdir() if p.is_dir())):
            for img_path in sub.glob("*.png"):
                samples.append(ImageSample(path=img_path, label=label))
            for img_path in sub.glob("*.jpg"):
                samples.append(ImageSample(path=img_path, label=label))
        return samples

    train_root = Path(args.train_root)
    test_root = Path(args.test_root)

    train_samples = collect_samples(train_root)
    test_samples = collect_samples(test_root)

    X_train, y_train = extract_hog_features(train_samples)
    X_test, y_test = extract_hog_features(test_samples)

    clf = train_linear_svm(X_train, y_train)
    y_pred = clf.predict(X_test)

    print(classification_report(y_test, y_pred))

