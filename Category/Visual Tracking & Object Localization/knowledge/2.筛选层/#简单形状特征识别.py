#简单形状特征识别
'''
目标： 不靠 AI 怎么区分球（Circle）和条状物（Strip）？
    指标 1：圆度（Circularity）公式：$C = \frac{4\pi \times \text{Area}}{\text{Perimeter}^2}$
        标准圆的 $C$ 接近 1.0。
        越细长的物体 $C$ 越小。
    指标 2：长宽比（Aspect Ratio）
        利用最小外接矩形（minAreaRect）的长短轴比值。

    def _contour_shape_hint(cnt):
    area = cv2.contourArea(cnt)
    perimeter = cv2.arcLength(cnt, True)
    circularity = (4 * np.pi * area) / (perimeter**2) if perimeter > 0 else 0
    
    if circularity > 0.8: return "circle"
    if circularity < 0.3: return "strip"
    return "other"
深入理解：为什么这些特征能分出形状？
    圆度 (Circularity) 的本质：
        在周长固定的情况下，圆形的面积是最大的。
        圆： 计算结果接近 1.0。
        正方形： 计算结果约为 0.78。
        细长条： 随着周长暴增而面积增长缓慢，结果会趋近 0.1 甚至更低。
    长宽比 (Aspect Ratio) 的本质：
        它不关心轮廓有多弯曲，只看它最长的地方和最宽的地方的比值。
        这在工业分拣中非常有用，例如区分“螺丝（长条）”和“垫圈（圆/环）”。
你需要注意的“坑” (代码鲁棒性)
    在 vision_2025.py 的实际应用中，单靠这两个数值可能会误判。例如：
        遮挡问题： 如果一个圆形目标被挡住了一半，它的圆度会瞬间崩塌，从 0.9 降到 0.4。
        噪点问题： 极小的色块（面积只有几个像素）可能会产生离谱的圆度值。
    因此，代码中通常还会加入面积过滤：

    Python
    if cv2.contourArea(cnt) < 100: # 面积太小，不进行形状分析
        continue
    '''
import cv2
import numpy as np

def detect_shape_features(contour):
    """
    输入: 单个轮廓 (contour)
    输出: 形状名称 (string), 圆度值 (float), 长宽比 (float)
    """
    # 1. 计算面积和周长
    area = cv2.contourArea(contour)
    perimeter = cv2.arcLength(contour, True)
    
    if perimeter == 0: return "Unknown", 0, 0

    # 2. 计算圆度 (Circularity)
    # 公式: 4 * π * Area / Perimeter^2
    circularity = (4 * np.pi * area) / (perimeter ** 2)

    # 3. 计算最小外接矩形的长宽比 (Aspect Ratio)
    # rect 格式: ((中心x, 中心y), (宽, 高), 旋转角度)
    rect = cv2.minAreaRect(contour)
    (x, y), (w, h), angle = rect
    aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else 0

    # 4. 逻辑分类 (vision_2025.py 的核心判断)
    shape_type = "Other"
    if circularity > 0.8:
        shape_type = "Circle/Ball"  # 圆度高 -> 球体或圆形
    elif aspect_ratio > 3.0:
        shape_type = "Strip/Line"   # 长宽比大 -> 条状物
    elif 0.5 < circularity < 0.8:
        shape_type = "Box/Block"    # 中间地带 -> 方块
        
    return shape_type, circularity, aspect_ratio

# --- 测试演示逻辑 ---
# 创建一个黑色的画布并画上几何图形
img = np.zeros((400, 600, 3), dtype=np.uint8)
cv2.circle(img, (150, 100), 50, (255, 255, 255), -1)      # 画圆
cv2.rectangle(img, (350, 50), (400, 250), (255, 255, 255), -1) # 画长条

# 转换为灰度图并提取轮廓
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
contours, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

for cnt in contours:
    name, circ, ar = detect_shape_features(cnt)
    # 获取轮廓中心点用于文字标注
    M = cv2.moments(cnt)
    cx, cy = int(M['m10']/M['m00']), int(M['m01']/M['m00'])
    
    # 绘制结果
    cv2.putText(img, f"{name} (C:{circ:.2f}, AR:{ar:.1f})", (cx-100, cy), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

cv2.imshow("Shape Detection", img)
cv2.waitKey(0)