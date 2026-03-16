#最小外接矩形 (cv2.minAreaRect)
'''
普通的 cv2.boundingRect 永远是水平和垂直的，但物体在现实中往往是倾斜的。minAreaRect 会根据物体的实际轮廓寻找面积最小的覆盖矩形，带有旋转角度。输入： 轮廓数据 (contour)。操作：计算包含所有轮廓点的最小面积矩形。提取矩形的中心点 $(x, y)$、尺寸 $(w, h)$ 和 旋转角度 $\theta$。使用 cv2.boxPoints 将矩形参数转为 4 个顶点坐标以便绘制。输出： 一个包含 ((cx, cy), (w, h), angle) 的元组。

核心代码实现：
# 1. 计算最小外接矩形
rect = cv2.minAreaRect(cnt) 
(cx, cy), (w, h), angle = rect

# 2. 获取矩形的四个顶点坐标
box = cv2.boxPoints(rect)
box = np.int0(box) # 转换为整数

# 3. 绘制矩形（绿色，线宽2）
cv2.drawContours(img, [box], 0, (0, 255, 0), 2)

# 打印旋转角度
print(f"物体中心: ({cx}, {cy}), 旋转角度: {angle}度")
'''
