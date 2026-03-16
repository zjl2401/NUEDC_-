#连通域与面积过滤
import cv2

def get_laser_centroid(mask, min_area=5, max_area=500):
    # 1. 寻找轮廓 (Contours)
    # cv2.RETR_EXTERNAL 只找最外层轮廓
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    best_cnt = None
    max_current_area = 0
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        # 2. 面积过滤：太小的是噪点，太大的是反光块
        if min_area < area < max_area:
            if area > max_current_area:
                max_current_area = area
                best_cnt = cnt
                
    # 3. 计算质心
    if best_cnt is not None:
        M = cv2.moments(best_cnt)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            return (cx, cy), max_current_area
            
    return None, 0

'''
A. 为什么要设 min_area？
    对抗“椒盐噪声”：摄像头传感器在光线不足时会产生随机的闪烁像素点。这些点可能刚好符合红色的 HSV 范围，但它们通常只有 1-2 个像素大。
    设定阈值：如果你的激光点在画面中占 10 个像素，把 min_area 设为 5 就能完美过滤掉这些雪花点。
B. 为什么要设 max_area？
    排除大面积干扰：如果你身后有个红色的沙发，或者窗外有个红色的灯牌，它们的面积远大于激光点。
    安全防线：max_area 确保程序不会误把一个巨大的红色色块当成你的指挥棒。
C. 为什么要取“最大连通域”？
    唯一性假设：在轨迹跟随任务中，同一时间通常只有一个激光点。
    鲁棒性：即使画面边缘还有一些微小的红色干扰没滤干净，只要激光点是最明显的，程序就能死死锁定它。
'''
'''
连通域查找 (Contours)
    输入：
        mask：上一步生成的二值图。
    进行了什么操作：
        轮廓追踪：调用 cv2.findContours()。算法会扫描白色的像素簇，并把它们的边界连接起来。
        矢量化：将成千上万个白色像素点转化为一个个独立的点集（轮廓）。
    输出：
        contours：一个列表，里面包含了图像中发现的所有白色闭合区域的边界坐标。
面积过滤与质心计算
    输入：
        contours：上一步得到的轮廓列表。
        min_area / max_area：设定的面积阈值。
    进行了什么操作：
        面积筛选：遍历每个轮廓，计算其包围的面积。丢弃掉太小的（噪点）和太大的（背景干扰）。
        择优录取：在符合面积条件的轮廓中，选出面积最大的那一个，认定它就是“激光点”。
        数学求和（矩）：对该轮廓使用 cv2.moments()。通过一阶矩和零阶矩的比值算出重心的精确坐标。
    输出：
        (cx, cy)：激光点在屏幕上的 像素坐标。
        area：该目标的实际像素面积。
'''