#图像矩计算质心 (cv2.moments) 外接矩形、PnP 测距 
import cv2
import numpy as np

# 1. 假设已知目标物的实际物理尺寸 (单位: mm)
# 以中心为原点，四个角点的 3D 坐标
obj_pts = np.array([
    [-50, -50, 0], [50, -50, 0], 
    [50, 50, 0], [-50, 50, 0]
], dtype=np.float32)

# 2. 相机内参 (需通过标定获得)
camera_matrix = np.array([[800, 0, 320], [0, 800, 240], [0, 0, 1]], dtype=np.float32)
dist_coeffs = np.zeros((4,1)) # 假设无畸变

def process_frame(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for cnt in contours:
        if cv2.contourArea(cnt) < 500: continue

        # --- 矩心计算 ---
        M = cv2.moments(cnt)
        cx = int(M['m10']/M['m00'])
        cy = int(M['m01']/M['m00'])

        # --- 最小外接矩形 ---
        rect = cv2.minAreaRect(cnt)
        box = cv2.boxPoints(rect)
        box = np.int0(box) # 四个角点的像素坐标

        # --- PnP 测距 ---
        # 确保 box 点的顺序与 obj_pts 一致
        success, rvec, tvec = cv2.solvePnP(obj_pts, box.astype(np.float32), camera_matrix, dist_coeffs)
        
        if success:
            distance = np.linalg.norm(tvec) # 欧式距离
            z_depth = tvec[2][0]          # 垂直深度
            print(f"Distance: {distance:.2f}mm, Depth: {z_depth:.2f}mm")

    return frame
'''
输入： 
    经过筛选后的单个连通域轮廓 (best_cnt)。
进行了什么操作： 
    1.  积分累加：算法遍历轮廓内所有的像素点。
    2.  零阶矩 ($M_{00}$)：计算轮廓内所有像素的总和，对于二值图，它等价于轮廓面积。
    3.  一阶矩 ($M_{10}, M_{01}$)：分别计算像素在 $x$ 方向和 $y$ 方向上的累加加权值。
输出： 目标的重心坐标 $(cx, cy)$

1. 亚像素级的稳定性 (Sub-pixel Precision)
    如果直接取轮廓外接矩形的中心，坐标只能是整数（像素单位）。但激光点在移动时，像素亮度分布是连续变化的。图像矩通过加权平均，计算出的重心可以是 $10.4$ 像素。这意味着：
        当激光微小移动时，坐标会平滑滑过，而不是在 $10$ 和 $11$ 像素之间生硬跳动。
        这对于轨迹跟随至关重要，能让你的利萨如图形线条看起来更丝滑。
2. 抗形变干扰
    激光笔打在屏幕上并不总是完美的圆，可能会因为角度变成椭圆或不规则形状。
        质心 (Centroid) 是物理意义上的“平衡点”。无论形状如何扭曲，质心始终代表了该色块能量最集中的地方。

1. 矩心计算 (Centroid)通过图像矩（Moments）
    计算物体的几何中心，用于确定物体在图像坐标系中的精确点位置。
    输入：二值化后的图像（ROI）或轮廓点集。
    中间操作：计算 0 阶矩 $M_{00}$（代表面积）。计算 1 阶矩 $M_{10}$ 和 $M_{01}$。利用公式 $\bar{x} = \frac{M_{10}}{M_{00}}$, $\bar{y} = \frac{M_{01}}{M_{00}}$ 得到坐标。
    输出：像素坐标 $(u, v)$。
2. 外接矩形 (Bounding Box)
    为物体加上包围框，分为直立外接矩形 (BoundingRect) 和 最小外接矩形 (MinAreaRect)。
    输入：提取到的物体的轮廓（Contours）。
    中间操作：
        直立矩形：计算轮廓的最大/最小 $x, y$，输出不带旋转角度的矩形。
        最小矩形：基于旋转卡壳算法，寻找包围面积最小的矩形（带旋转角度）。
    输出：左上角坐标、宽高、旋转角度（针对 MinAreaRect）。
3. PnP 测距 (Perspective-n-Point)
    根据物体的 3D 模型点（已知）与图像 2D 匹配点，求解相机与物体之间的位姿。
    输入：
        Object Points: 物体在真实世界坐标系下的 3D 点（如长方形四个角点的实际尺寸）。
        Image Points: 图像中对应的四个角点像素坐标。Camera Matrix: 相机内参 $K$（焦距、主点）。
        Dist Coeffs: 畸变系数。
    中间操作：通过迭代（Iterative）、P3P 或 EPNP 算法求解重投影误差最小的旋转向量 $R$ 和平移向量 $T$。
    输出：平移向量 $T = [x, y, z]^T$，其中 $z$ 即为直线距离。

'''