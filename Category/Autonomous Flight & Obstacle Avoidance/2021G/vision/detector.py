# -*- coding: utf-8 -*-
"""
2021G 植保飞行器 - OpenCV 视觉检测
十字起降点、A 区块（红）、绿色作业区块（HSV/轮廓）。
"""

import cv2
import numpy as np
import config as cfg


def detect_cross(img):
    """
    检测十字起降点中心（白色/浅灰区域重心）。
    返回 (cx, cy) 或 None。
    """
    low = np.array(cfg.CROSS_HSV_LOW)
    high = np.array(cfg.CROSS_HSV_HIGH)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, low, high)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in contours:
        if cv2.contourArea(c) < cfg.MIN_CONTOUR_AREA:
            continue
        M = cv2.moments(c)
        if M["m00"] > 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            return (cx, cy)
    return None


def detect_green_blocks(img):
    """
    检测绿色区块，返回轮廓列表（每个轮廓的中心 (cx,cy) 与面积）。
    """
    low = np.array(cfg.GREEN_HSV_LOW)
    high = np.array(cfg.GREEN_HSV_HIGH)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, low, high)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    result = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < cfg.MIN_CONTOUR_AREA:
            continue
        M = cv2.moments(c)
        if M["m00"] > 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            result.append({"cx": cx, "cy": cy, "area": area})
    return result


def detect_a_block(img):
    """
    检测红色 “A” 区块（作业起点），HSV 双区间。
    返回 (cx, cy) 或 None。
    """
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    low1 = np.array(cfg.A_BLOCK_HSV_LOW1)
    high1 = np.array(cfg.A_BLOCK_HSV_HIGH1)
    low2 = np.array(cfg.A_BLOCK_HSV_LOW2)
    high2 = np.array(cfg.A_BLOCK_HSV_HIGH2)
    m1 = cv2.inRange(hsv, low1, high1)
    m2 = cv2.inRange(hsv, low2, high2)
    mask = cv2.bitwise_or(m1, m2)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best = None
    best_area = 0
    for c in contours:
        area = cv2.contourArea(c)
        if area < cfg.MIN_CONTOUR_AREA:
            continue
        if area > best_area:
            best_area = area
            M = cv2.moments(c)
            if M["m00"] > 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                best = (cx, cy)
    return best
