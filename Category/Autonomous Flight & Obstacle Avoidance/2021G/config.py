# -*- coding: utf-8 -*-
"""
2021 国赛 G 题 - 植保飞行器 (Plant Protection UAV)
香橙派 + OpenCV 全局配置（纯软件模拟）
"""

# 俯视地图尺寸（像素）
MAP_WIDTH = 800
MAP_HEIGHT = 600

# 十字起降点：中心坐标与臂长（像素）
CROSS_CENTER_X = 400
CROSS_CENTER_Y = 300
CROSS_ARM_LEN = 40
CROSS_ARM_WIDTH = 8

# 区块网格（行 x 列），每块边长（像素）
GRID_ROWS = 4
GRID_COLS = 6
CELL_SIZE = 80

# 巡航高度（模拟中用“俯视比例”表示，实际赛题为 150±10 cm）
CRUISE_ALTITUDE_PX = 1.0   # 俯视时视为 1:1，仅用于逻辑
TARGET_ALTITUDE_CM = 150

# 作业总时间上限（秒）
MISSION_TIMEOUT_S = 360

# 降落误差阈值（像素，对应 ±10 cm）
LANDING_ERROR_THRESHOLD_PX = 12

# ----- 视觉检测 HSV（OpenCV: H 0-180, S/V 0-255） -----
# 十字起降点：白色/浅灰
CROSS_HSV_LOW = (0, 0, 200)
CROSS_HSV_HIGH = (180, 40, 255)

# 绿色作业区块
GREEN_HSV_LOW = (35, 80, 80)
GREEN_HSV_HIGH = (85, 255, 255)

# “A” 区块：红色（作业起点）
A_BLOCK_HSV_LOW1 = (0, 100, 100)
A_BLOCK_HSV_HIGH1 = (10, 255, 255)
A_BLOCK_HSV_LOW2 = (170, 100, 100)
A_BLOCK_HSV_HIGH2 = (180, 255, 255)

# 轮廓最小面积，过滤噪声
MIN_CONTOUR_AREA = 200

# 摄像头/模拟帧率
FPS = 25
