# -*- coding: utf-8 -*-
"""电器识别：基于存储的特征模板进行最近邻匹配（可扩展为简单学习）"""

import numpy as np
import json
import os
from config import APPLIANCE_NAMES


# 特征向量顺序（用于欧氏距离）
FEATURE_KEYS = ["rms_ma", "phase_deg", "pf", "h3_ratio", "h5_ratio", "h7_ratio"]
# 归一化权重（量纲不同，需缩放）
WEIGHTS = np.array([1.0 / 500.0, 1.0 / 90.0, 1.0, 10.0, 10.0, 10.0], dtype=np.float64)


def feature_vector(features: dict) -> np.ndarray:
    """将 extract_features 返回的 dict 转为固定顺序的向量。"""
    return np.array([float(features.get(k, 0)) for k in FEATURE_KEYS], dtype=np.float64)


def weighted_distance(a: np.ndarray, b: np.ndarray) -> float:
    """加权欧氏距离。"""
    d = (a - b) * WEIGHTS
    return float(np.sqrt(np.sum(d * d)))


class ApplianceClassifier:
    """学习模式：存储各电器特征；识别模式：最近邻匹配。"""

    def __init__(self, model_path: str = "appliance_model.json"):
        self.model_path = model_path
        self.templates = {}
        self.means = {}
        self.is_fitted = False

    def add_sample(self, appliance_id: int, features: dict) -> None:
        """学习：添加一个样本。"""
        if appliance_id not in self.templates:
            self.templates[appliance_id] = []
        self.templates[appliance_id].append(feature_vector(features))

    def fit(self) -> None:
        """学习结束：对每类取平均特征作为模板。"""
        self.means = {}
        for aid, vecs in self.templates.items():
            self.means[aid] = np.mean(vecs, axis=0)
        self.is_fitted = len(self.means) > 0

    def clear(self) -> None:
        """清除所有存储的特征（题目：学习前清除）。"""
        self.templates = {}
        self.means = {}
        self.is_fitted = False

    def predict_single(self, features: dict) -> int:
        """识别：返回最近邻的电器编号，若无模板返回 0。"""
        if not getattr(self, "is_fitted", False) or not self.means:
            return 0
        x = feature_vector(features)
        best_id, best_dist = 0, float("inf")
        for aid, mu in self.means.items():
            d = weighted_distance(x, mu)
            if d < best_dist:
                best_dist, best_id = d, aid
        return best_id

    def predict_multi(self, features: dict, threshold: float = 2.0) -> list:
        """
        多电器同时用电：返回所有距离小于 threshold 的电器编号。
        threshold 可调，用于“随机增减在用电器”的分解。
        """
        if not getattr(self, "is_fitted", False) or not self.means:
            return []
        x = feature_vector(features)
        active = []
        for aid, mu in self.means.items():
            if weighted_distance(x, mu) < threshold:
                active.append(aid)
        return sorted(active)

    def save(self, path: str = None) -> None:
        path = path or self.model_path
        data = {
            "means": {str(k): v.tolist() for k, v in self.means.items()},
            "is_fitted": getattr(self, "is_fitted", False),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self, path: str = None) -> None:
        path = path or self.model_path
        if not os.path.isfile(path):
            self.means = {}
            self.is_fitted = False
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.means = {int(k): np.array(v) for k, v in data.get("means", {}).items()}
        self.is_fitted = data.get("is_fitted", False)


def get_appliance_name(appliance_id: int) -> str:
    return APPLIANCE_NAMES.get(appliance_id, f"未知({appliance_id})")
