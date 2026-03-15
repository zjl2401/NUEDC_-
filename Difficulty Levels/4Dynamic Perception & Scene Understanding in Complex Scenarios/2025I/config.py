# -*- coding: utf-8 -*-
"""
非接触式控制盘 (2025I) - 配置文件
香橙派 + OpenCV，纯软件模拟：手势识别 → 空间映射 → 控制信号
"""
from __future__ import annotations

# ---------- 视频源与分辨率 ----------
CAM_INDEX = 0
PROC_WIDTH = 640
PROC_HEIGHT = 480
TARGET_FPS = 15

# ---------- 肤色检测（YCrCb，抗光影干扰） ----------
# 肤色在 YCrCb 的典型范围（可根据环境微调）
SKIN_Y_LOW = 0
SKIN_Y_HIGH = 255
SKIN_Cr_LOW = 133
SKIN_Cr_HIGH = 173
SKIN_Cb_LOW = 77
SKIN_Cb_HIGH = 127

# 形态学去噪
SKIN_MORPH_OPEN = (3, 3)   # 去小斑点
SKIN_MORPH_CLOSE = (9, 9)  # 填洞、连成手掌

# ---------- 手部轮廓过滤 ----------
MIN_HAND_AREA = 1500       # 最小手掌面积（像素），过滤噪声
MAX_HAND_AREA = 80000      # 最大面积，避免整屏误检
# 手部轮廓近似：轮廓面积/凸包面积，握拳时更接近 1
FIST_EXTENT_THRESH = 0.75  # 大于此视为握拳
OPEN_EXTENT_THRESH = 0.55  # 小于此视为张开
# 凸包缺陷深度（用于数手指），过小忽略
DEFECT_DEPTH_THRESH = 15

# ---------- 控制映射（图像坐标 → 控制量） ----------
# 光标/参数映射：图像中心为原点，归一化到 [-1, 1] 或 [0, 1]
MAP_DEADZONE = 0.05        # 中心死区，减少抖动
MAP_SMOOTH = 0.25          # 位置平滑系数 (0~1)，越大越平滑、延迟越高
# 虚拟控制盘显示区域（屏幕内的一块矩形）
CONTROL_PANEL_MARGIN = 40  # 控制盘边距
CONTROL_PANEL_ALPHA = 0.85 # 叠加透明度

# ---------- 实时与抗干扰 ----------
# 手部丢失时保持上一帧位置的最大帧数
MAX_TRACK_LOST_FRAMES = 5
# 每 N 帧做一次完整手势分类（其余帧只做位置跟踪，降延迟）
GESTURE_CLASSIFY_EVERY_N = 1

# ---------- 显示与调试 ----------
SHOW_DEBUG_WINDOW = True
SHOW_SKIN_MASK = False     # 是否显示肤色二值图
LOG_LEVEL = "INFO"
