# -*- coding: utf-8 -*-
"""
2025电赛C题 - 单目视觉目标物测量 - 全局配置
适用于 Orange Pi RK3588 + OpenCV 纯软件仿真
"""

import os

# 路径配置
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
CALIBRATION_DIR = os.path.join(PROJECT_ROOT, "calibration")   # 标定图/标定结果
SAMPLE_IMAGES_DIR = os.path.join(PROJECT_ROOT, "samples")     # 测试图像

# 相机标定默认参数（无标定文件时使用针孔模型近似）
# 可通过棋盘格标定得到真实值
DEFAULT_FX = 800.0   # 焦距 x (pixels)
DEFAULT_FY = 800.0   # 焦距 y (pixels)
DEFAULT_CX = 320.0   # 主点 x (图像宽一半)
DEFAULT_CY = 240.0   # 主点 y (图像高一半)

# 参考物尺寸 (米)，用于单目测距
# 若场景中有已知尺寸的物体，可据此反推距离
REFERENCE_OBJECT_REAL_HEIGHT_M = 0.1   # 例如 10cm 高的标定块
REFERENCE_OBJECT_REAL_WIDTH_M = 0.1

# 默认相机安装高度（俯视时镜头到测量平面距离，米）
DEFAULT_CAMERA_HEIGHT_M = 0.5

# 边缘检测参数
CANNY_LOW = 50
CANNY_HIGH = 150
CONTOUR_MIN_AREA = 100   # 最小轮廓面积，过滤噪点
CONTOUR_APPROX_EPS = 0.02  # 多边形逼近精度 (周长比例)

# 圆检测参数 (HoughCircles)
DP = 1
MIN_DIST = 50
CIRCLE_PARAM1 = 100
CIRCLE_PARAM2 = 30
MIN_RADIUS = 10
MAX_RADIUS = 300

# 显示与调试
SHOW_DEBUG = True
OUTPUT_DPI = 150  # 保存结果图 DPI
