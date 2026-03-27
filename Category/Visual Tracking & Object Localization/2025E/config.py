# -*- coding: utf-8 -*-
"""2025E 视觉闭环控制 - 全局配置（纯软件模拟，OpenCV）"""

# ============ 画布与仿真 ============
CANVAS_W = 640
CANVAS_H = 480
SIM_FPS = 30

# ============ 真机摄像头（可选） ============
CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
EXPOSURE = -6  # 视摄像头驱动而定，不支持时会被忽略

# ============ 真机透视校正（可选） ============
# 若摄像头对准有黑框的“屏幕/靶面”，可启用透视矫正，把黑框映射到标准坐标
USE_PERSPECTIVE = True
SCREEN_W = 640
SCREEN_H = 480

# ROI：锁定目标后只在局部区域检测（提高速度与稳定性）
ROI_ENABLED = True
ROI_SIZE = 240

# ROI 回退：丢失时扩大 ROI / 退回全图的策略
ROI_GROW_ON_LOST = True
ROI_SIZE_MAX = 420
ROI_GROW_STEP = 60
LOST_TO_FULLFRAME_FRAMES = 8

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

# 目标重捕获与抗干扰
MAX_JUMP_PX = 120  # 单帧最大允许跳变距离（超过视为可疑，进入重捕获/降权）
CONFIRM_HITS_FRAMES = 2  # 连续检测到多少帧才认为“稳定锁定”

# ============ 控制 ============
DEADZONE_PX = 3
PID_KP = 0.18
PID_KI = 0.02
PID_KD = 0.06
PID_MAX_OUTPUT = 1.2

# ============ 命中/计分 ============
# 仿真：aim 点 = follower 十字；真机：默认按“目标落在画面中心”作为命中（相机中心即准星）
HIT_RADIUS_PX = 18
HIT_HOLD_FRAMES = 6     # 连续命中多少帧算一次“击中”
HIT_COOLDOWN_FRAMES = 10  # 两次击中之间的冷却帧，避免重复计分
SCORE_PER_HIT = 10

# ============ 真机云台/舵机（可选） ============
# 舵机角度限制与中心
PAN_MIN = 0.0
PAN_MAX = 180.0
TILT_MIN = 0.0
TILT_MAX = 180.0
PAN_CENTER = 90.0
TILT_CENTER = 90.0

# 像素误差 -> 舵机角度增量 的映射（需标定）
# 例如：屏幕坐标偏移 100px，需要转多少度？
PIXEL_TO_PAN = 0.03
PIXEL_TO_TILT = 0.03

# 舵机脉宽范围（us）
SERVO_MIN_US = 500
SERVO_MAX_US = 2500

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
