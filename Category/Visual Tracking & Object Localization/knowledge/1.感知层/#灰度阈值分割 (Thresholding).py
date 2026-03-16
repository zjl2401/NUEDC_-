#灰度阈值分割 (Thresholding)
'''
当目标与背景有明显的明暗差异（如白底黑字、黑底白块）时，使用灰度图比 HSV 更高效、更稳定。
输入： 原始 BGR 图像。
中间操作：
    灰度化： 移除颜色信息，仅保留亮度。
    二值化 (threshold)： 设定一个阈值（如 127），低于阈值的设为 0（黑），高于设为 255（白）。
    自适应阈值 (可选)： 如果画面光照不均，使用 adaptiveThreshold。
输出： 二值化 Mask 图。

    Python
    # 1. 转为灰度图
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 2. 手动阈值分割 (这里假设目标是黑色的，所以用 THRESH_BINARY_INV 翻转)
    # 输入：灰度图, 阈值, 最大值, 模式
    ret, mask = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)

    # 3. 如果光照不均，建议使用自适应阈值
    # mask = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
'''