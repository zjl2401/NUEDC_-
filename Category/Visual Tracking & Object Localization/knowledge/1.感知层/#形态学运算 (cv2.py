#形态学运算 (cv2.morphologyEx)
'''
在颜色分割后，Mask 图像往往不完美：可能有细小的噪声点（杂质），或者由于光照不均导致一个物体断裂成两半。
A. 开运算 (Opening) — 去除杂质
    操作： 先腐蚀（Erosion），再膨胀（Dilation）。
    原理： 腐蚀会把比结构元素小的白点（噪声）直接“吃掉”，而大物体虽然也被削了一圈，但随后的膨胀会把它补回来。
    适用场景： 画面中有散落的零星像素噪点。
B. 闭运算 (Closing) — 连接断裂
    操作： 先膨胀，再腐蚀。
    原理： 膨胀会让两个靠近的白块“生长”并融合在一起，填补中间的黑缝，随后的腐蚀会恢复物体的原始边缘。
    适用场景： 目标物体中间有黑洞，或一个长条由于阴影断成了两截。
核心代码实现：
    Python
    # 定义结构元素（内核），5x5 的全 1 矩阵
    kernel = np.ones((5, 5), np.uint8)

    # 开运算：去噪
    opened_mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    # 闭运算：填洞/连接
    closed_mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
'''