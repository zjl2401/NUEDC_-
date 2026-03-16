#CLAHE 光照归一化
import cv2
import numpy as np

def apply_clahe_to_hsv(bgr_frame):
    # 1. 输入：原始 BGR 图像
    # 2. 转换：从 BGR 空间转换到 HSV 空间
    hsv = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2HSV)
    
    # 3. 分离通道：H（色调）, S（饱和度）, V（亮度）
    h, s, v = cv2.split(hsv)
    
    # 4. 配置 CLAHE 对象
    # clipLimit: 限制对比度的阈值，越高对比度越强
    # tileGridSize: 将图像拆分成 8x8 的小方格分别计算
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    
    # 5. 操作：仅对 V (亮度) 通道应用 CLAHE
    v_enhanced = clahe.apply(v)
    
    # 6. 合并通道：将增强后的 V 通道合并回去
    hsv_final = cv2.merge((h, s, v_enhanced))
    
    # 7. 输出：转回 BGR 方便后续显示或处理
    result = cv2.cvtColor(hsv_final, cv2.COLOR_HSV2BGR)
    return result

# 测试代码
cap = cv2.VideoCapture(0)
while True:
    ret, frame = cap.read()
    if not ret: break
    
    enhanced_frame = apply_clahe_to_hsv(frame)
    
    cv2.imshow('Original', frame)
    cv2.imshow('CLAHE Enhanced', enhanced_frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
cap.release()
cv2.destroyAllWindows()
'''
问题： 普通的直方图均衡化会增强全局对比度，容易让暗部噪点飞起。CLAHE（限制对比度的自适应直方图均衡化）将图像划分为小块（Tiles），分别均衡，并裁剪直方图防止过度增强。
输入： HSV 图像。
操作： 提取 V（明度）通道，应用 CLAHE 算法。
输出： 亮度分布更均匀的图像。
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    hsv[:, :, 2] = clahe.apply(hsv[:, :, 2]) # 只对亮度通道操作，保持颜色不变
在视觉检测中，我们通常不直接对彩色图做均衡化（那会导致色彩失真），而是先转到 HSV 或 LAB 空间，只对亮度通道（V 或 L）进行增强。
CLAHE 的两个关键参数（调优重点）：
    clipLimit (默认 40, 建议 2.0-3.0):
        如果你发现画面噪点太多，调低它。
        如果你发现画面依然很暗，对比度拉不开，调高它。
    tileGridSize (默认 8x8):
        如果光照分布非常不均匀（比如一半死黑一半暴晒），可以尝试 (16, 16)，这会让局部调整更加细腻。
'''