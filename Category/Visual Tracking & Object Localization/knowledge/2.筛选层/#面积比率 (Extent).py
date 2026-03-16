#面积比率 (Extent)
'''
Extent（填充度）是一个非常鲁棒的形状描述子。它衡量的是物体实际面积与其正外接矩形面积的比值。输入： 轮廓数据 (contour)。操作：计算轮廓的实际面积 ($Area_{obj}$)。计算水平正矩形 (boundingRect) 的面积 ($Area_{bbox} = w \times h$)。计算比值：$Extent = \frac{Area_{obj}}{Area_{bbox}}$。判断逻辑：矩形： $Extent \approx 1.0$ (理论上满填充)。圆形： $Extent \approx \frac{\pi r^2}{(2r)^2} = \frac{\pi}{4} \approx 0.785$。三角形： 对于直角三角形，$Extent \approx 0.5$。输出： 0 到 1 之间的浮点数。

核心代码实现：
Python
# 1. 计算物体的实际面积
area = cv2.contourArea(cnt)

# 2. 获取水平正外接矩形
x, y, w, h = cv2.boundingRect(cnt)
rect_area = w * h

# 3. 计算 Extent
extent = float(area) / rect_area if rect_area > 0 else 0

# 4. 根据 Extent 辅助判断形状
if extent > 0.9:
    shape_type = "Rectangle"
elif 0.7 < extent < 0.85:
    shape_type = "Circle"
else:
    shape_type = "Irregular"

print(f"当前目标的填充度 (Extent): {extent:.2f}, 初步判定为: {shape_type}")                                                                                  
'''
