#基础 HSV 色彩空间分割
import cv2
import numpy as np

def extract_masks(frame):
    # 1. 转换颜色空间
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # --- 红色双段分割 ---
    # 第一段：0-10 度 (深红)
    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([10, 255, 255])
    # 第二段：170-180 度 (粉红/鲜红)
    lower_red2 = np.array([170, 100, 100])
    upper_red2 = np.array([180, 255, 255])
    
    mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
    # 取并集 (OR 操作)
    red_mask = cv2.bitwise_or(mask_red1, mask_red2)
    
    # --- 绿色单段分割 ---
    # 绿色通常在 35-85 度左右
    lower_green = np.array([35, 100, 100])
    upper_green = np.array([85, 255, 255])
    green_mask = cv2.inRange(hsv, lower_green, upper_green)
    
    return red_mask, green_mask