#黑框四边形检测 (find_screen_quad)
import cv2
import numpy as np

def find_and_order_screen_quad(frame):
    """
    输入：包含屏幕和背景的 BGR 全景图
    输出：排序后的 4 个顶点 [[TL], [TR], [BR], [BL]]
    """
    # --- 操作 1: 预处理与轮廓检测 ---
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 75, 200)
    
    # 寻找轮廓并取面积最大的前 5 个
    cnts, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:5]

    screen_pts = None
    for c in cnts:
        # 逼近多边形
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        # 如果是四边形，则认为是屏幕
        if len(approx) == 4:
            screen_pts = approx.reshape(4, 2)
            break

    if screen_pts is None:
        return None

    # --- 操作 2: 顶点排序 (核心数学逻辑) ---
    # 准备一个 4x2 的矩阵来保存排序后的点
    rect = np.zeros((4, 2), dtype="float32")
    
    # 左上角 (TL) 的 x+y 之和最小，右下角 (BR) 的 x+y 之和最大
    s = screen_pts.sum(axis=1)
    rect[0] = screen_pts[np.argmin(s)]  # Top-Left
    rect[2] = screen_pts[np.argmax(s)]  # Bottom-Right
    
    # 右上角 (TR) 的 y-x 之差最小，左下角 (BL) 的 y-x 之差最大
    diff = np.diff(screen_pts, axis=1)
    rect[1] = screen_pts[np.argmin(diff)] # Top-Right
    rect[3] = screen_pts[np.argmax(diff)] # Bottom-Left

    return rect
'''
干什么：
    从复杂的背景（墙壁、桌子、杂物）中提取出目标屏幕的四个顶点坐标。
进行了什么操作：
    二值化/边缘检测：通过 cv2.Canny 或阈值处理提取画面线条。
    轮廓发现：找到最大的闭合轮廓（通常假设屏幕是画面中最大的矩形物体）。
    多边形逼近 (cv2.approxPolyDP)：将弯曲的轮廓简化为折线。如果逼近结果刚好是 4 个点，说明找到了四边形。
    顶点排序（核心逻辑）：
        计算四个点的 $(x+y)$：
            最小值是左上角 (Top-Left)，最大值是右下角 (Bottom-Right)。
        计算四个点的 $(y-x)$：
            最小值是右上角 (Top-Right)，最大值是左下角 (Bottom-Left)。
为什么：
    确定有效区域：
        摄像头视野（FOV）往往比屏幕大很多。不限制边界，墙上的反光也会被误认为激光。
    防止图像颠倒：
        approxPolyDP 返回的点可能顺时针也可能逆时针，起始点也不固定。如果不排序，后续变换出来的画面可能是倒着的或镜像的。

输入：包含屏幕和背景的全景图。
操作：利用 x+y 和 y-x 的数学特性强制对顶点排序。
输出：确定了“左上、右上、右下、左下”顺序的四个物理顶点。
'''