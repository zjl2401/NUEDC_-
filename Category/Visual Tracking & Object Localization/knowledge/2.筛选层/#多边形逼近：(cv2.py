#多边形逼近：(cv2.approxPolyDP)
'''
多边形逼近通过减少轮廓点数，将复杂的曲线简化为由直线段组成的闭合图形。
    算法原理：D-P 算法 (Douglas-Peucker)它会寻找轮廓上距离直线最远的点，如果这个距离大于指定的阈值 $\epsilon$（Epsilon），就保留这个点作为顶点，否则就将其视为直线的一部分。
    输入： 原始轮廓、逼近精度 $\epsilon$。
    关键参数 $\epsilon$： 通常设为轮廓周长的百分比（例如 0.02 * perimeter）。$\epsilon$ 越小，逼近越精细（顶点多）；
        $\epsilon$ 越大，逼近越粗糙（顶点少）。
    形状判别逻辑：通过逼近后的顶点数量，我们可以极其简单地判断形状：
        3个顶点： 三角形
        4个顶点： 矩形或菱形
        5个顶点： 五边形
        >8个顶点： 接近圆形或不规则形
    核心代码实现：
        Python
        def identify_shape(contour):
        # 1. 计算周长，True 表示闭合
        peri = cv2.arcLength(contour, True)
        
        # 2. 进行多边形逼近，0.02*peri 是经验阈值
        # epsilon 越小，拟合越精确；True 表示闭合
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        
        # 3. 根据顶点数判断
        num_vertices = len(approx)
        
        if num_vertices == 3:
            return "Triangle"
        elif num_vertices == 4:
            # 进一步判断：长宽比接近 1 则是正方形，否则是长方形
            (x, y, w, h) = cv2.boundingRect(approx)
            ar = w / float(h)
            return "Square" if 0.95 <= ar <= 1.05 else "Rectangle"
        elif num_vertices == 5:
            return "Pentagon"
        elif num_vertices > 8:
            return "Circle-like"
        return "Polygon"
'''
