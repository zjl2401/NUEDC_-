#滑动条 HSV 色彩空间分割
import cv2
import numpy as np

def nothing(x):
    pass

# 1. 初始化摄像头（0 通常是笔记本自带摄像头）
cap = cv2.VideoCapture(0)

# 2. 创建一个窗口，并添加 6 个滑动条来控制 H, S, V 的上下限
cv2.namedWindow("Trackbars")
cv2.resizeWindow("Trackbars", 640, 300)

# 参数说明：名称, 窗口名, 默认值, 最大值, 回调函数
cv2.createTrackbar("L-H", "Trackbars", 0, 180, nothing)   # Low Hue
cv2.createTrackbar("L-S", "Trackbars", 100, 255, nothing) # Low Saturation
cv2.createTrackbar("L-V", "Trackbars", 100, 255, nothing) # Low Value
cv2.createTrackbar("U-H", "Trackbars", 10, 180, nothing)  # Upper Hue
cv2.createTrackbar("U-S", "Trackbars", 255, 255, nothing) # Upper Saturation
cv2.createTrackbar("U-V", "Trackbars", 255, 255, nothing) # Upper Value

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # 转换色彩空间
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # 3. 读取当前滑动条的数值
    l_h = cv2.getTrackbarPos("L-H", "Trackbars")
    l_s = cv2.getTrackbarPos("L-S", "Trackbars")
    l_v = cv2.getTrackbarPos("L-V", "Trackbars")
    u_h = cv2.getTrackbarPos("U-H", "Trackbars")
    u_s = cv2.getTrackbarPos("U-S", "Trackbars")
    u_v = cv2.getTrackbarPos("U-V", "Trackbars")

    # 定义阈值范围并创建 Mask
    lower = np.array([l_h, l_s, l_v])
    upper = np.array([u_h, u_s, u_v])
    mask = cv2.inRange(hsv, lower, upper)

    # 4. 显示结果
    # 原图
    cv2.imshow("Frame", frame)
    # 过滤后的二值图（白色代表被选中的颜色）
    cv2.imshow("Mask", mask)

    # 按下 'q' 键退出并打印当前数值
    if cv2.waitKey(1) & 0xFF == ord('q'):
        print(f"最终阈值建议: lower = [{l_h}, {l_s}, {l_v}], upper = [{u_h}, {u_s}, {u_v}]")
        break

cap.release()
cv2.destroyAllWindows()