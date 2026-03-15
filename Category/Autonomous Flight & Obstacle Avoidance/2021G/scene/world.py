# -*- coding: utf-8 -*-
"""
2021G 植保飞行器 - 2D 俯视世界
十字起降点、A 区块、绿色作业区、渲染与 UAV 视图。
"""

import cv2
import numpy as np
import config as cfg


def draw_cross(img, cx, cy, arm_len, width, color=(240, 240, 240)):
    """绘制十字起降点。"""
    h, w = img.shape[:2]
    # 横臂
    x1 = max(0, int(cx - arm_len))
    x2 = min(w, int(cx + arm_len))
    y1 = max(0, int(cy - width // 2))
    y2 = min(h, int(cy + width // 2))
    cv2.rectangle(img, (x1, y1), (x2, y2), color, -1)
    # 竖臂
    x1 = max(0, int(cx - width // 2))
    x2 = min(w, int(cx + width // 2))
    y1 = max(0, int(cy - arm_len))
    y2 = min(h, int(cy + arm_len))
    cv2.rectangle(img, (x1, y1), (x2, y2), color, -1)


def build_map(a_block_pos, green_cells, seed=None):
    """
    构建俯视地图：背景灰 + 十字 + A 区块(红) + 绿色作业区块。
    a_block_pos: (row, col) 或 None
    green_cells: list of (row, col) 需要播撒的绿色区块
    """
    img = np.zeros((cfg.MAP_HEIGHT, cfg.MAP_WIDTH, 3), dtype=np.uint8)
    img[:] = (60, 60, 60)

    # 网格参数
    rows, cols = cfg.GRID_ROWS, cfg.GRID_COLS
    cw = cfg.CELL_SIZE
    ox = (cfg.MAP_WIDTH - cols * cw) // 2
    oy = (cfg.MAP_HEIGHT - rows * cw) // 2

    # 所有格子先画成深色
    for r in range(rows):
        for c in range(cols):
            x1 = ox + c * cw
            y1 = oy + r * cw
            cv2.rectangle(img, (x1, y1), (x1 + cw, y1 + cw), (80, 80, 80), -1)
            cv2.rectangle(img, (x1, y1), (x1 + cw, y1 + cw), (100, 100, 100), 1)

    # A 区块：红色
    if a_block_pos is not None:
        ar, ac = a_block_pos
        x1 = ox + ac * cw
        y1 = oy + ar * cw
        cv2.rectangle(img, (x1, y1), (x1 + cw, y1 + cw), (0, 0, 220), -1)
        cv2.putText(img, "A", (x1 + cw//2 - 12, y1 + cw//2 + 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    # 绿色作业区块
    for (r, c) in green_cells:
        x1 = ox + c * cw
        y1 = oy + r * cw
        cv2.rectangle(img, (x1, y1), (x1 + cw, y1 + cw), (0, 180, 0), -1)

    # 十字起降点（叠在最上）
    draw_cross(img, cfg.CROSS_CENTER_X, cfg.CROSS_CENTER_Y,
               cfg.CROSS_ARM_LEN, cfg.CROSS_ARM_WIDTH)

    return img


def get_uav_view(full_map, uav_x, uav_y, view_radius=120):
    """从俯视图中裁剪 UAV 当前位置周围的视野（模拟机载摄像头俯视）。"""
    h, w = full_map.shape[:2]
    x1 = int(max(0, uav_x - view_radius))
    y1 = int(max(0, uav_y - view_radius))
    x2 = int(min(w, uav_x + view_radius))
    y2 = int(min(h, uav_y + view_radius))
    return full_map[y1:y2, x1:x2].copy()


def get_cell_center(row, col):
    """返回区块 (row,col) 在俯视图上的中心像素坐标。"""
    cw = cfg.CELL_SIZE
    ox = (cfg.MAP_WIDTH - cfg.GRID_COLS * cw) // 2
    oy = (cfg.MAP_HEIGHT - cfg.GRID_ROWS * cw) // 2
    cx = ox + col * cw + cw // 2
    cy = oy + row * cw + cw // 2
    return cx, cy
