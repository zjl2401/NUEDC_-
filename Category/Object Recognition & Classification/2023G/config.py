# -*- coding: utf-8 -*-
"""
2023 电赛 G 题 - 空地协同智能消防系统
香橙派 + OpenCV 全局配置（纯软件模拟）
"""

# ============ 2D 场景（俯视世界） ============
WORLD_WIDTH = 800   # 世界宽度 px
WORLD_HEIGHT = 600  # 世界高度 px
FPS = 30

# ============ 火源检测（红色光斑 / 发热物体模拟） ============
# HSV 红色双区间
FIRE_HSV_LOW1 = (0, 100, 100)
FIRE_HSV_HIGH1 = (10, 255, 255)
FIRE_HSV_LOW2 = (170, 100, 100)
FIRE_HSV_HIGH2 = (180, 255, 255)
FIRE_MIN_AREA = 150   # 最小连通域面积，过滤噪声
FIRE_MAX_AREA = 50000

# ============ 无人机（上帝视角） ============
UAV_VIEW_SCALE = 1.0   # 俯视图缩放，1=整图即全视野
UAV_DETECT_INTERVAL = 3  # 每 N 帧下发一次火源坐标，降低通信负载

# ============ 地面小车 ============
VEHICLE_SPEED = 3.0       # 像素/帧
VEHICLE_RADIUS = 12       # 碰撞半径
FIRE_ACTION_RADIUS = 40   # 进入该半径内执行灭火
FIRE_ACTION_DURATION = 60 # 灭火动作持续帧数（约 2 秒）

# ============ 障碍物（栅格地图） ============
OBSTACLE_CELL_SIZE = 20   # 栅格大小 px
# 障碍物占世界比例（模拟时随机生成）
OBSTACLE_DENSITY = 0.08

# ============ 通信（模拟 WiFi / LoRa） ============
COMM_USE_SOCKET = False   # True=本机 socket 模拟双端，False=内存 Queue 单进程
COMM_PORT_UAV = 9001      # 无人机端发送
COMM_PORT_GROUND = 9002   # 小车端接收（若用 socket）
COMM_LATENCY_FRAMES = 0   # 模拟延迟：延迟 N 帧后小车才收到
