# -*- coding: utf-8 -*-
"""
野生动物巡查系统 - 配置文件
针对：非固定形态目标、低信噪比、远距离小目标、嵌入式低功耗
"""
from __future__ import annotations

# ---------- 摄像头与分辨率（影响功耗与远距离检测） ----------
CAM_INDEX = 0
# 主处理分辨率：降低可省电、提速；提高可利于小目标（按需在 320~640 间权衡）
PROC_WIDTH = 640
PROC_HEIGHT = 480
# 是否启用多尺度：先低分辨率粗检，再高分辨率精检（耗电增加）
MULTI_SCALE_ENABLED = False
# 全分辨率仅用于精检 ROI（若 MULTI_SCALE_ENABLED）
FULL_WIDTH = 1280
FULL_HEIGHT = 720

# ---------- 帧率与功耗 ----------
TARGET_FPS = 10
# 每 N 帧做一次完整检测，其余帧可跳帧或仅做轻量检测
PROCESS_EVERY_N_FRAMES = 1
# 无目标时是否降频检测（省电）
IDLE_SLEEP_FRAMES = 5  # 连续 N 帧无目标后，每 IDLE_SLEEP_FRAMES 帧检测一次

# ---------- 背景建模（应对杂草、树木等复杂背景） ----------
# OpenCV 背景减除器: "MOG2" | "GMG" | "KNN"
BG_SUBTRACTOR = "MOG2"
# MOG2 参数
MOG2_HISTORY = 500
MOG2_VAR_THRESHOLD = 16
MOG2_DETECT_SHADOWS = True
# 学习率 (0~1)，越小背景越稳定、对缓慢变化越不敏感
BG_LEARNING_RATE = 0.001

# ---------- 形态学与去噪 ----------
# 开运算核大小，去除小斑点（杂草、树叶）
MORPH_OPEN_SIZE = (3, 3)
# 闭运算核大小，填洞、连接断裂
MORPH_CLOSE_SIZE = (5, 5)
# 最小连通域面积（像素），过滤噪声
MIN_FOREGROUND_AREA = 80
# 最大单目标面积（避免整片树林被当成一个目标）
MAX_SINGLE_TARGET_AREA = 50000

# ---------- 目标过滤（非固定形态：用运动+几何约束代替固定形状） ----------
# 允许的宽高比范围（外接矩形 max/min 边比，≥1；四足/动物约 1~3.5）
MIN_ASPECT_RATIO = 1.0
MAX_ASPECT_RATIO = 3.5
# 最小外接矩形边长（小目标）
MIN_BBOX_SIDE = 15
# 轮廓近似：用面积比过滤过于“方正”的干扰（如石块）
MIN_EXTENT = 0.1   # 轮廓面积/外接矩形面积 下限
MAX_EXTENT = 1.0   # 上限

# ---------- 多尺度/小目标 ----------
# 图像金字塔层数（0=不缩放）
PYRAMID_LEVELS = 0
# 小目标判定：面积小于此视为“远景小目标”，可启用增强
SMALL_TARGET_AREA_THRESH = 1500

# ---------- 显示与调试 ----------
SHOW_DEBUG_WINDOW = True
SAVE_DETECTION_IMAGES = False
LOG_LEVEL = "INFO"
