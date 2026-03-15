# -*- coding: utf-8 -*-
"""2025E 视觉闭环控制 - 全局配置（纯软件模拟，OpenCV）"""

# ============ 画布与仿真 ============
CANVAS_W = 640
CANVAS_H = 480
SIM_FPS = 30

# ============ 多目标颜色 HSV 范围 ============
# 红 (目标 0)
RED_LOWER_1 = (0, 100, 100)
RED_UPPER_1 = (10, 255, 255)
RED_LOWER_2 = (170, 100, 100)
RED_UPPER_2 = (180, 255, 255)

# 绿 (目标 1 / 激光点)
GREEN_LOWER = (35, 80, 80)
GREEN_UPPER = (85, 255, 255)

# 蓝 (目标 2)
BLUE_LOWER = (100, 80, 80)
BLUE_UPPER = (130, 255, 255)

# 黄 (目标 3)
YELLOW_LOWER = (20, 100, 100)
YELLOW_UPPER = (35, 255, 255)

# 青 (目标 4)
CYAN_LOWER = (85, 80, 80)
CYAN_UPPER = (100, 255, 255)

# 目标过滤
MIN_BLOB_AREA = 50
MAX_BLOB_AREA = 3000

# ============ 控制 ============
DEADZONE_PX = 3
PID_KP = 0.18
PID_KI = 0.02
PID_KD = 0.06
PID_MAX_OUTPUT = 1.2

# 预测
PREDICT_FRAMES = 3
KALMAN_PROCESS_NOISE = 0.03
KALMAN_MEASURE_NOISE = 0.5

# ============ 利萨如图形参数 ============
# x = A*sin(a*t + d), y = B*sin(b*t)
LISSAJOUS_A = 150
LISSAJOUS_B = 120
LISSAJOUS_A_FREQ = 2.0   # a
LISSAJOUS_B_FREQ = 3.0   # b
LISSAJOUS_PHASE = 0.0    # d (弧度)
LISSAJOUS_SPEED = 0.8    # 时间缩放

# ============ 动态环境干扰（模拟） ============
# 背景闪烁：每 N 帧随机亮度
FLICKER_PROB = 0.08
FLICKER_ALPHA_MIN = 0.3
FLICKER_ALPHA_MAX = 0.9

# 遮挡：随机矩形遮挡概率与持续时间（帧数）
OCCLUSION_PROB = 0.02
OCCLUSION_DURATION = 15
OCCLUSION_MAX_SIZE = 80

# 光照渐变：周期性强弱
LIGHT_SINE_AMPLITUDE = 0.25  # 亮度变化幅度
LIGHT_SINE_PERIOD = 120      # 周期（帧）
