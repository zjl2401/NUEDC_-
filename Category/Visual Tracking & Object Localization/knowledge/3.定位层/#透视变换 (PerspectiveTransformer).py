#透视变换 (PerspectiveTransformer)
def get_screen_coordinate(laser_point, src_pts, screen_w=1920, screen_h=1080):
    """
    输入：
        laser_point: 图像矩算出的质心 (cx, cy)
        src_pts: 上一步得到的排序后的屏幕 4 个顶点
        screen_w/h: 你电脑屏幕的标准分辨率
    输出：映射后的标准屏幕坐标 (x, y)
    """
    # --- 操作 1: 计算变换矩阵 M ---
    # 定义目标坐标系：标准的长方形 [左上, 右上, 右下, 左下]
    dst_pts = np.array([
        [0, 0], 
        [screen_w, 0], 
        [screen_w, screen_h], 
        [0, screen_h]
    ], dtype="float32")
    
    # 生成透视变换矩阵 M
    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
    
    # --- 操作 2: 坐标投影运算 ---
    # 将输入的 (cx, cy) 包装成 OpenCV 要求的 3D 向量格式
    point_data = np.array([[[laser_point[0], laser_point[1]]]], dtype="float32")
    
    # 使用 M 矩阵进行透视投影变换
    transformed_point = cv2.perspectiveTransform(point_data, M)
    
    # 提取结果并转为整数像素
    final_x = int(transformed_point[0][0][0])
    final_y = int(transformed_point[0][0][1])
    
    return (final_x, final_y)
'''
干什么：
    利用数学矩阵，将一个倾斜、拉伸的四边形区域“拉直”成一个标准的长方形。
进行了什么操作：
    获取变换矩阵 (cv2.getPerspectiveTransform)：
        输入：刚才排序好的 4 个原始顶点。
        输入：目标屏幕的标准尺寸（如 4 个标准顶点：[0,0], [1920,0], [1920,1080], [0,1080]）。
    坐标转换 (cv2.perspectiveTransform)：将激光点的像素坐标 $(cx, cy)$ 乘以这个矩阵，得到它在标准屏幕上的物理坐标 $(x', y')$。
为什么：
    纠正透视畸变：由于摄像头安装位置（通常在斜上方或侧方），正方形的屏幕在画面里看起来像个梯形或不规则四边形。透视变换能消除这种“近大远小”的几何失真。
    归一化与交互：摄像头画面可能是 $640 \times 480$ 的。电脑屏幕是 $1920 \times 1080$ 的。变换后，激光点在画面里的位置能完美对应到显示器上的每一个像素，从而实现**“激光指哪，光标跟到哪”**的高精度交互。

输入：图像坐标 $(cx, cy)$ + 变换矩阵 $M$。
操作：通过透视投影矩阵运算，消除摄像头斜拍产生的拉伸畸变。
输出：标准屏幕坐标（例如指在屏幕正中心，输出就是 $960, 540$）。
'''