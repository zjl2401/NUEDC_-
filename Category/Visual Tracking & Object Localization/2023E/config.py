# -*- coding: utf-8 -*-
"""激光追踪系统 - 全局配置（OpenCV + 香橙派）"""

# ============ 摄像头 ============
CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
TARGET_FPS = 30
# 关键：降低曝光，避免激光过曝成白点（按实际摄像头调整）
EXPOSURE = -8  # 负值降低曝光，具体范围视驱动而定

# ============ 屏幕/透视校正 ============
# 校正后虚拟屏幕分辨率（与舵机标定一致）
SCREEN_W = 320
SCREEN_H = 240

# ============ HSV 颜色范围 ============
# 红色在 HSV 中 H 约 0~10 和 170~180
RED_LOWER_1 = (0, 100, 100)
RED_UPPER_1 = (10, 255, 255)
RED_LOWER_2 = (170, 100, 100)
RED_UPPER_2 = (180, 255, 255)

# 绿色激光
GREEN_LOWER = (35, 100, 100)
GREEN_UPPER = (85, 255, 255)

# 黑框检测（用于透视校正 / 画圈）
BLACK_LOWER = (0, 0, 0)
BLACK_UPPER = (180, 255, 30)

# ============ 目标过滤 ============
MIN_LASER_AREA = 10
MAX_LASER_AREA = 500

# ============ 控制 ============
# 死区：误差小于此像素不动作，减少云台抖动
DEADZONE_PX = 2

# 增量式 PID
PID_KP = 0.15
PID_KI = 0.02
PID_KD = 0.05
PID_MAX_OUTPUT = 1.0

# 预测：用前几帧做线性预测（动态追踪）
PREDICT_FRAMES = 2

# ============ 舵机（香橙派 GPIO/PWM） ============
# 角度范围（度）
PAN_MIN = 0
PAN_MAX = 180
TILT_MIN = 0
TILT_MAX = 180
# 中位（屏幕中心对应角度，需标定）
PAN_CENTER = 90
TILT_CENTER = 90
# 屏幕像素到角度的比例（标定后填写：每像素对应多少度）
SCREEN_TO_PAN = 0.3   # 屏幕水平 1 像素 -> 舵机约 0.3 度
SCREEN_TO_TILT = 0.3
# PWM 脉宽范围 (us)，依舵机规格修改
SERVO_MIN_US = 500
SERVO_MAX_US = 2500

# 香橙派 PWM 引脚（以 Orange Pi 5 / Zero2 常见为例，按实际板子改）
# Orange Pi 5: 可用 GPIO 或 硬件 PWM 脚
PAN_PWM_PIN = "PA0"   # 示例，请查板子引脚图
TILT_PWM_PIN = "PA1"
