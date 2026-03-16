#目标选择与定位 (Object Localization)
'''
定位的本质是找到物体在图像中的“数学描述”（中心点、角度、距离）。
输入： 二值化 Mask。
中间操作：
    轮廓提取： 找到物体的边界。
    特征计算： 计算矩心（位置）、外接矩形（尺寸和角度）。
    物理投影： 根据相机焦距和像素偏移，计算实际物体相对于相机的方位角。
    输出： 目标状态向量 [x, y, w, h, angle]。

Python
def localize_target(mask, frame_width):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours: return None
    
    # 假设选择最大的那个
    cnt = max(contours, key=cv2.contourArea)
    
    # 获取几何矩
    M = cv2.moments(cnt)
    if M['m00'] == 0: return None
    
    # 像素中心点
    cx = int(M['m10'] / M['m00'])
    cy = int(M['m01'] / M['m00'])
    
    # 计算偏航误差 (中心点偏移量)
    error_x = cx - (frame_width / 2)
    
    return {"center": (cx, cy), "error_x": error_x}
'''