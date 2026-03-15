# -*- coding: utf-8 -*-
"""
单目深度/距离与几何尺寸计算
依据：针孔模型 + 已知参考尺寸 或 已知平面距离
"""

import numpy as np
from typing import Tuple, Optional
import config


def distance_from_reference_size(
    focal_length_px: float,
    real_size_m: float,
    pixel_size_px: float,
) -> float:
    """
    单目测距：已知物体实际尺寸与在图像中的像素尺寸，求距离。
    distance = (real_size * focal_length) / pixel_size
    单位：米。
    """
    if pixel_size_px <= 0:
        return float("inf")
    return (real_size_m * focal_length_px) / pixel_size_px


def real_size_from_distance(
    distance_m: float,
    focal_length_px: float,
    pixel_size_px: float,
) -> float:
    """
    已知距离和焦距，从像素尺寸反推真实尺寸。
    real_size = (distance * pixel_size) / focal_length
    单位：米。
    """
    if focal_length_px <= 0:
        return 0.0
    return (distance_m * pixel_size_px) / focal_length_px


def pixel_size_to_world_at_plane(
    pixel_length: float,
    plane_z_m: float,
    K: np.ndarray,
    length_in_image_along: str = "x",
) -> float:
    """
    在已知平面 z = plane_z_m 上，将一段像素长度转换为世界坐标长度（米）。
    length_in_image_along: "x" 或 "y"，表示该像素长度沿图像 x 或 y 方向。
    """
    fx, fy = K[0, 0], K[1, 1]
    if length_in_image_along == "x":
        return (pixel_length * plane_z_m) / fx
    return (pixel_length * plane_z_m) / fy


def world_size_to_pixel_at_plane(
    world_length_m: float,
    plane_z_m: float,
    K: np.ndarray,
    along: str = "x",
) -> float:
    """世界长度（米）在平面 z 上对应的像素长度。"""
    fx, fy = K[0, 0], K[1, 1]
    if along == "x":
        return (world_length_m * fx) / plane_z_m
    return (world_length_m * fy) / plane_z_m


def measure_circle(
    center_px: Tuple[float, float],
    radius_px: float,
    K: np.ndarray,
    distance_m: Optional[float] = None,
    real_diameter_m: Optional[float] = None,
) -> dict:
    """
    圆的测量结果。
    若给 distance_m：用距离+焦距推算直径（米）；
    若给 real_diameter_m：用真实直径反推距离（米）。
    """
    fx = (K[0, 0] + K[1, 1]) / 2.0
    diameter_px = 2.0 * radius_px
    out = {
        "center_px": center_px,
        "radius_px": radius_px,
        "diameter_px": diameter_px,
        "distance_m": None,
        "diameter_m": None,
    }
    if distance_m is not None and distance_m > 0:
        out["distance_m"] = distance_m
        out["diameter_m"] = real_size_from_distance(
            distance_m, fx, diameter_px
        )
    elif real_diameter_m is not None and real_diameter_m > 0:
        out["diameter_m"] = real_diameter_m
        out["distance_m"] = distance_from_reference_size(
            fx, real_diameter_m, diameter_px
        )
    return out


def measure_rectangle(
    center_px: Tuple[float, float],
    width_px: float,
    height_px: float,
    K: np.ndarray,
    distance_m: Optional[float] = None,
    real_width_m: Optional[float] = None,
    real_height_m: Optional[float] = None,
) -> dict:
    """
    矩形测量。若给 distance_m，用焦距推算宽高（米）；
    若给 real_width_m/real_height_m，反推距离（米）。
    """
    fx, fy = K[0, 0], K[1, 1]
    out = {
        "center_px": center_px,
        "width_px": width_px,
        "height_px": height_px,
        "distance_m": None,
        "width_m": None,
        "height_m": None,
    }
    if distance_m is not None and distance_m > 0:
        out["distance_m"] = distance_m
        out["width_m"] = real_size_from_distance(distance_m, fx, width_px)
        out["height_m"] = real_size_from_distance(distance_m, fy, height_px)
    elif real_width_m is not None and real_width_m > 0:
        out["width_m"] = real_width_m
        out["distance_m"] = distance_from_reference_size(
            fx, real_width_m, width_px
        )
        if real_height_m is not None and real_height_m > 0:
            out["height_m"] = real_height_m
            d2 = distance_from_reference_size(fy, real_height_m, height_px)
            if out["distance_m"] is not None:
                out["distance_m"] = (out["distance_m"] + d2) / 2
        elif out["distance_m"] is not None:
            out["height_m"] = real_size_from_distance(
                out["distance_m"], fy, height_px
            )
    elif real_height_m is not None and real_height_m > 0:
        out["height_m"] = real_height_m
        out["distance_m"] = distance_from_reference_size(
            fy, real_height_m, height_px
        )
        out["width_m"] = real_size_from_distance(
            out["distance_m"], fx, width_px
        )
    return out
